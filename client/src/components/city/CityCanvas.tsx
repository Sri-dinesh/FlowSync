"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Text, Billboard } from "@react-three/drei";
import type {
  CityFrame,
  CityIntersectionState,
} from "@/types/city";
import CityGrid from "@/components/city/CityGrid";
import CityRoads from "@/components/city/CityRoads";
import CityVehicle from "@/components/city/CityVehicle";
import TrafficLight from "@/components/simulation/TrafficLight";

// ── Constants ─────────────────────────────────────────────────────────────────
const INTERSECTION_POSITIONS: Record<string, [number, number, number]> = {
  A: [-10, 0, -10],
  B: [10, 0, -10],
  C: [-10, 0, 10],
  D: [10, 0, 10],
};

// Holographic Queue indicators helper (same as /simulation)
function getQueueColor(value: number) {
  if (value >= 8) return "#ef4444"; // dangerous red
  if (value >= 5) return "#eab308"; // warn yellow
  return "#06b6d4"; // cyan normal
}

interface QueueLabelProps {
  value: number;
  position: [number, number, number];
}

function QueueLabel({ value, position }: QueueLabelProps) {
  const color = getQueueColor(value);
  return (
    <Billboard position={position} follow={true}>
      <group scale={0.7}>
        {/* Sleek backing plate */}
        <mesh position={[0, 0, 0]}>
          <planeGeometry args={[1.2, 0.8]} />
          <meshBasicMaterial color="#111111" opacity={0.85} transparent />
        </mesh>
        {/* Glowing border accent */}
        <mesh position={[0, 0, -0.01]}>
          <planeGeometry args={[1.3, 0.9]} />
          <meshBasicMaterial color={color} opacity={0.6} transparent />
        </mesh>
        {/* Label title */}
        <Text
          position={[0, 0.2, 0.02]}
          fontSize={0.15}
          color="#a1a1aa"
          anchorX="center"
          anchorY="middle"
          letterSpacing={0.1}
        >
          WAITING
        </Text>
        {/* Value Text */}
        <Text
          position={[0, -0.1, 0.02]}
          fontSize={0.5}
          color={color}
          anchorX="center"
          anchorY="middle"
          fontWeight="bold"
        >
          {value}
        </Text>
      </group>
    </Billboard>
  );
}

// Map signal phase and color to R3F TrafficLight states (same as /simulation)
function resolveLightColor(
  phase: number,
  signalColor: string,
  direction: string
): "green" | "yellow" | "red" | "left-green" | "left-yellow" {
  const isNS = direction === "north" || direction === "south";
  const isEW = direction === "east" || direction === "west";

  if (isNS) {
    if (phase === 0) {
      return signalColor as "green" | "yellow" | "red";
    } else if (phase === 2) {
      return signalColor === "green" ? "left-green" : signalColor === "yellow" ? "left-yellow" : "red";
    }
  } else if (isEW) {
    if (phase === 1) {
      return signalColor as "green" | "yellow" | "red";
    } else if (phase === 3) {
      return signalColor === "green" ? "left-green" : signalColor === "yellow" ? "left-yellow" : "red";
    }
  }
  return "red";
}

