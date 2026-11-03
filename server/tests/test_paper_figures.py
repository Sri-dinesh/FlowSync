"""Static paper assets: source drift, truthful scope, integrity and text layout."""
import json
import shutil

from PIL import Image
import pytest

from research.paper_figures.catalog import FIGURES
from research.paper_figures.drawing import Board
from research.paper_figures import generate as tool


@pytest.fixture(scope="module")
def assets(tmp_path_factory):
    output=tmp_path_factory.mktemp("paper-assets")/"figures"
    result=tool.generate(output,dpi=96)
    assert result["figures"]==10 and result["native_traffic_runs"]==0
    return output


def test_every_paper_asset_renders_as_vector_and_raster_with_verified_sources(assets):
    receipt=tool.verify(assets)
    assert receipt["verified"] and receipt["files"]==35
    assert receipt["rendering_reexecuted"] is False
    for spec in FIGURES:
        assert (assets/(spec.identifier+".svg")).read_text().startswith("<?xml")
        assert (assets/(spec.identifier+".pdf")).read_bytes().startswith(b"%PDF-")
        with Image.open(assets/(spec.identifier+".png")) as image:
            assert image.width>600 and image.height>300
            image.load()
    assert (assets/"all_figures.pdf").read_bytes().startswith(b"%PDF-")
    assert "\\begin{figure*}" in (assets/"figures.tex").read_text()


def test_witness_and_deferred_protocol_cannot_be_mistaken_for_traffic_results(assets):
    manifest=json.loads((assets/"manifest.json").read_text())
    example=manifest["constructed_illustrations"]["fig08_ledger_witness"]
    assert example["controller_intervals"]==880 and not example["performance_evaluated"]
    assert example["native_traffic_runs"]==example["training_runs"]==0
    assert [r["phase"] for r in example["decisions"]]==[1,0]
    assert [r["budget_green_s"] for r in example["decisions"]]==[16,8]
    assert example["decisions"][0]["debt_ew_s"]==8
    assert example["decisions"][1]["debt_ew_s"]==pytest.approx(1.6,abs=.0001)
    captions=json.loads((assets/"captions.json").read_text())
    planned=next(c for c in captions if c["identifier"]=="fig09_paired_study_design")
    assert planned["status"]=="deferred_protocol_schematic"
    assert "not completed scientific collection" in planned["caption"]
    assert "Evaluation truth" in (assets/"fig02_control_boundary.svg").read_text()


def test_stale_sources_are_refused_instead_of_silently_redrawing_new_methods(tmp_path):
    inputs=tool.source_check()
    for name in inputs["source_sha256"]:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(tool.ROOT/name,path)
    assert tool.source_check(tmp_path)==inputs
    changed=tmp_path/"server/app/rl/dqn_network.py"
    changed.write_text(changed.read_text()+"\n# changed after paper freeze\n")
    with pytest.raises(ValueError,match="Frozen figure source changed"):
        tool.source_check(tmp_path)


@pytest.mark.parametrize("change",["image","missing","scope","captions","generator"])
def test_changed_assets_or_relabelled_scope_are_rejected(assets,tmp_path,change):
    output=tmp_path/"copy";shutil.copytree(assets,output)
    path=output/"manifest.json";m=json.loads(path.read_text())
    if change=="image":
        image=output/"fig01_system_architecture.png"
        image.write_bytes(image.read_bytes()+b"changed")
    elif change=="missing":
        name="fig01_system_architecture.pdf";(output/name).unlink();m["output_sha256"].pop(name)
    elif change=="scope":m["native_traffic_runs"]=1
    elif change=="generator":m["generator_sha256"][next(iter(m["generator_sha256"]))]="0"*64
    else:
        p=output/"captions.json";rows=json.loads(p.read_text());rows[0]["caption"]="Proven optimal control"
        p.write_text(json.dumps(rows));m["output_sha256"][p.name]=tool.digest(p)
    path.write_text(json.dumps(m))
    with pytest.raises(ValueError):tool.verify(output)


def test_generator_never_overwrites_existing_outputs_or_frozen_evidence(assets,tmp_path):
    before=tool.digest(assets/"manifest.json")
    with pytest.raises(FileExistsError):tool.generate(assets)
    assert tool.digest(assets/"manifest.json")==before
    evidence=tmp_path/"evidence";evidence.mkdir();(evidence/"manifest.json").write_text("{}")
    with pytest.raises(ValueError,match="frozen evidence"):tool.generate(evidence/"figures")
    assert not (evidence/"figures").exists()


@pytest.mark.parametrize("options",[dict(dpi=0),dict(dpi=601),dict(formats=("pdf","pdf")),
    dict(formats=()),dict(identifiers=["missing"]),dict(identifiers=["fig01_system_architecture"]*2)])
def test_invalid_requests_fail_before_creating_outputs(tmp_path,options):
    with pytest.raises(ValueError):tool.generate(tmp_path/"new",**options)
    assert not (tmp_path/"new").exists()


def test_svg_geometry_and_source_archive_are_deterministic(tmp_path):
    paths=[tmp_path/"a",tmp_path/"b"]
    for p in paths:tool.generate(p,["fig06_signal_execution"],("svg",),96)
    for name in ("fig06_signal_execution.svg","source_snapshot.zip"):
        assert (paths[0]/name).read_bytes()==(paths[1]/name).read_bytes()
    assert not (paths[0]/"figures.tex").exists()  # No nonexistent PDF reference.


@pytest.mark.parametrize("bad_layout",["text","overlap","page"])
def test_layout_checks_fail_for_actual_clipping_or_overlap(bad_layout):
    b=Board()
    try:
        if bad_layout=="text":b.box(1,1,.7,1,"A heading far too long for this box")
        elif bad_layout=="page":b.text(50,2,"Outside page")
        else:b.box(1,1,2,1,"First");b.box(1.5,1,2,1,"Second")
        with pytest.raises(ValueError):b.validate()
    finally:b.close()
