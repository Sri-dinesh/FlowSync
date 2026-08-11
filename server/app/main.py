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
from .routers.cctv import router as cctv_router
from .services import model_service, supabase_service
from .simulation.environment import TrafficEnv
from .websockets.simulation_ws import simulation_socket
from .websockets.city_ws import city_socket
from .websockets.training_ws import broadcast_training_metric, training_socket
from .websockets.cctv_ws import cctv_socket

from .simulation.intersection import Intersection

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # --- Simulation environment (used by /ws/simulation only) ---
    sim_intersection = Intersection()

    # --- Training environment (used by Trainer only, completely separate) ---
    training_env = TrafficEnv()
    
    # --- City Environment ---
    from .simulation.city_network import CityNetwork
    from .simulation.city_spawner import CitySpawner
    city_network = CityNetwork()
    city_spawner = CitySpawner()
    
    # Inference agent — used by /ws/simulation for live AI decisions
    sim_agent = DQNAgent()
    
    # Training agent — used exclusively by Trainer
    training_agent = DQNAgent()

    trainer = Trainer(
        env=training_env,
        agent=training_agent,
        supabase_service=supabase_service,
        model_service=model_service,
        ws_broadcast_fn=broadcast_training_metric,
        app_state=app.state,
    )

    app.state.sim_intersection = sim_intersection
    app.state.training_env = training_env
    app.state.sim_agent = sim_agent
    app.state.training_agent = training_agent
    app.state.trainer = trainer
    app.state.supabase_service = supabase_service
    app.state.model_service = model_service
    app.state.city_network = city_network
    app.state.city_spawner = city_spawner
    app.state.mode = "fixed"
    app.state.sim_running = False
    app.state.current_simulation_id = None
    app.state.sim_task = None
    app.state.training_task = None

    # --- CCTV / Real-World ---
    try:
        from .realworld.pipeline.yolo_detector import YOLODetector
        from .realworld.pipeline.roi_manager import ROIManager
        yolo_detector = YOLODetector()
        await yolo_detector.load_model()  # loads best.pt or pretrained fallback
        warmup_ms = await yolo_detector.warmup()
        print(f"[CCTV] YOLO detector ready on {yolo_detector.device} (warmup: {warmup_ms:.0f}ms)")
        app.state.yolo_detector = yolo_detector
        app.state.roi_manager = ROIManager()
    except Exception as e:
        print(f"[CCTV] YOLODetector init skipped (install ultralytics): {e}")
        app.state.yolo_detector = None
        app.state.roi_manager = None

    yield

    trainer.stop()

    # Graceful CCTV shutdown
    if hasattr(app.state, 'cctv_pipeline') and app.state.cctv_pipeline is not None:
        await app.state.cctv_pipeline.stop()


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
app.include_router(cctv_router)

app.add_api_websocket_route("/ws/simulation", simulation_socket)
app.add_api_websocket_route("/ws/training", training_socket)
app.add_api_websocket_route("/ws/city", city_socket)
app.add_api_websocket_route("/ws/cctv", cctv_socket)


@app.get("/")
def root() -> dict:
    return {"status": "ok", "service": "FlowSync API"}


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
