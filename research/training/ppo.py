"""On-policy completed-macro rollouts and clipped policy-gradient updates.

GAE: Schulman et al., https://arxiv.org/abs/1506.02438. Discounts and trace
decay are raised to elapsed macro duration / the nominal two-second interval.
"""
from dataclasses import dataclass
import hashlib
import json

import numpy as np
import torch

from research.experiments.runtime import ObservedState, SignalAudit, apply_scenario_step, build_environment
from research.policies.ppo import DECISION_TICKS
from server.app.controllers.safety_shield import SafetyShield
from server.app.rl.observations import OBSERVED_VERSION, encode_policy_observation

GAMMA, LAMBDA = .99, .95


@dataclass
class Transition:
    state: np.ndarray
    mask: np.ndarray
    action: int  # The sampled proposal, including when the shield overrides it.
    log_probability: float
    value: float
    reward: float
    ticks: int
    next_value: float
    next_state: np.ndarray | None = None


def advantages(transitions):
    """One episode only. Its final complete transition bootstraps its own next gate."""
    result = np.zeros(len(transitions), dtype=np.float32)
    following = 0.
    for i in reversed(range(len(transitions))):
        t = transitions[i]
        if t.ticks < DECISION_TICKS:
            raise ValueError("Incomplete macro-action cannot enter PPO")
        duration = t.ticks / DECISION_TICKS
        delta = t.reward + GAMMA ** duration * t.next_value - t.value
        following = delta + (GAMMA * LAMBDA) ** duration * following
        result[i] = following
    return result, result + np.asarray([t.value for t in transitions], dtype=np.float32)


def collect_episode(model, scenario, seed, injector, generator, budget):
    if scenario.split != "train":
        raise ValueError("PPO rollouts are restricted to training scenarios")
    env, profile = build_environment(scenario)
    obs, _ = env.reset(seed=seed)
    sensor, shield, audit = ObservedState(), SafetyShield(), SignalAudit()
    pending, held_action, rows, proposals = None, 0, [], []
    total_reward, overrides, dropped = 0., 0, 0
    arrivals = hashlib.sha256()
    for step in range(scenario.duration_steps + 1):
        budget.check("PPO rollout")
        if step < scenario.duration_steps:
            apply_scenario_step(env.intersection, profile, scenario.demand_profile, step)
        delivered, ctx = sensor.build(env, obs, step, injector)
        state = encode_policy_observation(delivered, ctx, OBSERVED_VERSION)
        gate = ctx.is_decision_step and (pending is None or pending.ticks >= DECISION_TICKS)
        if pending is not None and gate:
            pending.next_state = state.copy()
            with torch.no_grad():
                pending.next_value = float(model.values(torch.as_tensor(state).unsqueeze(0))[0])
            rows.append(pending)
            pending = None
        if step == scenario.duration_steps:
            dropped = pending.ticks if pending else 0
            break
        if gate:
            states = torch.as_tensor(state).unsqueeze(0)
            masks = torch.as_tensor(ctx.valid_action_mask, dtype=torch.bool).unsqueeze(0)
            with torch.no_grad():
                policy = model.distribution(states, masks)
                # Local RNG: resetting/seeding the traffic environment cannot
                # restart policy exploration or couple it to arrival randomness.
                action = torch.multinomial(policy.probs[0], 1, generator=generator)
                held_action = int(action[0])
                logp = float(policy.log_prob(action)[0])
                value = float(model.values(states)[0])
            pending = Transition(state.copy(), ctx.valid_action_mask.copy(), held_action,
                                 logp, value, 0., 0, 0.)
            proposals.append(dict(step=step, proposed=held_action, mask=pending.mask.tolist(),
                                  probabilities=policy.probs[0].tolist(), value=value))
        requested = held_action if ctx.is_decision_step else ctx.current_phase
        decision = shield.filter_context(requested, ctx)
        overrides += int(decision.executed_action != requested)
        if gate:
            proposals[-1]["executed"] = decision.executed_action
        signal = env.intersection.signal
        before = signal.current_phase, signal.color.name, signal.time_in_phase
        obs, reward, _, _, _ = env.step(decision.executed_action)
        audit.observe(before, signal)
        arrivals.update(json.dumps([step, env.intersection.spawner.generated_movements_last_tick]).encode())
        total_reward += reward
        if pending is not None:
            pending.reward += GAMMA ** (pending.ticks / DECISION_TICKS) * reward
            pending.ticks += 1
    return rows, dict(seed=seed, scenario=scenario.to_dict(), transitions=len(rows), proposals=proposals,
        reward=total_reward, avg_delay=env.intersection.get_avg_wait_time(), passed=env.intersection.total_passed,
        dropped_partial_ticks=dropped, shield_override_ticks=overrides, shield=shield.get_audit_metrics(),
        signal_samples=audit.samples, signal_violations=audit.conflicts+audit.clearance_violations,
        arrival_trace_hash=arrivals.hexdigest(),
        fault_diagnostics=injector.get_realized_diagnostics(), reward_components=dict(env.reward_component_accumulators))


