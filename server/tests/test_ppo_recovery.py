import json

import numpy as np
import pytest
import torch

from research.pilots.recover_ppo_restoration_pilot import advance_sampler, rebuild
from research.pilots.run_ppo_restoration_pilot import store_batch, optimizers, sha, write
from research.policies.ppo import ActorCritic, save_checkpoint
from research.training.ppo import Transition, update
from research.training.train_policy import RunBudget


def test_sampler_recovery_replays_every_proposal_including_final_partial():
    expected = torch.Generator().manual_seed(101)
    summaries = []
    for probabilities in ([.1, .2, .3, .4], [1., 0., 0., 0.], [.4, .3, .2, .1]):
        action = int(torch.multinomial(torch.tensor(probabilities), 1, generator=expected)[0])
        summaries.append(dict(proposals=[dict(probabilities=probabilities, proposed=action)]))
    actual = torch.Generator().manual_seed(101)
    advance_sampler(actual, json.loads(json.dumps(summaries)))
    assert torch.equal(expected.get_state(), actual.get_state())
    summaries[0]["proposals"][0]["proposed"] = (summaries[0]["proposals"][0]["proposed"]+1) % 4
    with pytest.raises(ValueError, match="Sampler replay"):
        advance_sampler(torch.Generator().manual_seed(101), summaries)


def test_rebuild_exact_optimizer_and_sampler_at_last_committed_batch(tmp_path, monkeypatch):
    torch.set_num_threads(1)
    monkeypatch.setattr(ActorCritic, "from_parent", classmethod(lambda cls, path: cls()))
    torch.manual_seed(101)
    model = ActorCritic()
    actor, critic = optimizers(model)
    generator = torch.Generator().manual_seed(101)
    summaries, episodes = [], []
    for episode in range(6):
        state = np.zeros(36, np.float32)
        mask = np.ones(4, bool)
        policy = model.distribution(torch.as_tensor(state)[None], torch.as_tensor(mask)[None])
        proposals = []
        for _ in range(2):  # Complete transition plus dropped final macro proposal.
            action = int(torch.multinomial(policy.probs[0], 1, generator=generator)[0])
            proposals.append(dict(probabilities=policy.probs[0].tolist(), proposed=action))
        action = proposals[0]["proposed"]
        logp = float(policy.log_prob(torch.tensor([action])).detach()[0])
        episodes.append([Transition(state, mask, action, logp, 0., 1., 20, 0., state.copy())])
        summaries.append(dict(episode=episode+1, proposals=proposals))
    expected_sampler = generator.get_state().clone()
    store_batch(tmp_path/"batch_6.npz", episodes)
    logs = update(model, episodes, actor, critic, RunBudget(30), warmup=True)
    write(tmp_path/"updates.json", [dict(episode=6, batch_sha256=sha(tmp_path/"batch_6.npz"), updates=logs)])
    save_checkpoint(tmp_path/"checkpoint_6.pt", model, dict(episode=6))
    # An uncommitted seventh episode must not advance the recovered sampler.
    summaries.append(dict(episode=7, proposals=summaries[0]["proposals"]))
    (tmp_path/"episodes.jsonl").write_text("".join(json.dumps(s)+"\n" for s in summaries))
    restored, _, restored_critic, sampler, _, persisted, completed = rebuild(tmp_path, "101", RunBudget(30))
    assert completed == 6 and len(persisted) == 7
    assert all(torch.equal(value, restored.state_dict()[key]) for key, value in model.state_dict().items())
    assert torch.equal(sampler.get_state(), expected_sampler)
    original_state, recovered_state = critic.state_dict()["state"], restored_critic.state_dict()["state"]
    assert original_state.keys() == recovered_state.keys()
    assert all(torch.equal(value, recovered_state[key][field]) for key, fields in original_state.items()
               for field, value in fields.items())
