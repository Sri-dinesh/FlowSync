#!/usr/bin/env python3
"""Offline checks for maintained documentation, dependency metadata and hygiene."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)")
OPTIONAL_ARTIFACTS = ("results/", "server/models/", "data/", "models/")


def repository_files(root):
    result = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"],
                            cwd=root, capture_output=True, text=True, check=True)
    return sorted({root / name for name in result.stdout.split("\0") if name and (root / name).is_file()})


def check_frontend(root):
    issues = []
    package = json.loads((root / "client/package.json").read_text())
    lock = json.loads((root / "client/package-lock.json").read_text())
    for field in ("dependencies", "devDependencies", "optionalDependencies"):
        if package.get(field, {}) != lock["packages"][""].get(field, {}):
            issues.append(f"client/package-lock.json: {field} differs from package.json")
    for name in ("pnpm-lock.yaml", "pnpm-workspace.yaml", "client/pnpm-lock.yaml", "client/yarn.lock"):
        if (root / name).exists():
            issues.append(f"{name}: duplicate JavaScript package-manager configuration")
    return issues


def check_links(root, files):
    issues, checked, optional = [], 0, 0
    for path in files:
        if path.suffix != ".md":
            continue
        name = path.relative_to(root).as_posix()
        if name.startswith(("docs/archive/", "research/docs/archive/")) and path.name != "README.md":
            continue  # Historical line/path references are evidence, not maintained guides.
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            for match in LINK.finditer(line):
                target = match.group(1).strip("<>")
                parsed = urlsplit(target)
                if parsed.scheme == "file":
                    issues.append(f"{name}:{line_number}: machine-specific file:// link")
                    continue
                if parsed.scheme or target.startswith(("#", "//")):
                    continue
                if not parsed.path:
                    continue
                resolved = (path.parent / unquote(parsed.path)).resolve()
                try:
                    relative = resolved.relative_to(root).as_posix()
                except ValueError:
                    issues.append(f"{name}:{line_number}: link leaves repository: {target}")
                    continue
                if relative.startswith(OPTIONAL_ARTIFACTS):
                    optional += 1
                    continue
                checked += 1
                if not resolved.exists():
                    issues.append(f"{name}:{line_number}: missing local link: {target}")
    return issues, checked, optional


def constant_path(node, root):
    if isinstance(node, ast.Name) and node.id == "ROOT":
        return root
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left, right = constant_path(node.left, root), constant_path(node.right, root)
        if isinstance(left, Path) and isinstance(right, str):
            return left / right
    return None


def check_source(root, files):
    issues, count = [], 0
    for path in files:
        name = path.relative_to(root).as_posix()
        if path.suffix == ".py":
            count += 1
            try:
                tree = ast.parse(path.read_text(), filename=name)
            except SyntaxError as exc:
                issues.append(f"{name}:{exc.lineno}: {exc.msg}")
                continue
            for node in ast.walk(tree):
                modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                           else [node.module] if isinstance(node, ast.ImportFrom) and not node.level else [])
                for module in modules:
                    if module and (module == "research" or module.startswith("research.")):
                        if (module.startswith("research.legacy.") and name.startswith("research/")
                                and not name.startswith("research/legacy/")):
                            issues.append(f"{name}:{node.lineno}: maintained tools must not depend on legacy runners")
                        target = root.joinpath(*module.split("."))
                        if not target.with_suffix(".py").is_file() and not (target / "__init__.py").is_file():
                            issues.append(f"{name}:{node.lineno}: missing research import: {module}")
            if name.startswith("research/"):
                if path.parent == root / "research" and path.name not in {"__init__.py", "__main__.py"}:
                    issues.append(f"{name}: place research tools in their purpose-based package")
                if not (path.parent / "__init__.py").is_file():
                    issues.append(f"{name}: research package needs __init__.py")
                for node in tree.body:
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PROTOCOL" for t in node.targets):
                        protocol = constant_path(node.value, root)
                        if isinstance(protocol, Path) and not protocol.is_file():
                            issues.append(f"{name}: missing declared protocol: {protocol.relative_to(root)}")
        elif path.suffix == ".sh":
            if path.parent == root / "research":
                issues.append(f"{name}: place pilot launchers in research/pilots/launchers")
            result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
            if result.returncode:
                issues.append(f"{name}: shell syntax error: {result.stderr.strip()}")
    return issues, count


def check_hygiene(root):
    issues = []
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root, text=True).split("\0")
    for name in tracked:
        if not name or not (root / name).exists():
            continue
        path = Path(name)
        if path.suffix in {".pyc", ".pyo", ".pt", ".pth", ".ckpt"} or "__pycache__" in path.parts:
            issues.append(f"{name}: generated/model artifact must not be tracked")
        if (path.name == ".env" or path.name.startswith(".env.")) and path.name != ".env.example":
            issues.append(f"{name}: private environment file must not be tracked")
    probes = ["research/scenarios/__pycache__/probe.pyc", "research/calibration/__pycache__/probe.pyc",
              "server/.env", "client/.env.local"]
    ignored = subprocess.run(["git", "check-ignore", "--stdin"], cwd=root, input="\n".join(probes)+"\n",
                             capture_output=True, text=True)
    for name in probes:
        if name not in ignored.stdout.splitlines():
            issues.append(f"{name}: ignore rules must protect generated/private files")
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    files = repository_files(ROOT)
    links, checked_links, optional_links = check_links(ROOT, files)
    source, checked_python = check_source(ROOT, files)
    issues = check_frontend(ROOT) + check_hygiene(ROOT) + links + source
    for issue in issues:
        print(issue)
    print(f"Checked {checked_python} Python files and {checked_links} local documentation links; "
          f"{optional_links} local artifact links are optional in a fresh clone.")
    if issues:
        print(f"Repository check failed: {len(issues)} issue(s).")
        return 1
    print("Repository checks passed. External links and generated data were not fetched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
