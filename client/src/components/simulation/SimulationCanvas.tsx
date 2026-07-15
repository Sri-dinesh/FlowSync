"use client";

import { memo, useMemo, Suspense, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment, ContactShadows } from "@react-three/drei";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";

import IntersectionScene from "@/components/simulation/IntersectionScene";
import { useSimulationStore } from "@/store/simulationStore";

const SimulationCanvas = memo(function SimulationCanvas() {
  const isConnected = useSimulationStore((state) => state.isConnected);
  const isRunning = useSimulationStore((state) => state.isRunning);
  const [timeOfDay, setTimeOfDay] = useState<"day" | "night">("night");

  const statusMessage = useMemo(() => {
    if (!isConnected) {
      return "Backend Disconnected";
    }
    if (!isRunning) {
      return "Simulation Paused";
    }
    return "Live Simulation";
  }, [isConnected, isRunning]);

  const bgColor = timeOfDay === "day" ? "#f0f4f8" : "#111622";

  return (
    <div className="relative h-full w-full">
      <div className="absolute top-6 left-6 z-10 flex gap-2">
        <button 
          onClick={() => setTimeOfDay("day")}
          className={`px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all duration-300 ${timeOfDay === "day" ? 'bg-white text-black shadow-lg shadow-white/20' : 'bg-black/60 text-white/50 hover:bg-black/80 hover:text-white backdrop-blur-md border border-white/10'}`}
        >
          Day Mode
        </button>
        <button 
          onClick={() => setTimeOfDay("night")}
          className={`px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all duration-300 ${timeOfDay === "night" ? 'bg-white text-black shadow-lg shadow-white/20' : 'bg-black/60 text-white/50 hover:bg-black/80 hover:text-white backdrop-blur-md border border-white/10'}`}
        >
          Night Mode
        </button>
      </div>

      <Canvas
        orthographic
        shadows
        dpr={[1, 2]}
        camera={{ position: [20, 20, 20], zoom: 45, near: 0.1, far: 1000 }}
        onCreated={({ camera, gl }) => {
          camera.lookAt(0, 0, 0);
          gl.setClearColor(bgColor);
        }}
      >
        <color attach="background" args={[bgColor]} />
        
        <Suspense fallback={null}>
          <ambientLight intensity={timeOfDay === "day" ? 1.0 : 0.5} />
          
          <Environment preset="city" environmentIntensity={timeOfDay === "day" ? 1.0 : 0.2} />
          
          {timeOfDay === "day" ? (
             <group>
               <directionalLight 
                 position={[20, 40, 20]} 
                 intensity={2.0} 
                 castShadow 
                 shadow-mapSize-width={2048} 
                 shadow-mapSize-height={2048}
                 shadow-bias={-0.0001}
                 color="#fffcf2"
               />
               {/* Glowing Physical Sun with high emission for rays */}
               <mesh position={[-25, 30, -25]}>
                 <sphereGeometry args={[4, 32, 32]} />
                 <meshStandardMaterial 
                   color="#ffdd44" 
                   emissive="#ffaa00" 
                   emissiveIntensity={8.0} 
                   toneMapped={false} 
                 />
               </mesh>
             </group>
          ) : (
             <>
                <directionalLight 
                  position={[10, 20, 10]} 
                  intensity={1.2} 
                  castShadow 
                  shadow-mapSize-width={2048} 
                  shadow-mapSize-height={2048}
                  shadow-bias={-0.0001}
                />
                <directionalLight 
                  position={[-10, 15, -10]} 
                  intensity={0.6} 
                  color="#6b9bd1"
                />
             </>
          )}

          <hemisphereLight 
            args={timeOfDay === "day" ? ["#ffffff", "#aaaaaa", 0.8] : ["#87ceeb", "#2a2a3e", 0.4]} 
          />
          
          <IntersectionScene />
          
          <ContactShadows 
            position={[0, 0.01, 0]} 
            opacity={0.8} 
            scale={50} 
            blur={1.5} 
            far={10} 
            resolution={512} 
            color="#000000" 
          />
          
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
            autoRotate={false}
            autoRotateSpeed={0.5}
          />

          <EffectComposer>
            <Bloom 
              luminanceThreshold={timeOfDay === "day" ? 0.9 : 0.2} 
              luminanceSmoothing={0.9} 
              intensity={timeOfDay === "day" ? 1.5 : 1.5} 
            />
          </EffectComposer>
        </Suspense>
      </Canvas>
      
      {/* Dynamic Status Indicator */}
      <div className="absolute top-4 right-4 flex items-center gap-2 rounded-full border border-white/10 bg-black/60 px-3 py-1.5 backdrop-blur-md pointer-events-auto">
        <div className={`h-2 w-2 rounded-full animate-pulse ${
          !isConnected ? 'bg-rose-500' : !isRunning ? 'bg-amber-500' : 'bg-emerald-500'
        }`} />
        <span className="text-[10px] font-medium uppercase tracking-wider text-white/80">
          {statusMessage}
        </span>
      </div>

      {/* Legend overlay */}
      <div className="pointer-events-auto absolute inset-x-0 bottom-4 flex items-center justify-center gap-4 text-[10px] text-white/50 bg-black/40 backdrop-blur-md py-2 px-5 mx-auto w-fit rounded-full border border-white/5 shadow-2xl">
        <span className="flex items-center gap-2">
          <span className="h-1.5 w-3 rounded-full bg-sky-500" />
          moving
        </span>
        <span className="flex items-center gap-2">
          <span className="h-1.5 w-3 rounded-full bg-amber-400" />
          waiting
        </span>
        <span className="flex items-center gap-2">
          <span className="h-1.5 w-3 rounded-full bg-emerald-400" />
          green
        </span>
        <span className="flex items-center gap-2">
          <span className="h-1.5 w-3 rounded-full bg-rose-500" />
          red
        </span>
      </div>
      
      {/* Hint overlay - only show when disconnected or not running to encourage user action */}
      {(!isConnected || !isRunning) && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/10">
          <div className="rounded-xl border border-white/10 bg-black/40 p-6 backdrop-blur-sm text-center shadow-2xl">
            <p className="text-sm font-light tracking-[0.15em] text-white/90">
              {!isConnected ? "READY FOR CONNECTION" : "READY TO START"}
            </p>
            <p className="mt-2 text-[10px] text-white/40 uppercase tracking-widest">
              {!isConnected ? "Ensure backend server is running" : "Click the Start button to begin simulation"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
});

export default SimulationCanvas;