// ── Single Intersection Component ──
function IntersectionNode({
  data,
  showCongestion,
}: {
  data: CityIntersectionState;
  showCongestion: boolean;
}) {
  const [cx, , cz] = INTERSECTION_POSITIONS[data.id];
  const { current_phase, color } = data.signal;

  // Congestion heatmap logic based on avg_wait_time
  const wait = data.avg_wait_time;
  let heatmapColor = "#22c55e"; // green
  let heatmapOpacity = 0.0;
  
  if (wait >= 12) {
    heatmapColor = "#ef4444"; // red
    heatmapOpacity = Math.min(0.45, 0.2 + (wait - 12) * 0.02);
  } else if (wait >= 4) {
    heatmapColor = "#f59e0b"; // amber
    heatmapOpacity = Math.min(0.35, 0.15 + (wait - 4) * 0.02);
  } else if (wait > 0.5) {
    heatmapColor = "#22c55e";
    heatmapOpacity = Math.min(0.2, 0.05 + wait * 0.02);
  }

  return (
    <group position={[cx, 0, cz]}>
      {/* Congestion Heatmap Overlay */}
      {showCongestion && heatmapOpacity > 0 && (
        <mesh position={[0, 0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[16, 16]} />
          <meshBasicMaterial 
            color={heatmapColor} 
            opacity={heatmapOpacity} 
            transparent 
            depthWrite={false} 
          />
        </mesh>
      )}

      {/* Intersection ID floating indicator */}
      <Text
        position={[0, 4.2, 0]}
        fontSize={0.9}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
        fontWeight="bold"
      >
        {data.id}
      </Text>

      {/* detailed Traffic Light poles aligned to lanes */}
      <TrafficLight
        color={resolveLightColor(current_phase, color, "north")}
        position={[-3.2, 0, -3.2]}
        direction="north"
      />
      <TrafficLight
        color={resolveLightColor(current_phase, color, "south")}
        position={[3.2, 0, 3.2]}
        direction="south"
      />
      <TrafficLight
        color={resolveLightColor(current_phase, color, "east")}
        position={[3.2, 0, -3.2]}
        direction="east"
      />
      <TrafficLight
        color={resolveLightColor(current_phase, color, "west")}
        position={[-3.2, 0, 3.2]}
        direction="west"
      />

      {/* Floating Holographic Queue Indicators */}
      <QueueLabel value={data.queue_lengths.north} position={[-1.2, 2.5, -6.5]} />
      <QueueLabel value={data.queue_lengths.south} position={[1.2, 2.5, 6.5]} />
      <QueueLabel value={data.queue_lengths.east} position={[6.5, 2.5, -1.2]} />
      <QueueLabel value={data.queue_lengths.west} position={[-6.5, 2.5, 1.2]} />
    </group>
  );
}

// ── Main Canvas ──
interface CityCanvasProps {
  frame: CityFrame | null;
  showCongestion: boolean; // Keep prop to maintain component signature
}

export default function CityCanvas({ frame, showCongestion }: CityCanvasProps) {
  const intersectionData = frame?.intersections ?? {};
  const roadVehicles = frame?.road_vehicles ?? [];

  return (
    <Canvas
      camera={{ position: [0, 32, 36], fov: 45 }}
      shadows
      gl={{ antialias: true, alpha: false }}
      style={{ background: "#0a0a0f" }}
    >
      {/* Lighting & Environment */}
      <ambientLight intensity={0.5} />
      <directionalLight
        position={[20, 40, 20]}
        intensity={1.5}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-bias={-0.0001}
      />
      <directionalLight
        position={[-20, 30, -20]}
        intensity={0.6}
        color="#6b9bd1"
      />

      <Suspense fallback={null}>
        {/* City Ground, Curb bases, and skyscrapers */}
        <CityGrid />

        {/* Detailed textured roads networks */}
        <CityRoads />

        {/* 4 Intersection poles & signal heads */}
        {(["A", "B", "C", "D"] as const).map((id) => {
          let data = intersectionData[id];
          if (!data) {
            // Provide default dummy data to render the poles before the simulation starts
            data = {
              id,
              grid_x: id === "A" || id === "C" ? -10 : 10,
              grid_z: id === "A" || id === "B" ? -10 : 10,
              avg_wait_time: 0,
              total_waiting: 0,
              signal: {
                current_phase: 0,
                color: "red",
                time_in_phase: 0,
                starvation_timer: {},
                can_switch_phase: true,
              },
              queue_lengths: { north: 0, south: 0, east: 0, west: 0 },
              vehicles: [],
            };
          }
          return (
            <IntersectionNode key={id} data={data} showCongestion={showCongestion} />
          );
        })}

        {/* Render all intersection vehicles (with detailed models & paints) */}
        {Object.values(intersectionData)
          .flatMap((inter) => inter.vehicles.map(v => ({ v, cx: inter.grid_x, cz: inter.grid_z, iid: inter.id })))
          .map(({ v, cx, cz, iid }) => (
            <CityVehicle key={v.id} vehicle={v} intersectionId={iid} cx={cx} cz={cz} />
          ))}

        {/* Render all road vehicles */}
        {roadVehicles.map((rv) => (
          <CityVehicle
            key={rv.id}
            vehicle={{
              id: rv.id,
              lane: "north", // placeholder
              turn: "straight",
              position: rv.progress,
              state: "moving",
              wait_time: 0,
              world_x: rv.world_x,
              world_z: rv.world_z,
              prev_turn: rv.prev_turn,
              next_turn: rv.next_turn,
            }}
          />
        ))}
      </Suspense>

      {/* Orbit controls */}
      <OrbitControls
        enablePan
        enableZoom
        enableRotate
        target={[0, 0, 0]}
        minDistance={10}
        maxDistance={80}
        maxPolarAngle={Math.PI / 2.2}
      />
    </Canvas>
  );
}
