"use client";

import { Text, Billboard } from "@react-three/drei";
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
  const isNS = direction === "north" || direction === "south";
  const isEW = direction === "east" || direction === "west";

  if (isNS) {
    if (phase === 0) {
      return signalColor as any;
    } else if (phase === 2) {
      return (signalColor === "green" ? "left-green" : signalColor === "yellow" ? "left-yellow" : "red") as any;
    }
  } else if (isEW) {
    if (phase === 1) {
      return signalColor as any;
    } else if (phase === 3) {
      return (signalColor === "green" ? "left-green" : signalColor === "yellow" ? "left-yellow" : "red") as any;
    }
  }
  return "red";
}

// Queue Label holographic overlay
interface QueueLabelProps {
  value: number;
  position: [number, number, number];
}

function QueueLabel({ value, position }: QueueLabelProps) {
  const color = getQueueColor(value);
  return (
    <Billboard position={position} follow={true} lockX={false} lockY={false} lockZ={false}>
      <group>
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

      {/* Render detailed Traffic Light cantilever poles - aligned precisely to lanes */}
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "north")}
        position={[-3.2, 0, -3.2]}
        direction="north"
      />
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "south")}
        position={[3.2, 0, 3.2]}
        direction="south"
      />
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "east")}
        position={[3.2, 0, -3.2]}
        direction="east"
      />
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "west")}
        position={[-3.2, 0, 3.2]}
        direction="west"
      />

      {/* Floating Holographic Queue Indicators */}
      <QueueLabel value={displayQueueLengths.north} position={[-1.2, 2.5, -7.2]} />
      <QueueLabel value={displayQueueLengths.south} position={[1.2, 2.5, 7.2]} />
      <QueueLabel value={displayQueueLengths.east} position={[7.2, 2.5, -1.2]} />
      <QueueLabel value={displayQueueLengths.west} position={[-7.2, 2.5, 1.2]} />

      {/* Map active live vehicles to their detailed 3D components */}
      {isRunning
        ? vehicles.map((vehicle) => (
            <Vehicle key={vehicle.id} vehicle={vehicle} />
          ))
        : null}
    </group>
  );
}
