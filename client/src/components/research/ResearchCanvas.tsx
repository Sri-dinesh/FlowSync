"use client";

import React, { memo, useState, Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment, ContactShadows } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { Research3DScene } from "./Research3DScene";
import type { ResearchTelemetryFrame } from "@/types/research";

interface ResearchCanvasProps {
  frameOverride?: ResearchTelemetryFrame | null;
  label?: string;
  quality?: "performance" | "high";
}

export const ResearchCanvas = memo(function ResearchCanvas({
  frameOverride,
  label,
  quality = "performance",
}: ResearchCanvasProps) {
  const [timeOfDay, setTimeOfDay] = useState<"day" | "night">("night");
  const bgColor = timeOfDay === "day" ? "#e2e8f0" : "#0d111a";

  const isPerformance = quality === "performance";

  return (
    <div className="relative w-full h-full min-h-[380px] rounded-md overflow-hidden border border-neutral-800 bg-[#0d111a]">
      {/* Top Overlay Controls */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <button
          onClick={() => setTimeOfDay((prev) => (prev === "day" ? "night" : "day"))}
          className="px-2.5 py-1 rounded-md text-[10px] font-bold font-mono uppercase tracking-wider bg-black/60 hover:bg-black/80 text-white/70 hover:text-white backdrop-blur-md border border-white/10 transition-all"
        >
          {timeOfDay === "day" ? "Mode: Day" : "Mode: Night"}
        </button>

        {label && (
          <div className="px-3 py-1 rounded-md text-[11px] font-bold font-mono tracking-wide bg-indigo-950/80 text-indigo-200 border border-indigo-500/30 backdrop-blur-md">
            {label}
          </div>
        )}
      </div>

      <Canvas
        orthographic
        shadows={!isPerformance}
        dpr={isPerformance ? [1, 1.25] : [1, 1.5]}
        performance={{ min: 0.5 }}
        gl={{ powerPreference: "high-performance", antialias: !isPerformance, alpha: false }}
        camera={{ position: [22, 22, 22], zoom: 42, near: 0.1, far: 1000 }}
        onCreated={({ camera, gl }) => {
          camera.lookAt(0, 0, 0);
          gl.setClearColor(bgColor);
        }}
      >
        <color attach="background" args={[bgColor]} />

        <Suspense fallback={null}>
          <ambientLight intensity={timeOfDay === "day" ? 1.0 : 0.4} />

          <Environment preset="city" environmentIntensity={timeOfDay === "day" ? 0.9 : 0.2} />

          {timeOfDay === "day" ? (
            <directionalLight
              position={[20, 35, 20]}
              intensity={1.8}
              castShadow={!isPerformance}
              shadow-mapSize-width={1024}
              shadow-mapSize-height={1024}
              color="#fffcf2"
            />
          ) : (
            <directionalLight position={[10, 20, 10]} intensity={1.1} castShadow={!isPerformance} color="#93c5fd" />
          )}

          <hemisphereLight
            args={timeOfDay === "day" ? ["#ffffff", "#94a3b8", 0.8] : ["#60a5fa", "#1e1b4b", 0.35]}
          />

          <Research3DScene frameOverride={frameOverride} label={label} />

          {!isPerformance && (
            <ContactShadows
              frames={1}
              position={[0, 0.01, 0]}
              opacity={0.7}
              scale={50}
              blur={1.5}
              far={10}
              resolution={512}
              color="#000000"
            />
          )}

          <OrbitControls
            makeDefault
            enablePan={true}
            enableRotate={true}
            enableZoom={true}
            target={[0, 0, 0]}
            maxPolarAngle={Math.PI / 2 - 0.05}
            minPolarAngle={0.1}
            maxZoom={120}
            minZoom={15}
          />

          {!isPerformance && (
            <EffectComposer multisampling={0}>
              <Bloom luminanceThreshold={0.8} luminanceSmoothing={0.9} intensity={1.2} />
            </EffectComposer>
          )}
        </Suspense>
      </Canvas>
    </div>
  );
});
