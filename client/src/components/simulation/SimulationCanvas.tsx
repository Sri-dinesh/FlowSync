"use client";

import { memo, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

import IntersectionScene from "@/components/simulation/IntersectionScene";
import { useSimulationStore } from "@/store/simulationStore";

const SimulationCanvas = memo(function SimulationCanvas() {
  const isConnected = useSimulationStore((state) => state.isConnected);
  const isRunning = useSimulationStore((state) => state.isRunning);
  const lastFrameAt = useSimulationStore((state) => state.lastFrameAt);

  const overlayMessage = useMemo(() => {
    if (!isConnected) {
      return "Waiting for backend connection...";
    }
    if (!isRunning) {
      return "Click Start to run the simulation.";
    }
    if (!lastFrameAt) {
      return "Waiting for frames...";
    }
    return null;
  }, [isConnected, isRunning, lastFrameAt]);

  return (
    <div className="relative h-[420px] w-full">
      <Canvas
        orthographic
        shadows
        dpr={[1, 1.5]}
        camera={{ position: [0, 10, 0], zoom: 50, near: 0.1, far: 50 }}
        onCreated={({ camera }) => {
          camera.up.set(0, 0, -1);
          camera.lookAt(0, 0, 0);
        }}
      >
        <color attach="background" args={["#0b0f14"]} />
        <ambientLight intensity={0.75} />
        <directionalLight position={[6, 10, 4]} intensity={1} castShadow />
        <IntersectionScene />
        <OrbitControls enablePan={false} enableRotate={false} enableZoom />
      </Canvas>
      <div className="pointer-events-none absolute inset-x-0 top-2 flex justify-between px-3 text-[10px] uppercase tracking-[0.12em] text-white/35">
        <span>North</span>
        <span>East</span>
      </div>
      <div className="pointer-events-none absolute inset-x-0 bottom-2 flex items-center justify-center gap-4 text-[10px] text-white/45">
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-3 rounded-[2px] bg-slate-200" />
          vehicle
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-3 rounded-[2px] bg-blue-500" />
          ai-moved
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-3 rounded-[2px] bg-amber-400" />
          waiting
        </span>
      </div>
      {overlayMessage && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="rounded-lg border border-white/10 bg-black/60 px-4 py-2 text-xs uppercase tracking-[0.2em] text-white/70">
            {overlayMessage}
          </div>
        </div>
      )}
    </div>
  );
});

export default SimulationCanvas;
