import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import { Color, Object3D, Vector3 } from "three";

import IntersectionGrid from "@/components/simulation/IntersectionGrid";
import Road from "@/components/simulation/Road";
import TrafficLight from "@/components/simulation/TrafficLight";
import { useSimulationStore } from "@/store/simulationStore";
import type { VehicleState } from "@/types/simulation";

const MAX_VEHICLES = 40;

function mapRange(
  value: number,
  inMin: number,
  inMax: number,
  outMin: number,
  outMax: number,
) {
  return outMin + ((value - inMin) * (outMax - outMin)) / (inMax - inMin);
}

function getVehiclePosition(vehicle: VehicleState): Vector3 {
  const progress = Math.min(Math.max(vehicle.position, 0), 1);

  switch (vehicle.lane) {
    case "north":
      return new Vector3(-0.5, 0.12, mapRange(progress, 0, 1, 8, 0));
    case "south":
      return new Vector3(0.5, 0.12, mapRange(progress, 0, 1, -8, 0));
    case "east":
      return new Vector3(mapRange(progress, 0, 1, 8, 0), 0.12, -0.5);
    case "west":
      return new Vector3(mapRange(progress, 0, 1, -8, 0), 0.12, 0.5);
    default:
      return new Vector3(0, 0.12, 0);
  }
}

function getQueueColor(value: number) {
  if (value >= 8) {
    return "#f87171";
  }
  if (value >= 5) {
    return "#fbbf24";
  }
  return "#e2e8f0";
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

function QueueLabel({
  value,
  position,
}: {
  value: number;
  position: [number, number, number];
}) {
  return (
    <Text
      position={position}
      fontSize={0.4}
      color={getQueueColor(value)}
      anchorX="center"
      anchorY="middle"
    >
      {value}
    </Text>
  );
}

export default function IntersectionScene() {
  const frame = useSimulationStore((state) => state.currentFrame);
  const vehicles = frame?.vehicles ?? [];
  const queueLengths = frame?.queue_lengths ?? {};
  const signalPhase = frame?.signal_phase ?? 0;
  const signalColor = frame?.signal_color ?? "red";

  const meshRef = useRef<THREE.InstancedMesh>(null);
  const currentPositionsRef = useRef<Map<string, Vector3>>(new Map());
  const targetPositionsRef = useRef<Map<string, Vector3>>(new Map());
  const spawnProgressRef = useRef<Map<string, number>>(new Map());
  const exitProgressRef = useRef<Map<string, number>>(new Map());
  const tempObject = useMemo(() => new Object3D(), []);
  const movingColor = useMemo(() => new Color("#f8fafc"), []);
  const waitingColor = useMemo(() => new Color("#fbbf24"), []);

  useEffect(() => {
    const targets = targetPositionsRef.current;
    const currents = currentPositionsRef.current;
    const spawns = spawnProgressRef.current;
    const exits = exitProgressRef.current;
    const activeIds = new Set<string>();

    vehicles.forEach((vehicle) => {
      activeIds.add(vehicle.id);
      targets.set(vehicle.id, getVehiclePosition(vehicle));
      if (!currents.has(vehicle.id)) {
        currents.set(vehicle.id, getVehiclePosition(vehicle));
      }
      if (!spawns.has(vehicle.id)) {
        spawns.set(vehicle.id, 0);
      }
      if (exits.has(vehicle.id)) {
        exits.delete(vehicle.id);
      }
    });

    for (const id of Array.from(targets.keys())) {
      if (!activeIds.has(id)) {
        if (!exits.has(id)) {
          exits.set(id, 1);
        }
      }
    }
  }, [vehicles]);

  useFrame((_, delta) => {
    const mesh = meshRef.current;
    if (!mesh) {
      return;
    }

    const currents = currentPositionsRef.current;
    const targets = targetPositionsRef.current;
    const spawns = spawnProgressRef.current;
    const exits = exitProgressRef.current;

    const renderIds = [
      ...vehicles.map((vehicle) => vehicle.id),
      ...Array.from(exits.keys()),
    ];

    renderIds.slice(0, MAX_VEHICLES).forEach((id, index) => {
      const vehicle = vehicles.find((item) => item.id === id);
      const target = targets.get(id);
      const current = currents.get(id);
      if (!target || !current) {
        return;
      }

      current.lerp(target, 0.15);

      let scale = 1;
      if (vehicle) {
        const progress = spawns.get(id) ?? 1;
        const nextProgress = Math.min(1, progress + delta * 5);
        spawns.set(id, nextProgress);
        scale = nextProgress;
      } else {
        const progress = exits.get(id) ?? 1;
        const nextProgress = Math.max(0, progress - delta * 5);
        exits.set(id, nextProgress);
        scale = nextProgress;

        if (nextProgress <= 0) {
          exits.delete(id);
          targets.delete(id);
          currents.delete(id);
          spawns.delete(id);
        }
      }

      tempObject.position.copy(current);
      tempObject.scale.set(scale, scale, scale);
      tempObject.updateMatrix();
      mesh.setMatrixAt(index, tempObject.matrix);

      const color = vehicle?.state === "waiting" ? waitingColor : movingColor;
      mesh.setColorAt(index, color);
    });

    for (let index = renderIds.length; index < MAX_VEHICLES; index += 1) {
      tempObject.position.set(0, -10, 0);
      tempObject.scale.set(0, 0, 0);
      tempObject.updateMatrix();
      mesh.setMatrixAt(index, tempObject.matrix);
      mesh.setColorAt(index, movingColor);
    }

    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) {
      mesh.instanceColor.needsUpdate = true;
    }
  });

  return (
    <group>
      <IntersectionGrid />
      <Road direction="horizontal" />
      <Road direction="vertical" />

      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "north")}
        position={[-1.2, 0.5, 3.2]}
      />
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "south")}
        position={[1.2, 0.5, -3.2]}
      />
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "east")}
        position={[3.2, 0.5, 1.2]}
      />
      <TrafficLight
        color={resolveLightColor(signalPhase, signalColor, "west")}
        position={[-3.2, 0.5, -1.2]}
      />

      <QueueLabel value={queueLengths.north ?? 0} position={[0, 0.6, 6.6]} />
      <QueueLabel value={queueLengths.south ?? 0} position={[0, 0.6, -6.6]} />
      <QueueLabel value={queueLengths.east ?? 0} position={[6.6, 0.6, 0]} />
      <QueueLabel value={queueLengths.west ?? 0} position={[-6.6, 0.6, 0]} />

      <instancedMesh ref={meshRef} args={[undefined, undefined, MAX_VEHICLES]}>
        <boxGeometry args={[0.4, 0.2, 0.8]} />
        <meshStandardMaterial vertexColors />
      </instancedMesh>
    </group>
  );
}
