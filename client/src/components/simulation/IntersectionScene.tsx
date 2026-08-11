"use client";

import { Text, Billboard } from "@react-three/drei";
import IntersectionGrid from "@/components/simulation/IntersectionGrid";
import Road from "@/components/simulation/Road";
import TrafficLight from "@/components/simulation/TrafficLight";
import Vehicle from "@/components/simulation/Vehicle";
import { useSimulationStore } from "@/store/simulationStore";

function getQueueColor(value: number) {
  if (value >= 8) return "#ef4444";
  if (value >= 5) return "#eab308";
  return "#06b6d4";
}

function getWaitColor(seconds: number) {
  if (seconds >= 60) return "#ef4444";
  if (seconds >= 30) return "#eab308";
  return "#a3e635";
}

function resolveLightColor(
  phase: number,
  signalColor: string,
  direction: string,
): "green" | "yellow" | "red" | "left-green" | "left-yellow" {
  const isNS = direction === "north" || direction === "south";
  const isEW = direction === "east" || direction === "west";
  if (isNS) {
    if (phase === 0) return signalColor as "green" | "yellow" | "red";
    if (phase === 2) return signalColor === "green" ? "left-green" : signalColor === "yellow" ? "left-yellow" : "red";
  } else if (isEW) {
    if (phase === 1) return signalColor as "green" | "yellow" | "red";
    if (phase === 3) return signalColor === "green" ? "left-green" : signalColor === "yellow" ? "left-yellow" : "red";
  }
  return "red";
}

interface QueueLabelProps {
  queueCount: number;
  avgWait: number;
  position: [number, number, number];
}

function QueueLabel({ queueCount, avgWait, position }: QueueLabelProps) {
  const queueColor = getQueueColor(queueCount);
  const waitColor  = getWaitColor(avgWait);
  const waitStr    = avgWait > 0 ? avgWait.toFixed(0) + "s" : "-";

  return (
    <Billboard position={position} follow={true} lockX={false} lockY={false} lockZ={false}>
      <group>
        <mesh position={[0, 0, 0]}>
          <planeGeometry args={[1.6, 1.1]} />
          <meshBasicMaterial color="#111111" opacity={0.88} transparent />
        </mesh>
        <mesh position={[0, 0, -0.01]}>
          <planeGeometry args={[1.7, 1.2]} />
          <meshBasicMaterial color={queueColor} opacity={0.5} transparent />
        </mesh>
        <Text position={[0, 0.42, 0.02]} fontSize={0.14} color="#a1a1aa" anchorX="center" anchorY="middle" letterSpacing={0.1}>
          WAITING
        </Text>
        <Text position={[0, 0.1, 0.02]} fontSize={0.44} color={queueColor} anchorX="center" anchorY="middle" fontWeight="bold">
          {queueCount}
        </Text>
        <mesh position={[0, -0.17, 0.02]}>
          <planeGeometry args={[1.3, 0.012]} />
          <meshBasicMaterial color="#ffffff" opacity={0.08} transparent />
        </mesh>
        <Text position={[-0.35, -0.31, 0.02]} fontSize={0.12} color="#71717a" anchorX="left" anchorY="middle" letterSpacing={0.05}>
          AVG WAIT
        </Text>
        <Text position={[0.45, -0.31, 0.02]} fontSize={0.18} color={waitColor} anchorX="right" anchorY="middle" fontWeight="bold">
          {waitStr}
        </Text>
      </group>
    </Billboard>
  );
}

export default function IntersectionScene() {
  const frame        = useSimulationStore((state) => state.currentFrame);
  const isRunning    = useSimulationStore((state) => state.isRunning);
  const vehicles     = frame?.vehicles ?? [];
  const queueLengths = frame?.queue_lengths ?? {};
  const signalPhase  = frame?.signal_phase ?? 0;
  const signalColor  = frame?.signal_color ?? "red";

  const displayQueueLengths = {
    north: queueLengths.north ?? 0,
    south: queueLengths.south ?? 0,
    east:  queueLengths.east  ?? 0,
    west:  queueLengths.west  ?? 0,
  };

  const avgWaitPerDir = (dir: string): number => {
    const waiting = vehicles.filter((v) => v.lane === dir && v.state !== "passed" && v.wait_time > 0);
    if (waiting.length === 0) return 0;
    return waiting.reduce((sum, v) => sum + v.wait_time, 0) / waiting.length;
  };

  return (
    <group>
      <IntersectionGrid />
      <Road direction="horizontal" />
      <Road direction="vertical" />
      <TrafficLight color={resolveLightColor(signalPhase, signalColor, "north")} position={[-3.2, 0, -3.2]} direction="north" />
      <TrafficLight color={resolveLightColor(signalPhase, signalColor, "south")} position={[ 3.2, 0,  3.2]} direction="south" />
      <TrafficLight color={resolveLightColor(signalPhase, signalColor, "east")}  position={[ 3.2, 0, -3.2]} direction="east"  />
      <TrafficLight color={resolveLightColor(signalPhase, signalColor, "west")}  position={[-3.2, 0,  3.2]} direction="west"  />
      <QueueLabel queueCount={displayQueueLengths.north} avgWait={avgWaitPerDir("north")} position={[-1.2, 2.5, -7.2]} />
      <QueueLabel queueCount={displayQueueLengths.south} avgWait={avgWaitPerDir("south")} position={[ 1.2, 2.5,  7.2]} />
      <QueueLabel queueCount={displayQueueLengths.east}  avgWait={avgWaitPerDir("east")}  position={[ 7.2, 2.5, -1.2]} />
      <QueueLabel queueCount={displayQueueLengths.west}  avgWait={avgWaitPerDir("west")}  position={[-7.2, 2.5,  1.2]} />
      {isRunning ? vehicles.map((vehicle) => <Vehicle key={vehicle.id} vehicle={vehicle} />) : null}
    </group>
  );
}