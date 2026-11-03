"""Generate SVG/PDF/PNG methodology figures from the frozen FlowSync source.

Example: python -m research.paper_figures.generate --output research/paper_figures/generated
Use --list for figure IDs or --verify DIRECTORY for saved-file integrity checks.
Matplotlib is declared in research/requirements.txt. No TeX or Graphviz needed.
"""
import argparse
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import tempfile
import zipfile

from .catalog import FIGURES, select

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
SCHEMA = "flowsync_paper_figures_v1"
PDF_METADATA = dict(Creator="FlowSync methodology figure generator", CreationDate=None, ModDate=None)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_check(root=ROOT):
    manifest = json.loads((PACKAGE/"source_manifest.json").read_text())
    required = {p for f in FIGURES for p in f.sources}
    if manifest["schema_version"] != "paper_figure_sources_v1" or set(manifest["source_sha256"]) != required:
        raise ValueError("Figure source coverage differs from the reviewed catalogue")
    for name, expected in manifest["source_sha256"].items():
        path = (root/name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or digest(path) != expected:
            raise ValueError("Frozen figure source changed or is missing: "+name)
    return manifest


def fresh_output(path):
    if path.exists() or path.is_symlink():
        raise FileExistsError("Preserve existing figures; choose a new output directory: "+str(path))
    if any((p/"manifest.json").exists() or (p/"report.json").exists() for p in path.resolve().parents):
        raise ValueError("Do not write figures inside frozen evidence collections")


def save_json(path, value):
    with path.open("x") as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False); stream.write("\n")


def generator_sources():
    return sorted([*PACKAGE.glob("*.py"),PACKAGE/"source_manifest.json"])


def archive_sources(output, inputs, generators):
    with zipfile.ZipFile(output/"source_snapshot.zip","x") as archive:
        for name in sorted(set(inputs)|set(generators)):
            info = zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o100644 << 16; info.create_system=3
            archive.writestr(info,(ROOT/name).read_bytes())


