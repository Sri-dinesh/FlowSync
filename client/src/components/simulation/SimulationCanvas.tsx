"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

import IntersectionScene from "@/components/simulation/IntersectionScene";

export default function SimulationCanvas() {
  return (
    <div className="h-[360px] w-full">
      <Canvas
        orthographic
        shadows
        camera={{ position: [0, 10, 0], zoom: 50, near: 0.1, far: 50 }}
        onCreated={({ camera }) => {
          camera.up.set(0, 0, -1);
          camera.lookAt(0, 0, 0);
        }}
      >
        <color attach="background" args={["#0a0a0a"]} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[0, 10, 0]} intensity={0.8} castShadow />
        <IntersectionScene />
        <OrbitControls enablePan={false} enableRotate={false} enableZoom />
      </Canvas>
    </div>
  );
}
