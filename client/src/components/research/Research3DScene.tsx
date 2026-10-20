"use client";

import React, { useMemo } from "react";
import { Billboard, Text } from "@react-three/drei";
import { ConeGeometry, MeshBasicMaterial, DoubleSide } from "three";
import IntersectionGrid from "@/components/simulation/IntersectionGrid";
import Road from "@/components/simulation/Road";
import TrafficLight from "@/components/simulation/TrafficLight";
import Vehicle from "@/components/simulation/Vehicle";
import { useResearchStore } from "@/store/researchStore";
import type { ResearchTelemetryFrame } from "@/types/research";
import type { VehicleState } from "@/types/simulation";

function getQueueColor(count: number) {
  if (count >= 10) return "#ef4444";
  if (count >= 5) return "#eab308";
  return "#06b6d4";
}

function getWaitColor(seconds: number) {
  if (seconds >= 60) return "#ef4444";
  if (seconds >= 30) return "#eab308";
  return "#a3e635";
}

function resolveLightColor(
  phase: number,
  fsmState: string,
  direction: string
): "green" | "yellow" | "red" | "left-green" | "left-yellow" {
  const isNS = direction === "north" || direction === "south";
  const isEW = direction === "east" || direction === "west";

  const colorState = fsmState === "YELLOW_CLEARANCE" ? "yellow" : fsmState === "ALL_RED_CLEARANCE" ? "red" : "green";

  if (isNS) {
    if (phase === 0) return colorState as "green" | "yellow" | "red";
    if (phase === 2) return colorState === "green" ? "left-green" : colorState === "yellow" ? "left-yellow" : "red";
  } else if (isEW) {
    if (phase === 1) return colorState as "green" | "yellow" | "red";
    if (phase === 3) return colorState === "green" ? "left-green" : colorState === "yellow" ? "left-yellow" : "red";
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
  const waitColor = getWaitColor(avgWait);
  const waitStr = avgWait > 0 ? avgWait.toFixed(0) + "s" : "-";

  return (
    <Billboard position={position} follow={true}>
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
          QUEUED
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

// Camera FOV Conical Projection Overlay
function CameraFovCone() {
  const coneGeo = useMemo(() => new ConeGeometry(14, 18, 16, 1, true), []);
  const coneMat = useMemo(
    () =>
      new MeshBasicMaterial({
        color: "#38bdf8",
        transparent: true,
        opacity: 0.06,
        wireframe: false,
        side: DoubleSide,
        depthWrite: false,
      }),
    []
  );

  return (
    <group position={[12, 14, 12]} rotation={[-Math.PI / 4, Math.PI / 4, 0]}>
      <mesh geometry={coneGeo} material={coneMat} />
      {/* Wireframe border lines */}
      <mesh geometry={coneGeo}>
        <meshBasicMaterial color="#38bdf8" wireframe={true} transparent opacity={0.12} />
      </mesh>
    </group>
  );
}

// Ghost Vehicle (Missed ground-truth in transparent red, false positives in transparent yellow)
interface GhostVehicleProps {
  lane: string;
  type: "missed" | "false_positive";
  positionIndex: number;
}

function GhostVehicle({ lane, type, positionIndex }: GhostVehicleProps) {
  const isMissed = type === "missed";
  const color = isMissed ? "#ef4444" : "#eab308";

  // Approximate lane position offsets
  const laneOffsets: Record<string, [number, number, number]> = {
    north: [-1.5, 0.2, -6 - positionIndex * 3],
    south: [1.5, 0.2, 6 + positionIndex * 3],
    east: [6 + positionIndex * 3, 0.2, -1.5],
    west: [-6 - positionIndex * 3, 0.2, 1.5],
  };

  const pos = laneOffsets[lane] || [0, 0.2, 0];

  return (
    <group position={pos}>
      <mesh>
        <boxGeometry args={[0.45, 0.25, 0.9]} />
        <meshBasicMaterial color={color} transparent opacity={0.55} wireframe={false} />
      </mesh>
      <mesh>
        <boxGeometry args={[0.47, 0.27, 0.92]} />
        <meshBasicMaterial color={color} wireframe transparent opacity={0.8} />
      </mesh>
      <Billboard position={[0, 0.6, 0]}>
        <Text fontSize={0.14} color={color} anchorX="center" anchorY="middle" fontWeight="bold">
          {isMissed ? "MISSED (ORACLE)" : "FALSE POSITIVE"}
        </Text>
      </Billboard>
    </group>
  );
}

interface Research3DSceneProps {
  frameOverride?: ResearchTelemetryFrame | null;
  label?: string;
}

export function Research3DScene({ frameOverride, label }: Research3DSceneProps) {
  const storeFrame = useResearchStore((s) => s.currentFrame);
  const showPerceptionDebug = useResearchStore((s) => s.showPerceptionDebug);

  const frame = frameOverride !== undefined ? frameOverride : storeFrame;
  const fsmState = frame?.fsm?.current_state ?? "GREEN";
  const executedPhase: number =
    frame?.actions?.executed ?? frame?.signal_phase ?? frame?.signal?.current_phase ?? 0;
  const remainingInState = frame?.fsm?.remaining_in_state_s ?? 0;

  const vehicles: VehicleState[] = (frame?.vehicles as unknown as VehicleState[]) ?? [];

  const queueLengths = {
    north: frame?.metrics?.queue_length_north ?? 0,
    south: frame?.metrics?.queue_length_south ?? 0,
    east: frame?.metrics?.queue_length_east ?? 0,
    west: frame?.metrics?.queue_length_west ?? 0,
  };

  const avgWait = frame?.metrics?.delay_mean_s ?? 0;

  // Ghost vehicles for perception debug mode
  const missedCount = frame?.perception?.missed_count ?? 0;
  const falsePositiveCount = frame?.perception?.false_positive_count ?? 0;

  return (
    <group>
      <IntersectionGrid />
      <Road direction="horizontal" />
      <Road direction="vertical" />

      {/* Traffic Lights */}
      <TrafficLight
        color={resolveLightColor(executedPhase, fsmState, "north")}
        position={[-3.2, 0, -3.2]}
        direction="north"
      />
      <TrafficLight
        color={resolveLightColor(executedPhase, fsmState, "south")}
        position={[3.2, 0, 3.2]}
        direction="south"
      />
      <TrafficLight
        color={resolveLightColor(executedPhase, fsmState, "east")}
        position={[3.2, 0, -3.2]}
        direction="east"
      />
      <TrafficLight
        color={resolveLightColor(executedPhase, fsmState, "west")}
        position={[-3.2, 0, 3.2]}
        direction="west"
      />

      {/* Queue Labels */}
      <QueueLabel queueCount={queueLengths.north} avgWait={avgWait} position={[-1.2, 2.5, -7.2]} />
      <QueueLabel queueCount={queueLengths.south} avgWait={avgWait} position={[1.2, 2.5, 7.2]} />
      <QueueLabel queueCount={queueLengths.east} avgWait={avgWait} position={[7.2, 2.5, -1.2]} />
      <QueueLabel queueCount={queueLengths.west} avgWait={avgWait} position={[-7.2, 2.5, 1.2]} />

      {/* Vehicles */}
      {vehicles.map((v) => (
        <Vehicle key={v.id} vehicle={v} />
      ))}

      {/* Camera Field of View Conical Overlay */}
      <CameraFovCone />

      {/* Research Oracle Debug Overlays (Missed & False Positives) */}
      {showPerceptionDebug && missedCount > 0 && (
        <>
          <GhostVehicle lane="north" type="missed" positionIndex={1} />
          {missedCount > 1 && <GhostVehicle lane="south" type="missed" positionIndex={2} />}
        </>
      )}

      {showPerceptionDebug && falsePositiveCount > 0 && (
        <GhostVehicle lane="east" type="false_positive" positionIndex={1} />
      )}

      {/* Clearance / Transition HUD Badge */}
      {fsmState !== "GREEN" && (
        <Billboard position={[0, 4.2, 0]}>
          <group>
            <mesh>
              <planeGeometry args={[3.2, 0.8]} />
              <meshBasicMaterial
                color={fsmState === "YELLOW_CLEARANCE" ? "#854d0e" : "#991b1b"}
                transparent
                opacity={0.9}
              />
            </mesh>
            <Text
              position={[0, 0.15, 0.01]}
              fontSize={0.2}
              color="#ffffff"
              anchorX="center"
              anchorY="middle"
              fontWeight="bold"
            >
              {fsmState === "YELLOW_CLEARANCE" ? "YELLOW CLEARANCE" : "ALL-RED CLEARANCE"}
            </Text>
            <Text
              position={[0, -0.15, 0.01]}
              fontSize={0.16}
              color="#fef08a"
              anchorX="center"
              anchorY="middle"
              letterSpacing={0.05}
            >
              {`TIME REMAINING: ${remainingInState.toFixed(1)}s`}
            </Text>
          </group>
        </Billboard>
      )}

      {/* Optional Scene Label (e.g. For Paired Comparison "FlowSync-UQ" vs "D3QN Baseline") */}
      {label && (
        <Billboard position={[0, 6.2, 0]}>
          <group>
            <mesh>
              <planeGeometry args={[4.2, 0.9]} />
              <meshBasicMaterial color="#0b0f17" transparent opacity={0.88} />
            </mesh>
            <Text position={[0, 0, 0.01]} fontSize={0.28} color="#ffffff" anchorX="center" anchorY="middle" fontWeight="bold">
              {label}
            </Text>
          </group>
        </Billboard>
      )}
    </group>
  );
}
