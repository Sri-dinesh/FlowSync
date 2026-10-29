"""Research-only causal count restoration from delivered packet history."""
from collections import deque
import hashlib

import numpy as np
import torch
from torch import nn

from research.noise.fault_injector import PerceptionFaultInjector
from server.app.simulation.traffic_math import MOVEMENT_KEYS
from server.app.simulation.traffic_signal import PHASE_DEMAND_MOVEMENTS

VERSION = "causal_count_restoration_v1"
FEATURE_DIM = 17
EMA_ALPHAS = (.2, .5, .8, 1.)


def counts(observation):
    return np.rint(15*np.arctanh(np.clip(np.asarray(observation)[:12],0,.999999))).astype(np.float32)


def update_ema(previous,raw,alpha):
    alpha=np.asarray(alpha,dtype=np.float32)
    return alpha*raw+(np.float32(1)-alpha)*previous


class PacketHistory:
    """Only delivered counts, packet age/drop and authoritative lamp feedback."""
    def __init__(self): self.reset()

    def reset(self):
        self.history=deque(maxlen=11)
        self.last_step=None

    def update(self,observation,context):
        step=context.timestep
        if self.last_step is not None and step<=self.last_step:
            raise ValueError("Restoration history must advance; reset between runs.")
        if self.last_step is not None and step!=self.last_step+1: self.history.clear()
        self.last_step=step
        raw=counts(observation)
        self.history.append((step,raw.copy()))
        lookup=dict(self.history)
        values=np.stack([row for _,row in self.history])
        features=np.zeros((12,FEATURE_DIM),dtype=np.float32)
        features[:,0]=raw/15
        for column,lag in enumerate((1,5,10),1):
            if step-lag in lookup:
                features[:,column]=lookup[step-lag]/15
                features[:,10+column]=1
        features[:,4]=values.mean(axis=0)/15
        features[:,5]=values.max(axis=0)/15
        features[:,6]=values.min(axis=0)/15
        served=PHASE_DEMAND_MOVEMENTS.get(context.current_phase,()) if context.color=="GREEN" else ()
        features[:,7]=[float(m in served) for m in MOVEMENT_KEYS]
        features[:,8]=min(max(context.time_in_phase,0)/45,1)
        features[:,9]=min(max(context.extra_telemetry.get("observation_age_ms",0),0)/5000,1)
        features[:,10]=float(context.extra_telemetry.get("frame_dropped",False))
        for i in range(12): features[i,14+i%3]=1
        return features


class CountRestorer(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(FEATURE_DIM,32),nn.ReLU(),nn.Linear(32,32),nn.ReLU(),nn.Linear(32,1))
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self,features):
        estimate=features[...,0]*15+15*self.net(features).squeeze(-1)
        estimate=torch.minimum(estimate.clamp(min=0),features[...,5]*15+2)
        return estimate*(features[...,5]>0)


def predict(model,features):
    with torch.no_grad():
        result=model(torch.as_tensor(features,dtype=torch.float32)).cpu().numpy()
    if not np.isfinite(result).all(): raise ValueError("Nonfinite count-restoration output.")
    return np.rint(result).astype(np.float32)


class RestorationInjector:
    """Corrupt first, then restore. Clean input is passed only to the injector."""
    def __init__(self,profile,seed,model_path=None,alpha=None):
        if (model_path is None)==(alpha is None): raise ValueError("Choose one model or EMA.")
        if alpha is not None and not 0<alpha<=1: raise ValueError("EMA alpha must be in (0,1].")
        self.base=PerceptionFaultInjector(profile,seed=seed)
        self.seed=seed
        self.alpha=alpha
        self.model=None
        self.model_sha256=None
        if model_path is not None:
            payload=torch.load(model_path,map_location="cpu",weights_only=True)
            if payload["schema_version"]!=VERSION: raise ValueError("Incompatible restoration checkpoint.")
            self.model=CountRestorer()
            self.model.load_state_dict(payload["state_dict"],strict=True)
            self.model.eval()
            self.model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest()
        self.reset(seed)

    def reset(self,seed=None):
        if seed is not None: self.seed=seed
        self.base.reset(self.seed)
        self.history=PacketHistory()
        self.ema=None
        self.changed_packets=0
        self.absolute_correction=0.

    def restore_delivered(self,delivered,context):
        # This interface intentionally has no clean observation or fault profile.
        raw=counts(delivered)
        if self.model is not None:
            restored=predict(self.model,self.history.update(delivered,context))
        else:
            self.ema=raw.copy() if self.ema is None else update_ema(self.ema,raw,self.alpha)
            restored=np.rint(self.ema)
        changed=restored!=raw
        result=delivered.copy()
        result[:12][changed]=np.tanh(restored[changed]/15)
        self.changed_packets+=int(changed.any())
        self.absolute_correction+=float(np.abs(restored-raw).sum())
        return result

    def corrupt_observation(self,clean_obs,step=0,context=None,*,upstream_counts=None):
        if context is None or upstream_counts is not None:
            raise ValueError("Restoration pilot requires a v6/v7 delivery context, not spatial inputs.")
        delivered=self.base.corrupt_observation(clean_obs,step,context)
        return self.restore_delivered(delivered,context)

    def get_realized_diagnostics(self):
        return {**self.base.get_realized_diagnostics(),"restoration_schema":VERSION,
                "restoration_sha256":self.model_sha256,"ema_alpha":self.alpha,
                "restored_packets":self.changed_packets,"absolute_count_correction":self.absolute_correction}
