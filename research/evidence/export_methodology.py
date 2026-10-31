"""Inspect reviewed method/parameter sources without importing application code.

The catalogue describes defaults and their provenance. Executed manifests and
external measurements remain separate authorities; no readiness certification
or numerical tuning follows from a successful static check.
"""
import argparse
import ast
import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = Path("research/manifests/methodology.json")
TABLE_START = "<!-- methodology-parameters:start -->"
TABLE_END = "<!-- methodology-parameters:end -->"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def local_path(root, name):
    path = (root/name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Source must be an existing repository file: {name}")
    return path


def scoped_node(tree, scope):
    node = tree
    for name in scope.split(".") if scope else ():
        matches = [n for n in node.body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.name == name]
        if len(matches) != 1:
            raise ValueError(f"Scope must resolve exactly once: {scope}")
        node = matches[0]
    return node


def body_nodes(node):
    for child in ast.iter_child_nodes(node):
        yield child
        if not isinstance(child,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):
            yield from body_nodes(child)


def select(tree, ref):
    scope = scoped_node(tree,ref.get("scope",""))
    kind,target = ref["kind"],ref.get("target")
    if kind == "symbol":
        return scope
    matches = []
    if kind == "assignment":
        for node in body_nodes(scope):
            targets = node.targets if isinstance(node,ast.Assign) else [node.target] if isinstance(node,ast.AnnAssign) else []
            for assigned in targets:
                if ast.unparse(assigned) == target and node.value is not None:
                    matches.append(node.value)
                elif isinstance(assigned,(ast.Tuple,ast.List)) and isinstance(node.value,(ast.Tuple,ast.List)):
                    matches.extend(value for name,value in zip(assigned.elts,node.value.elts) if ast.unparse(name) == target)
    elif kind == "default":
        if not isinstance(scope,(ast.FunctionDef,ast.AsyncFunctionDef)):
            raise ValueError("Argument defaults require a function scope")
        args = scope.args.posonlyargs+scope.args.args
        pairs = list(zip(args[len(args)-len(scope.args.defaults):],scope.args.defaults))
        pairs += list(zip(scope.args.kwonlyargs,scope.args.kw_defaults))
        matches = [value for argument,value in pairs if argument.arg == target and value is not None]
    elif kind == "call_keyword":
        for node in body_nodes(scope):
            if not isinstance(node,ast.Call) or ast.unparse(node.func) != ref["call"]:
                continue
            if "tag" in ref and (not node.args or not isinstance(node.args[0],ast.Constant) or node.args[0].value != ref["tag"]):
                continue
            matches.extend(k.value for k in node.keywords if k.arg == target)
    elif kind == "compare_rhs":
        nodes = list(body_nodes(scope))
        if "guard" in ref:
            guards = [n for n in nodes if isinstance(n,ast.If) and any(isinstance(test,ast.Compare)
                and ast.unparse(test.left) == ref["guard"]["left"] and len(test.comparators) == 1
                and isinstance(test.comparators[0],ast.Constant) and test.comparators[0].value == ref["guard"]["value"]
                for test in ast.walk(n.test))]
            nodes = [part for guard in guards for part in ast.walk(guard.test)]
        for node in nodes:
            if (isinstance(node,ast.Compare) and ast.unparse(node.left) == target and len(node.ops) == 1
                    and type(node.ops[0]).__name__ == ref["operator"]):
                matches.append(node.comparators[0])
    else:
        raise ValueError(f"Unknown source selector: {kind}")
    if len(matches) != 1:
        raise ValueError(f"Selector must resolve exactly once, found {len(matches)}: {ref}")
    return matches[0]


def expression_fingerprint(node):
    node = copy.deepcopy(node)
    # Prose/line shifts do not change the reviewed algorithm expression.
    for part in ast.walk(node):
        if isinstance(part,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and part.body:
            first = part.body[0]
            if isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and isinstance(first.value.value,str):
                part.body = part.body[1:]
    return digest(ast.dump(node,include_attributes=False).encode())


def literal_value(node):
    candidate = node
    if isinstance(candidate,ast.BoolOp) and isinstance(candidate.op,ast.Or):
        candidate = candidate.values[-1]  # Declared fallback only, not a runtime override.
    if isinstance(node,ast.Call) and ast.unparse(node.func).rsplit(".",1)[-1] == "Field":
        defaults = [k.value for k in node.keywords if k.arg == "default"]
        if len(defaults) == 1:
            candidate = defaults[0]
    if isinstance(candidate,ast.Call) and ast.unparse(candidate.func) == "nn.Sequential":
        layers = []
        for layer in candidate.args:
            if not isinstance(layer,ast.Call):
                return "dynamic",None
            args = []
            for argument in layer.args:
                try:
                    args.append(ast.literal_eval(argument))
                except (ValueError,TypeError):
                    args.append(dict(expression=ast.unparse(argument)))
            layers.append(dict(layer=ast.unparse(layer.func),arguments=args,
                keyword_expressions={k.arg:ast.unparse(k.value) for k in layer.keywords}))
        return "architecture_spec",layers
    try:
        value = ast.literal_eval(candidate)
        json.dumps(value,allow_nan=False)
        return "literal",value
    except (ValueError,TypeError,SyntaxError):
        return "dynamic",None


def inspect(root=ROOT, catalogue=CATALOGUE):
    root = Path(root).resolve()
    catalogue_path = local_path(root,str(catalogue))
    data = json.loads(catalogue_path.read_text())
    if data.get("schema_version") != "methodology_v1":
        raise ValueError("Unknown methodology catalogue schema")
    profiles = set(data["profiles"])
    references = data["references"]
    if not profiles or any(not r.get("url","").startswith("https://") for r in references.values()):
        raise ValueError("Profiles and primary-source reference URLs are required")
    sources,trees,issues,parameters,methods,ids = {},{},[],[],[],set()
    def resolve(ref):
        name = ref["file"]
        path = local_path(root,name)
        if name not in trees:
            raw = path.read_bytes()
            sources[name] = digest(raw)
            trees[name] = ast.parse(raw,filename=name)
        node = select(trees[name],ref)
        return dict(source=ref,line=getattr(node,"lineno",1),expression=ast.unparse(node),
                    expression_sha256=expression_fingerprint(node))
    for group,output in (("parameters",parameters),("methods",methods)):
        for entry in data[group]:
            identity = entry["id"]
            if identity in ids:
                issues.append(f"Duplicate catalogue identifier: {identity}")
            ids.add(identity)
            required = ("purpose","profiles","origin","justification","status","override_notes","references","reviewed_ast_sha256")
            if any(key not in entry or entry[key] in ("",None) for key in required):
                issues.append(f"Missing review metadata: {identity}")
            if not entry.get("profiles") or set(entry["profiles"])-profiles or set(entry.get("references",[]))-set(references):
                issues.append(f"Unknown profile/reference: {identity}")
            if entry.get("origin") not in {"local_engineering","synthetic_protocol","literature_adaptation","calibration_required","derived","established_method"}:
                issues.append(f"Unknown numerical/method origin: {identity}")
            if entry.get("status") not in {"active","conditional","declared_unused","historical_example"}:
                issues.append(f"Unknown activity status: {identity}")
            if group == "parameters" and not entry.get("unit"):
                issues.append(f"Missing unit: {identity}")
            try:
                current = resolve(entry["source"])
                if current["expression_sha256"] != entry["reviewed_ast_sha256"]:
                    issues.append(f"Unreviewed source expression: {identity}")
                consumers = []
                for consumer in entry.get("consumers",[]):
                    result = resolve(consumer["source"])
                    if result["expression_sha256"] != consumer["reviewed_ast_sha256"]:
                        issues.append(f"Unreviewed consumer/activity contract: {identity}")
                    consumers.append({key:value for key,value in result.items() if key != "expression"})
                if entry.get("status") == "declared_unused" and not consumers:
                    issues.append(f"Unused declaration needs a reviewed consumer: {identity}")
                row = {**entry,**current,"consumers":consumers}
                if group == "parameters":
                    row["resolution"],row["value"] = literal_value(select(trees[entry["source"]["file"]],entry["source"]))
                output.append(row)
            except (ValueError,KeyError,SyntaxError,OSError) as exc:
                issues.append(f"{identity}: {exc}")
    return dict(schema_version=data["schema_version"],structural_integrity_passed=not issues,issues=issues,
        profiles=data["profiles"],references=references,parameters=parameters,methods=methods,
        source_sha256=sources,catalogue_sha256=digest(catalogue_path.read_bytes()),
        coverage="Curated method-critical parameter surfaces and implementation contracts, not every local variable or numerical literal.",
        authority="Source defaults only. Executed settings require the corresponding run manifest/checkpoint; physical measurements require independent data.",
        open_evidence_requirements=data["open_evidence_requirements"],
        algorithmic_novelty_established=False,field_validation_established=False,production_certified=False)


def compare_sources(root, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    mappings = [manifest[key] for key in ("source_hashes","source_sha256") if isinstance(manifest.get(key),dict)]
    if len(mappings) != 1 or not mappings[0]:
        raise ValueError("Expected one known nonempty source_hashes/source_sha256 map")
    differences = []
    for name,expected in mappings[0].items():
        if not isinstance(expected,str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise ValueError("Historical source hashes must be full SHA-256 hex digests")
        path = (Path(root)/name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(Path(root).resolve()):
            raise ValueError("Historical source path leaves repository")
        actual = digest(path.read_bytes()) if path.is_file() else None
        if actual != expected:
            differences.append(dict(file=name,recorded_sha256=expected,current_sha256=actual))
    return dict(recorded_sources_match=not differences,differences=differences,
        interpretation="Changed sources require archived-source replay. No archived code was executed and no evidence was rewritten.")


def parameter_rows(report):
    return [dict(id=p["id"],profiles=";".join(p["profiles"]),value=json.dumps(p["value"],sort_keys=True),
        resolution=p["resolution"],unit=p["unit"],origin=p["origin"],status=p["status"],purpose=p["purpose"],
        justification=p["justification"],override_notes=p["override_notes"],references=";".join(p["references"]),
        file=p["source"]["file"],line=p["line"],expression=p["expression"],source_sha256=report["source_sha256"][p["source"]["file"]])
        for p in report["parameters"]]


def content_table(report):
    """Deterministic source-default table for the maintained reference."""
    lines = ["| Parameter | Source default | Unit | Activity | Source |",
             "| --- | --- | --- | --- | --- |"]
    for row in report["parameters"]:
        if row["resolution"] == "dynamic":
            value = row["expression"]+" (dynamic reference)"
        elif row["resolution"] == "architecture_spec":
            value = "; ".join(layer["layer"].replace("nn.","")+"("+", ".join(
                arg["expression"] if isinstance(arg,dict) else str(arg) for arg in layer["arguments"])+")" for layer in row["value"])
        else:
            value = json.dumps(row["value"],ensure_ascii=False)
        if len(value) > 180:
            value = "Structured schema; full value in source and exported JSON/CSV"
        value = value.replace("|","\\|").replace("\n"," ")
        lines.append(f"| `{row['id']}` | `{value}` | {row['unit']} | {row['status']} | [source]({row['source']['file']}) |")
    return "\n".join(lines)


def check_content(report, path):
    text = Path(path).read_text()
    if text.count(TABLE_START) != 1 or text.count(TABLE_END) != 1:
        return ["CONTENT.md requires exactly one generated methodology parameter table"]
    actual = text.split(TABLE_START,1)[1].split(TABLE_END,1)[0].strip()
    if actual != content_table(report):
        return ["CONTENT.md parameter table differs from reviewed sources; regenerate it after reviewing catalogue drift"]
    return []


def export(report, output, root=ROOT):
    if not report["structural_integrity_passed"]:
        raise ValueError("Resolve methodology review issues before export")
    output = Path(output).resolve()
    if any((p/"manifest.json").exists() and (p/"report.json").exists() for p in output.parents):
        raise ValueError("Do not write inside an existing sealed evidence collection")
    output.mkdir(parents=True,exist_ok=False)
    rows = parameter_rows(report)
    with (output/"parameters.csv").open("x",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output/"methodology.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    (output/"parameter_table.md").write_text(content_table(report)+"\n")
    paths = set(report["source_sha256"])|{str(CATALOGUE),str(Path(__file__).resolve().relative_to(ROOT))}
    with zipfile.ZipFile(output/"source_snapshot.zip","x",compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(paths):
            archive.write(local_path(Path(root),name),name)
    revision = subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    dirty = bool(subprocess.check_output(["git","status","--porcelain"],cwd=root,text=True).strip())
    manifest = dict(git_commit=revision,worktree_dirty=dirty,python_version=sys.version,
        output_sha256={p.name:digest(p.read_bytes()) for p in output.iterdir() if p.is_file()},
        scope="Static implementation/defaults snapshot. No training, traffic experiment, cloud write or readiness certification.")
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--table",action="store_true",help="Print the reviewed source-default table for CONTENT.md")
    mode.add_argument("--output",type=Path)
    mode.add_argument("--compare-manifest",type=Path)
    args = parser.parse_args()
    if args.compare_manifest:
        print(json.dumps(compare_sources(ROOT,args.compare_manifest),indent=2))
        return
    report = inspect()
    if args.table:
        if not report["structural_integrity_passed"]:
            raise SystemExit("Review source/catalogue drift before rendering the table")
        print(content_table(report))
        return
    if args.output:
        export(report,args.output)
    print(json.dumps(dict(structural_integrity_passed=report["structural_integrity_passed"],
        parameters=len(report["parameters"]),methods=len(report["methods"]),issues=report["issues"],
        dynamic_parameters=sum(p["resolution"] == "dynamic" for p in report["parameters"]),
        algorithmic_novelty_established=False,field_validation_established=False,production_certified=False),indent=2))
    if not report["structural_integrity_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
