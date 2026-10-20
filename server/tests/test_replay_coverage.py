"""Coverage selection and continuation checks; fixtures are not evidence."""
import copy
import json

import pytest

from research.audit_replay_coverage import ARMS, EXTRA_ONLINE, SEEDS, STEPS, extra_cases, summarize


@pytest.fixture
def records(tmp_path):
    scenario=dict(scenario_id="train_fixture",split="train",name="fixture",description="fixture",
                  duration_steps=1200,topology="single_intersection",demand_profile={})
    demos=[dict(executed_scenario=scenario,seed=100+i,fault={}) for i in range(24)]
    logs=[dict(executed_scenario=scenario,seed=1000+i,episode=i,fault={}) for i in range(1,91)]
    (tmp_path/"demonstrations.jsonl").write_text("\n".join(map(json.dumps,demos)))
    (tmp_path/"training.jsonl").write_text("\n".join(map(json.dumps,logs)))
    original=[dict(seed=100+i) for i in range(6)]+[dict(seed=1000+i) for i in (1,16,31,46,61,76)]
    return tmp_path,original


def test_selection_fixed_in_advance_excludes_all_original_cases(records):
    path,original=records
    cases=extra_cases(path,original)
    assert len(cases)==12 and all(c["partition"]=="fit" for c in cases)
    assert [c["seed"] for c in cases[:6]]==list(range(106,112))
    assert [c["seed"] for c in cases[6:]]==[1000+i for i in EXTRA_ONLINE]
    assert not {c["seed"] for c in cases}&{c["seed"] for c in original}


@pytest.mark.parametrize("mutation,match",[("overlap","Overlapping"),("test","Only training"),("duplicate","Missing/duplicate")])
def test_reject_leakage_and_duplicate_records(records,mutation,match):
    path,original=records
    logs=[json.loads(s) for s in (path/"training.jsonl").read_text().splitlines()]
    if mutation=="overlap":
        logs[1]["seed"]=original[-1]["seed"]
    elif mutation=="test":
        logs[1]["executed_scenario"]["split"]="test"
    else:
        logs.append(copy.deepcopy(logs[0]))
    (path/"training.jsonl").write_text("\n".join(map(json.dumps,logs)))
    with pytest.raises(ValueError,match=match):
        extra_cases(path,original)


def curves():
    return [dict(seed=s,arm=a,updates=u,dataset_sha256=str(s),metrics={part:dict(
        fixed_label_mae=10. if u==0 else (12. if a=="narrow" else 9.),
        frozen_joint_objective=10. if u==0 else (12. if a=="narrow" else 9.))
        for part in ("fit","probe","expanded_fit")}) for s in SEEDS for a in ARMS for u in STEPS]


def test_screen_requires_parent_improvement_not_just_less_overfitting():
    rows=curves()
    assert summarize(rows)["promising_for_validation"]
    for r in rows:
        if r["arm"]=="broader" and r["updates"]==200:
            r["metrics"]["probe"]["fixed_label_mae"]=11.
    result=summarize(rows)
    assert result["checks"]["mean_probe_mae_five_percent_better_vs_narrow"]
    assert not result["promising_for_validation"]
    assert not result["publication_ready"]


@pytest.mark.parametrize("mutation,match",[("missing","Incomplete"),("initial","Unpaired initial"),
                                          ("hash","Unpaired dataset"),("nan","Non-finite")])
def test_reject_invalid_curves(mutation,match):
    rows=curves()
    if mutation=="missing": rows.pop()
    elif mutation=="initial": rows[0]["metrics"]["probe"]["fixed_label_mae"]=99.
    elif mutation=="hash": rows[0]["dataset_sha256"]="different"
    else: rows[-1]["metrics"]["probe"]["fixed_label_mae"]=float("nan")
    with pytest.raises(ValueError,match=match):
        summarize(rows)
