"""Research-only observed-input ridge correction of a frozen D3QN parent."""
from dataclasses import replace
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

from server.app.controllers.d3qn import D3QNController
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.max_pressure import MOVEMENT_INDEX, PHASE_MOVEMENTS
from server.app.rl.observations import encode_policy_observation
from server.app.simulation.traffic_math import DEST_MAP

FEATURES = ("demand", "downstream", "service_timer", "is_current", "current_age",
            "current_demand_age", "left_phase", "q_gap")
TARGET_SCALE = np.array([40.,1.,40.])
RIDGE = 10.
BOOTSTRAPS = 20


def action_features(observation, phase, age, q_values, parent, candidate):
    obs=np.asarray(observation,dtype=float); q=np.asarray(q_values,dtype=float)
    if obs.shape!=(36,) or q.shape!=(4,) or not np.isfinite(obs).all() or not np.isfinite(q).all():
        raise ValueError("Ranking requires finite v7 inputs and four Q values")
    if not all(isinstance(a,(int,np.integer)) and 0<=a<4 for a in (phase,parent,candidate)) or not np.isfinite(age) or age<0:
        raise ValueError("Invalid phase/age")
    directions={d:i for i,d in enumerate(("north","south","east","west"))}
    normalized_age=min(age,80.)/40.
    def phi(action):
        movements=PHASE_MOVEMENTS[action]
        demand=float(np.mean([obs[MOVEMENT_INDEX[m]] for m in movements]))
        downstream=float(np.mean([obs[28+directions[DEST_MAP[m]]] for m in movements]))
        current=float(action==phase)
        return np.array([demand,downstream,obs[32+action],current,current*normalized_age,
                         current*demand*normalized_age,float(action>=2),np.clip((q[action]-q[parent])/20.,-5,5)])
    return phi(candidate)-phi(parent)


def examples(rows):
    xs,ys,groups=[],[],[]
    for row in rows:
        if row["split"]!="train":
            raise ValueError("Only training labels may fit ranking")
        group=f"{row['scenario']}/{row['seed']}/{row['fault']['name']}"
        for event in row["events"]:
            branches=event.get("all_action_branches",[])
            if not branches:
                continue
            parent=event["policy_proposal"]
            base=next(b["outcome"] for b in branches if b["proposal"]==parent)
            for b in branches:
                action=b["proposal"]
                if action==parent:
                    continue
                out=b["outcome"]
                xs.append(action_features(event["policy_observation"],event["phase"],event["phase_age"],
                                          event["q_values"],parent,action))
                ys.append([base["incremental_delay_vehicle_seconds"]-out["incremental_delay_vehicle_seconds"],
                           out["vehicles_passed"]-base["vehicles_passed"],base["upstream_max_wait_s"]-out["upstream_max_wait_s"]])
                groups.append(group)
    x,y=np.asarray(xs),np.asarray(ys)
    if len(xs)<8 or len(set(groups))<4 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Insufficient/non-finite ranking labels")
    return x,y,np.asarray(groups)


def fit_model(rows, seed, checkpoint_hash):
    if {r["training_seed"] for r in rows}!={seed} or {r["checkpoint_hash"] for r in rows}!={checkpoint_hash}:
        raise ValueError("Mixed parent labels")
    x,y,groups=examples(rows)
    unique,counts=np.unique(groups,return_counts=True)
    weight=np.array([1./counts[np.flatnonzero(unique==g)[0]] for g in groups])
    scale=np.maximum(np.sqrt(np.average(x*x,axis=0,weights=weight)),.05)
    z=x/scale; targets=y/TARGET_SCALE
    def solve(w):
        w=w/w.mean()
        return np.linalg.solve(z.T@(w[:,None]*z)+RIDGE*np.eye(len(FEATURES)),z.T@(w[:,None]*targets))
    point=solve(weight)
    rng=np.random.default_rng(88000+seed)
    ensemble=[]
    for _ in range(BOOTSTRAPS):
        sampled=rng.choice(unique,size=len(unique),replace=True)
        w=weight*np.array([np.count_nonzero(sampled==g) for g in groups])
        ensemble.append(solve(w).tolist())
    return dict(version="action_rank_ridge_v1",features=list(FEATURES),parent_sha256=checkpoint_hash,
        seed=seed,scale=scale.tolist(),point=point.tolist(),ensemble=ensemble,ridge=RIDGE,
        target_scale=TARGET_SCALE.tolist(),fit_examples=len(x),fit_source_groups=len(unique),
        training_only=True,uncertainty="uncalibrated source-trajectory bootstrap 10th percentile")