def batch_data(episodes):
    episodes = [episode for episode in episodes if episode]
    if not episodes:
        raise ValueError("No complete decisions collected")
    rows = [t for episode in episodes for t in episode]
    targets = [advantages(episode) for episode in episodes]  # Never trace across resets.
    advantage = torch.as_tensor(np.concatenate([item[0] for item in targets]))
    return dict(states=torch.as_tensor(np.stack([t.state for t in rows])),
                masks=torch.as_tensor(np.stack([t.mask for t in rows])),
                actions=torch.tensor([t.action for t in rows]),
                old_logp=torch.tensor([t.log_probability for t in rows]),
                returns=torch.as_tensor(np.concatenate([item[1] for item in targets])),
                advantages=(advantage-advantage.mean())/(advantage.std(unbiased=False)+1e-8))


def clipped_loss(new_logp, old_logp, advantage, clip=.2):
    ratio = (new_logp-old_logp).exp()
    return -torch.minimum(ratio*advantage, ratio.clamp(1-clip, 1+clip)*advantage).mean()


def update(model, episodes, actor_optimizer, critic_optimizer, budget, warmup=False):
    data = batch_data(episodes)
    with torch.no_grad():
        actual = model.distribution(data["states"], data["masks"]).log_prob(data["actions"])
        if not torch.allclose(actual, data["old_logp"], rtol=1e-4, atol=1e-4):
            raise ValueError("PPO batch is not on-policy: old proposal log probabilities differ")
    logs = []
    for epoch in range(0 if warmup else 4):
        budget.check("PPO actor update")
        policy = model.distribution(data["states"], data["masks"])
        logp = policy.log_prob(data["actions"])
        delta = logp-data["old_logp"]
        approx_kl = float(((delta.exp()-1)-delta).mean().detach())
        if approx_kl > .02:
            logs.append(dict(kind="actor_kl_stop", epoch=epoch, approx_kl=approx_kl))
            break
        entropy = policy.entropy().mean()
        loss = clipped_loss(logp, data["old_logp"], data["advantages"]) - .01*entropy
        actor_optimizer.zero_grad(set_to_none=True)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.actor.parameters(), .5, error_if_nonfinite=True)
        actor_optimizer.step()
        logs.append(dict(kind="actor", epoch=epoch, loss=float(loss.detach()), entropy=float(entropy.detach()),
            approx_kl=approx_kl, clip_fraction=float((delta.exp().sub(1).abs()>.2).float().mean().detach()), grad_norm=float(norm)))
    if not warmup:
        with torch.no_grad():
            policy = model.distribution(data["states"], data["masks"])
            delta = policy.log_prob(data["actions"])-data["old_logp"]
            logs.append(dict(kind="actor_after", approx_kl=float(((delta.exp()-1)-delta).mean()),
                             entropy=float(policy.entropy().mean())))
    for epoch in range(20 if warmup else 8):
        budget.check("PPO critic update")
        prediction = model.values(data["states"])
        loss = .5*(prediction-data["returns"]).square().mean()
        critic_optimizer.zero_grad(set_to_none=True)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.critic.parameters(), .5, error_if_nonfinite=True)
        critic_optimizer.step()
        logs.append(dict(kind="critic", epoch=epoch, loss=float(loss.detach()), grad_norm=float(norm)))
    return logs