def overview(output, selected):
    from PIL import Image, ImageDraw, ImageFont
    from matplotlib.font_manager import FontProperties, findfont
    font=ImageFont.truetype(findfont(FontProperties(family="DejaVu Sans")),19)
    width,height,columns=850,650,2
    sheet=Image.new("RGB",(columns*width,((len(selected)+columns-1)//columns)*height),"white")
    draw=ImageDraw.Draw(sheet)
    for index,spec in enumerate(selected):
        x,y=(index%columns)*width,(index//columns)*height
        with Image.open(output/(spec.identifier+".png")) as img:
            thumb=img.convert("RGB");thumb.thumbnail((width-32,height-70),Image.Resampling.LANCZOS)
        sheet.paste(thumb,(x+(width-thumb.width)//2,y+48+(height-70-thumb.height)//2))
        draw.text((x+18,y+14),spec.identifier.split("_")[0]+"  "+spec.title,fill="#182B3A",font=font)
        draw.rectangle((x,y,x+width-1,y+height-1),outline="#CCD2D7")
    sheet.save(output/"overview.png")


def latex_snippet(output, selected, formats):
    extension = "pdf" if "pdf" in formats else "png" if "png" in formats else None
    if extension is None:
        return  # SVG-only users can use the svg package or their editor.
    def escape(text):
        return "".join({"\\":r"\textbackslash{}","&":r"\&","%":r"\%","$":r"\$","#":r"\#",
            "_":r"\_","{":r"\{","}":r"\}"}.get(char,char) for char in text)
    blocks=["% Requires \\usepackage{graphicx}. Copy the assets into figures/ or adjust paths.",
            "% Select the figures appropriate to the paper; including every figure is optional."]
    for spec in selected:
        blocks.append("\n".join([r"\begin{figure*}[t]",r"\centering",
            r"\includegraphics[width=\textwidth]{figures/"+spec.identifier+"."+extension+"}",
            r"\caption{"+escape(spec.caption)+"}",r"\label{fig:"+spec.identifier.replace("_","-")+"}",r"\end{figure*}"]))
    (output/"figures.tex").write_text("\n\n".join(blocks)+"\n")


def generate(output, identifiers=None, formats=("svg","pdf","png"), dpi=300):
    output = Path(output)
    chosen = select(identifiers)
    if not formats or len(set(formats)) != len(formats) or set(formats)-{"svg","pdf","png"}:
        raise ValueError("Choose unique formats from svg, pdf and png")
    if type(dpi) is not int or not 72 <= dpi <= 600:
        raise ValueError("PNG DPI must be an integer from 72 to 600")
    fresh_output(output)
    inputs = source_check()
    generators = {p.relative_to(ROOT).as_posix():digest(p) for p in generator_sources()}
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.font_manager import FontProperties, findfont
    from matplotlib.ft2font import __freetype_version__
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".paper-figures-",dir=output.parent) as folder:
        staging=Path(folder); evidence={}
        pdf = PdfPages(staging/"all_figures.pdf",metadata=PDF_METADATA) if "pdf" in formats else None
        try:
            for spec in chosen:
                board=spec.render()
                try:
                    board.validate()
                    for fmt in formats:
                        metadata = PDF_METADATA if fmt=="pdf" else dict(Creator="FlowSync methodology figure generator",Date=None) if fmt=="svg" else dict(Software="FlowSync methodology figure generator")
                        board.fig.savefig(staging/(spec.identifier+"."+fmt),format=fmt,dpi=dpi,metadata=metadata)
                    if pdf: pdf.savefig(board.fig)
                    if board.evidence: evidence[spec.identifier]=board.evidence
                finally: board.close()
        finally:
            if pdf: pdf.close()
        if "png" in formats: overview(staging,chosen)
        latex_snippet(staging,chosen,formats)
        save_json(staging/"captions.json",[asdict(spec) for spec in chosen])
        archive_sources(staging,inputs["source_sha256"],generators)
        if source_check() != inputs or any(digest(ROOT/n)!=h for n,h in generators.items()):
            raise ValueError("Sources changed during figure generation")
        font=Path(findfont(FontProperties(family="DejaVu Sans")))
        save_json(staging/"manifest.json",dict(schema_version=SCHEMA,
            implementation_commit=inputs["implementation_commit"],figure_ids=[s.identifier for s in chosen],formats=list(formats),png_dpi=dpi,
            scope="Methodology illustrations only. No native traffic or learning performance evaluated.",
            source_sha256=inputs["source_sha256"],generator_sha256=generators,
            environment=dict(python=platform.python_version(),matplotlib=version("matplotlib"),pillow=version("Pillow"),
                             freetype=__freetype_version__,font_file=font.name,font_sha256=digest(font)),
            constructed_illustrations=evidence,native_traffic_runs=0,training_runs=0,performance_evaluated=False,
            layout_checks=dict(page_text_containment=True,box_text_containment=True,opaque_box_overlap=False),
            output_sha256={p.name:digest(p) for p in staging.iterdir() if p.is_file()}))
        fresh_output(output)
        os.rename(staging,output)
    return dict(generated=True,figures=len(chosen),output=str(output),formats=list(formats),native_traffic_runs=0,training_runs=0)


def verify(directory):
    directory=Path(directory)
    saved=json.loads((directory/"manifest.json").read_text())
    selected=select(saved["figure_ids"])
    inputs=source_check()
    formats=saved["formats"]
    if (not isinstance(formats,list) or not formats or len(set(formats))!=len(formats)
            or set(formats)-{"svg","pdf","png"} or type(saved["png_dpi"]) is not int or not 72<=saved["png_dpi"]<=600
            or any(type(saved.get(k)) is not int or saved[k]!=0 for k in ("native_traffic_runs","training_runs"))
            or saved.get("performance_evaluated") is not False):
        raise ValueError("Changed figure format or non-experimental scope")
    expected_files={f.identifier+"."+fmt for f in selected for fmt in formats}|{"source_snapshot.zip","captions.json"}
    if "pdf" in formats: expected_files.add("all_figures.pdf")
    if "png" in formats: expected_files.add("overview.png")
    if {"pdf","png"}&set(formats): expected_files.add("figures.tex")
    if set(saved["output_sha256"])!=expected_files:
        raise ValueError("Expected figure assets are missing or relabelled")
    if (saved["schema_version"]!=SCHEMA or saved["source_sha256"]!=inputs["source_sha256"]
            or saved["implementation_commit"]!=inputs["implementation_commit"]
            or saved["generator_sha256"]!={p.relative_to(ROOT).as_posix():digest(p) for p in generator_sources()}
            or json.loads((directory/"captions.json").read_text())!=json.loads(json.dumps([asdict(f) for f in selected]))):
        raise ValueError("Saved figures differ from the current frozen source/catalogue/generator")
    if ({p.name for p in directory.iterdir()}!=set(saved["output_sha256"])|{"manifest.json"}
            or any(not (directory/n).is_file() or (directory/n).is_symlink() or digest(directory/n)!=h
                   for n,h in saved["output_sha256"].items())):
        raise ValueError("Figure output coverage or hashes changed")
    expected={**saved["source_sha256"],**saved["generator_sha256"]}
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        if set(archive.namelist())!=set(expected) or len(archive.namelist())!=len(expected) or any(
                hashlib.sha256(archive.read(n)).hexdigest()!=h for n,h in expected.items()):
            raise ValueError("Figure source archive changed")
    return dict(verified=True,figures=len(selected),files=len(saved["output_sha256"]),
        scope="Frozen source/catalogue, archived bytes and saved-output integrity only; no render or traffic rerun.",rendering_reexecuted=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--output",type=Path,default=PACKAGE/"generated")
    mode.add_argument("--verify",type=Path)
    mode.add_argument("--list",action="store_true")
    parser.add_argument("--figures",nargs="+",help="One or more IDs from --list; default is all ten")
    parser.add_argument("--formats",nargs="+",choices=("svg","pdf","png"),default=["svg","pdf","png"])
    parser.add_argument("--dpi",type=int,default=300)
    args=parser.parse_args()
    try:
        if args.list:
            for figure in FIGURES: print(figure.identifier+"  "+figure.title+"  ["+figure.status+"]")
            return
        result=verify(args.verify) if args.verify else generate(args.output,args.figures,tuple(args.formats),args.dpi)
    except (ValueError,OSError,KeyError,zipfile.BadZipFile) as exc:
        parser.exit(1,str(exc)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
