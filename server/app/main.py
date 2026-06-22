from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .rl.dqn_agent import DQNAgent
from .rl.trainer import Trainer
from .routers.metrics import router as metrics_router
from .routers.simulation import router as simulation_router
from .routers.training import router as training_router
from .services import model_service, supabase_service
from .simulation.environment import TrafficEnv
from .websockets.simulation_ws import simulation_socket
from .websockets.training_ws import broadcast_training_metric, training_socket

app_state: dict = {
    "env": None,
    "agent": None,
    "trainer": None,
    "intersection": None,
    "sim_running": False,
    "mode": "fixed",
    "current_simulation_id": None,
    "sim_task": None,
    "training_task": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    env = TrafficEnv()
    agent = DQNAgent()
    trainer = Trainer(
        env,
        agent,
        supabase_service,
        model_service,
        broadcast_training_metric,
    )

    app_state.update(
        {
            "env": env,
            "agent": agent,
            "trainer": trainer,
            "intersection": env.intersection,
        }
    )
    app.state.app_state = app_state
    yield


app = FastAPI(lifespan=lifespan)

_allowed_origins = settings.cors_origins_list()

_allow_origin_regex = r"https?://.*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation_router)
app.include_router(training_router)
app.include_router(metrics_router)

app.add_api_websocket_route("/ws/simulation", simulation_socket)
app.add_api_websocket_route("/ws/training", training_socket)


@app.get("/")
def root() -> dict:
    return {"status": "ok", "service": "FlowSync API"}


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
