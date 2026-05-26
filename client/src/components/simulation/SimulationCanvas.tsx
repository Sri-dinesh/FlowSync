"use client";

import { memo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { Perf } from "r3f-perf";

import IntersectionScene from "@/components/simulation/IntersectionScene";

const SimulationCanvas = memo(function SimulationCanvas() {
  return (
    <div className="h-[360px] w-full">
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
        <color attach="background" args={["#0a0a0a"]} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[0, 10, 0]} intensity={0.8} castShadow />
        {process.env.NODE_ENV === "development" && (
          <Perf position="top-left" />
        )}
        <IntersectionScene />
        <OrbitControls enablePan={false} enableRotate={false} enableZoom />
      </Canvas>
    </div>
  );
});

export default SimulationCanvas;
