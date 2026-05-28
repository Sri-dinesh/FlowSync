"use client";

import { Text } from "@react-three/drei";
import IntersectionGrid from "@/components/simulation/IntersectionGrid";
import Road from "@/components/simulation/Road";
import TrafficLight from "@/components/simulation/TrafficLight";
import Vehicle from "@/components/simulation/Vehicle";
import { useSimulationStore } from "@/store/simulationStore";

// Color coding based on length of queue for visual accessibility
function getQueueColor(value: number) {
  if (value >= 8) {
    return "#ef4444"; // Dangerous red
  }
  if (value >= 5) {
    return "#eab308"; // Warn yellow
  }
  return "#06b6d4"; // Cyan normal
}

function resolveLightColor(
  phase: number,
  signalColor: string,
  direction: string,
) {
  const isNS = phase === 0 || phase === 2;
  const isEW = phase === 1 || phase === 3;
  const active = direction === "north" || direction === "south" ? isNS : isEW;
  if (active && (signalColor === "green" || signalColor === "yellow")) {
    return signalColor;
  }
  return "red";
}

// Queue Label holographic overlay
interface QueueLabelProps {
  value: number;
  position: [number, number, number];
}

function QueueLabel({ value, position }: QueueLabelProps) {
  return (
    <group position={position}>
      {/* Small floating backing plate */}
      <mesh position={[0, 0, 0]} castShadow>
        <boxGeometry args={[0.8, 0.5, 0.08]} />
        <meshStandardMaterial
          color="#09090b"
          roughness={0.7}
          opacity={0.9}
          transparent
        />
      </mesh>

      {/* Glowing text inside backing plate */}
      <Text
        position={[0, 0, 0.06]}
        fontSize={0.35}
        color={getQueueColor(value)}
        anchorX="center"
        anchorY="middle"
        fontWeight="bold"
        opacity={0.95}
      >
        {value}
      </Text>

      {/* Outer glow effect */}
      <mesh position={[0, 0, 0.04]}>
        <boxGeometry args={[0.85, 0.55, 0.02]} />
        <meshStandardMaterial
          color={getQueueColor(value)}
          emissive={getQueueColor(value)}
          emissiveIntensity={value >= 8 ? 1.5 : 0.8}
          transparent
          opacity={0.3}
        />
      </mesh>
    </group>
  );
}

export default function IntersectionScene() {
  const frame = useSimulationStore((state) => state.currentFrame);
  const isRunning = useSimulationStore((state) => state.isRunning);
  const vehicles = frame?.vehicles ?? [];
  const queueLengths = frame?.queue_lengths ?? {};
  const signalPhase = frame?.signal_phase ?? 0;
  const signalColor = frame?.signal_color ?? "red";

  // Always show default state even when no data
  const displayQueueLengths = {
    north: queueLengths.north ?? 0,
    south: queueLengths.south ?? 0,
    east: queueLengths.east ?? 0,
    west: queueLengths.west ?? 0,
  };

  return (
    <group>
      {/* Render cityscape surroundings - this provides the base ground */}
      <IntersectionGrid />

      {/* Render full-length textured asphalt roads */}
      <Road direction="horizontal" />
      <Road direction="vertical" />

      {/* Render detailed Traffic Light cantilever poles - always visible */}
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "north")}
        position={[-1.5, 0, 2.5]}
        direction="north"
      />
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "south")}
        position={[1.5, 0, -2.5]}
        direction="south"
      />
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "east")}
        position={[2.5, 0, 1.5]}
        direction="east"
      />
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "west")}
        position={[-2.5, 0, -1.5]}
        direction="west"
      />

      {/* Floating Holographic Queue Indicators */}
      <QueueLabel value={displayQueueLengths.north} position={[0, 0.8, 6.2]} />
      <QueueLabel value={displayQueueLengths.south} position={[0, 0.8, -6.2]} />
      <QueueLabel value={displayQueueLengths.east} position={[6.2, 0.8, 0]} />
      <QueueLabel value={displayQueueLengths.west} position={[-6.2, 0.8, 0]} />

      {/* Map active live vehicles to their detailed 3D components */}
      {isRunning
        ? vehicles.map((vehicle) => (
            <Vehicle key={vehicle.id} vehicle={vehicle} />
          ))
        : null}
    </group>
  );
}