class RankingModel:
    def __init__(self,payload):
        self.payload=payload
        self.scale=np.asarray(payload["scale"],dtype=float)
        self.point=np.asarray(payload["point"],dtype=float)
        self.ensemble=np.asarray(payload["ensemble"],dtype=float)
        if (payload.get("version")!="action_rank_ridge_v1" or payload.get("features")!=list(FEATURES)
            or payload.get("target_scale")!=TARGET_SCALE.tolist() or self.scale.shape!=(8,)
            or self.point.shape!=(8,3) or self.ensemble.shape!=(BOOTSTRAPS,8,3)
            or not all(np.isfinite(a).all() for a in (self.scale,self.point,self.ensemble))
            or not (self.scale>0).all()):
            raise ValueError("Invalid ranking model")

    def choose(self,observation,phase,age,q_values,parent,mask,variant):
        if variant not in ("mean","uncertain"):
            raise ValueError("Unknown ranking variant")
        valid=np.asarray(mask,dtype=bool)
        if valid.shape!=(4,) or not isinstance(parent,(int,np.integer)) or not 0<=parent<4 or not valid[parent]:
            return parent,{}
        predictions={}
        try:
            for action in np.flatnonzero(valid):
                action=int(action)
                if action==parent:
                    continue
                x=action_features(observation,phase,age,q_values,parent,action)/self.scale
                gain=(x@self.point if variant=="mean" else
                      np.quantile(np.einsum("f,bft->bt",x,self.ensemble),.1,axis=0))*TARGET_SCALE
                if not np.isfinite(gain).all():
                    return parent,{}
                predictions[action]=gain.tolist()
        except (ValueError,TypeError,IndexError):
            return parent,{}
        qualifying=[a for a,g in predictions.items() if g[0]>1. and g[1]>=0 and g[2]>=-1.]
        choice=max(qualifying,key=lambda a:(predictions[a][0],-a)) if qualifying else parent
        return choice,predictions


class RankedD3QN(D3QNController):
    def __init__(self,checkpoint_path,model_path,variant):
        super().__init__(checkpoint_path=str(checkpoint_path))
        raw=Path(model_path).read_bytes()
        self.ranking=RankingModel(json.loads(raw))
        if self.agent.obs_version!="v7_36dim_observed" or self.ranking.payload["parent_sha256"]!=self._checkpoint_hash:
            raise ValueError("Ranking model does not match v7 parent")
        if variant not in ("mean","uncertain"):
            raise ValueError("Unknown ranking variant")
        self.variant=variant; self.ranking_hash=hashlib.sha256(raw).hexdigest()
        self.rank_evaluations=self.rank_corrections=0

    def reset(self,seed=None):
        super().reset(seed)
        self.rank_evaluations=self.rank_corrections=0

    def act(self,observation,context):
        gate=context.is_decision_step and context.timestep>=self._next_decision_step
        parent=super().act(observation,context)
        if not gate:
            return parent
        encoded=encode_policy_observation(observation,context,self.agent.obs_version)
        mask=context.valid_action_mask if context.valid_action_mask is not None else np.ones(4,dtype=bool)
        choice,predictions=self.ranking.choose(encoded,context.current_phase,context.time_in_phase,
            self._last_diagnostics["q_values"],parent,mask,self.variant)
        self.rank_evaluations+=1; self.rank_corrections+=int(choice!=parent)
        self._held_action=choice
        self._last_diagnostics.update(selected_action=choice,parent_action=parent,rank_predictions=predictions)
        return choice


class ActionRankController(FlowSyncUQController):
    def __init__(self,checkpoint_path,model_path,variant):
        policy=RankedD3QN(checkpoint_path,model_path,variant)
        super().__init__(d3qn_controller=policy,enable_shield=True,enable_fallback=False)
        self.name=f"action_rank_{variant}"
        self.rank_executed_changes=0

    def reset(self,seed=None):
        super().reset(seed)
        self.rank_executed_changes=0

    def act(self,observation,context):
        gate=context.is_decision_step and context.timestep>=self.d3qn._next_decision_step
        executed=super().act(observation,context)
        if gate:
            parent=self.d3qn.get_diagnostics()["parent_action"]
            parent_executed=copy.deepcopy(self.safety_shield).filter_context(parent,context).executed_action
            self.rank_executed_changes+=int(executed!=parent_executed)
        return executed

    def get_capabilities(self):
        return replace(super().get_capabilities(),name=self.name,supports_fallback=False,
                       description="Experimental action-ranking correction; unchanged physical shield")

    def get_diagnostics(self):
        return {**super().get_diagnostics(),"ranking_model_sha256":self.d3qn.ranking_hash,
                "rank_evaluations":self.d3qn.rank_evaluations,"rank_corrections":self.d3qn.rank_corrections,
                "rank_executed_changes":self.rank_executed_changes}
