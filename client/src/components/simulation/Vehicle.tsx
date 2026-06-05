"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import {
  CylinderGeometry,
  MeshStandardMaterial,
  Group,
  Mesh,
  Vector3,
  CubicBezierCurve3,
} from "three";
import type { VehicleState } from "@/types/simulation";

const SPAWN_DIST = 11;
const EXIT_DIST = 11;
const LANE_OFF = 0.75;
const Y = 0.12;

type Turn = "straight" | "left" | "right";

function buildCurve(lane: string, turn: Turn): CubicBezierCurve3 {
  let p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3;

  switch (lane) {
    case "north": // Southbound, starting North (-Z)
      p0 = new Vector3(-LANE_OFF, Y, -SPAWN_DIST);
      if (turn === "straight") {
        p1 = new Vector3(-LANE_OFF, Y, -1.5);
        p2 = new Vector3(-LANE_OFF, Y, 1.5);
        p3 = new Vector3(-LANE_OFF, Y, EXIT_DIST);
      } else if (turn === "right") { // To Westbound (-X)
        p1 = new Vector3(-LANE_OFF, Y, -1.5);
        p2 = new Vector3(-1.5, Y, -LANE_OFF);
        p3 = new Vector3(-EXIT_DIST, Y, -LANE_OFF);
      } else { // To Eastbound (+X)
        p1 = new Vector3(-LANE_OFF, Y, 1.5);
        p2 = new Vector3(1.5, Y, LANE_OFF);
        p3 = new Vector3(EXIT_DIST, Y, LANE_OFF);
      }
      break;

    case "south": // Northbound, starting South (+Z)
      p0 = new Vector3(LANE_OFF, Y, SPAWN_DIST);
      if (turn === "straight") {
        p1 = new Vector3(LANE_OFF, Y, 1.5);
        p2 = new Vector3(LANE_OFF, Y, -1.5);
        p3 = new Vector3(LANE_OFF, Y, -EXIT_DIST);
      } else if (turn === "right") { // To Eastbound (+X)
        p1 = new Vector3(LANE_OFF, Y, 1.5);
        p2 = new Vector3(1.5, Y, LANE_OFF);
        p3 = new Vector3(EXIT_DIST, Y, LANE_OFF);
      } else { // To Westbound (-X)
        p1 = new Vector3(LANE_OFF, Y, -1.5);
        p2 = new Vector3(-1.5, Y, -LANE_OFF);
        p3 = new Vector3(-EXIT_DIST, Y, -LANE_OFF);
      }
      break;

    case "east": // Westbound, starting East (+X)
      p0 = new Vector3(SPAWN_DIST, Y, -LANE_OFF);
      if (turn === "straight") {
        p1 = new Vector3(1.5, Y, -LANE_OFF);
        p2 = new Vector3(-1.5, Y, -LANE_OFF);
        p3 = new Vector3(-EXIT_DIST, Y, -LANE_OFF);
      } else if (turn === "right") { // To Northbound (-Z)
        p1 = new Vector3(1.5, Y, -LANE_OFF);
        p2 = new Vector3(LANE_OFF, Y, -1.5);
        p3 = new Vector3(LANE_OFF, Y, -EXIT_DIST);
      } else { // To Southbound (+Z)
        p1 = new Vector3(-1.5, Y, -LANE_OFF);
        p2 = new Vector3(-LANE_OFF, Y, 1.5);
        p3 = new Vector3(-LANE_OFF, Y, EXIT_DIST);
      }
      break;

    case "west": // Eastbound, starting West (-X)
      p0 = new Vector3(-SPAWN_DIST, Y, LANE_OFF);
      if (turn === "straight") {
        p1 = new Vector3(-1.5, Y, LANE_OFF);
        p2 = new Vector3(1.5, Y, LANE_OFF);
        p3 = new Vector3(EXIT_DIST, Y, LANE_OFF);
      } else if (turn === "right") { // To Southbound (+Z)
        p1 = new Vector3(-1.5, Y, LANE_OFF);
        p2 = new Vector3(-LANE_OFF, Y, 1.5);
        p3 = new Vector3(-LANE_OFF, Y, EXIT_DIST);
      } else { // To Northbound (-Z)
        p1 = new Vector3(1.5, Y, LANE_OFF);
        p2 = new Vector3(LANE_OFF, Y, -1.5);
        p3 = new Vector3(LANE_OFF, Y, -EXIT_DIST);
      }
      break;

    default:
      p0 = p1 = p2 = p3 = new Vector3(0, Y, 0);
  }

  return new CubicBezierCurve3(p0, p1, p2, p3);
}

function getVehicleProps(id: string) {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  const colors = [
    "#dc2626", "#2563eb", "#16a34a", "#ea580c",
    "#9333ea", "#0891b2", "#db2777", "#e2e8f0",
    "#292524", "#facc15",
  ];
  const types = ["sedan", "suv", "hatchback", "sportscar"] as const;
  return {
    paintColor: colors[Math.abs(hash) % colors.length],
    type: types[Math.abs(hash >> 3) % types.length],
  };
}

function useMaterials(paintColor: string, isWaiting: boolean) {
  return useMemo(() => ({
    paint: new MeshStandardMaterial({
      color: paintColor, roughness: 0.25, metalness: 0.75,
      emissive: paintColor, emissiveIntensity: 0.08,
    }),
    window: new MeshStandardMaterial({
      color: "#0a0a14", roughness: 0.02, metalness: 0.97,
      transparent: true, opacity: 0.88,
    }),
    wheel: new MeshStandardMaterial({ color: "#0f0f0f", roughness: 0.7, metalness: 0.3 }),
    headlight: new MeshStandardMaterial({
      color: "#fffde7", emissive: "#fffde7", emissiveIntensity: 2.2,
    }),
    brakelight: new MeshStandardMaterial({
      color: "#ff0000", emissive: "#ff0000",
      emissiveIntensity: isWaiting ? 3.5 : 0.25,
    }),
  }), [paintColor, isWaiting]);
}

function CarBody({ type, mats }: {
  type: "sedan" | "suv" | "hatchback" | "sportscar";
  mats: ReturnType<typeof useMaterials>;
}) {
  switch (type) {
    case "suv":
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.10, 0]} material={mats.paint}>
            <boxGeometry args={[0.44, 0.18, 0.82]} />
          </mesh>
          <mesh castShadow position={[0, 0.24, -0.05]} material={mats.paint}>
            <boxGeometry args={[0.40, 0.13, 0.50]} />
          </mesh>
          <mesh position={[0, 0.24, -0.05]} material={mats.window}>
            <boxGeometry args={[0.41, 0.09, 0.47]} />
          </mesh>
        </>
      );
    case "hatchback":
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.08, 0]} material={mats.paint}>
            <boxGeometry args={[0.42, 0.14, 0.74]} />
          </mesh>
          <mesh castShadow position={[0, 0.19, -0.07]} material={mats.paint}>
            <boxGeometry args={[0.38, 0.11, 0.44]} />
          </mesh>
          <mesh position={[0, 0.19, -0.07]} material={mats.window}>
            <boxGeometry args={[0.39, 0.08, 0.41]} />
          </mesh>
        </>
      );
    case "sportscar":
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.06, 0]} material={mats.paint}>
            <boxGeometry args={[0.46, 0.10, 0.88]} />
          </mesh>
          <mesh castShadow position={[0, 0.14, -0.03]} material={mats.paint}>
            <boxGeometry args={[0.38, 0.09, 0.40]} />
          </mesh>
          <mesh position={[0, 0.14, -0.03]} material={mats.window}>
            <boxGeometry args={[0.39, 0.07, 0.37]} />
          </mesh>
        </>
      );
    default:
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.08, 0]} material={mats.paint}>
            <boxGeometry args={[0.42, 0.14, 0.84]} />
          </mesh>
          <mesh castShadow position={[0, 0.19, -0.03]} material={mats.paint}>
            <boxGeometry args={[0.38, 0.11, 0.46]} />
          </mesh>
          <mesh position={[0, 0.19, -0.03]} material={mats.window}>
            <boxGeometry args={[0.39, 0.08, 0.43]} />
          </mesh>
        </>
      );
  }
}

interface VehicleProps {
  vehicle: VehicleState;
}

export default function Vehicle({ vehicle }: VehicleProps) {
  const turn = (vehicle.turn ?? "straight") as Turn;
  const { paintColor, type } = useMemo(() => getVehicleProps(vehicle.id), [vehicle.id]);
  const mats = useMaterials(paintColor, vehicle.state === "waiting");

  const curve = useMemo(() => buildCurve(vehicle.lane, turn), [vehicle.lane, turn]);

  const groupRef = useRef<Group>(null);
  const smoothPosRef = useRef<Vector3 | null>(null);
  const smoothRotRef = useRef<number | null>(null);
  const wheelAngleRef = useRef(0);
  const rfRef = useRef<Mesh>(null);
  const lfRef = useRef<Mesh>(null);
  const rrRef = useRef<Mesh>(null);
  const lrRef = useRef<Mesh>(null);

  const wheelGeo = useMemo(() => new CylinderGeometry(0.09, 0.09, 0.07, 10), []);

  useFrame((_, delta) => {
    if (!groupRef.current) return;

    const t = Math.min(Math.max(vehicle.position, 0), 0.999);
    const targetPos = curve.getPointAt(t);

    const tAhead = Math.min(t + 0.01, 1.0);
    const tangent = curve.getPointAt(tAhead).sub(targetPos).normalize();
    const targetRot = Math.atan2(tangent.x, tangent.z);

    if (!smoothPosRef.current) {
      smoothPosRef.current = targetPos.clone();
      smoothRotRef.current = targetRot;
    }

    const lerpFactor = vehicle.state === "moving" ? 0.6 : 0.8;
    smoothPosRef.current.lerp(targetPos, Math.min(1, delta * 60 * lerpFactor));

    let dRot = targetRot - smoothRotRef.current!;
    while (dRot > Math.PI) dRot -= 2 * Math.PI;
    while (dRot < -Math.PI) dRot += 2 * Math.PI;
    smoothRotRef.current! += dRot * Math.min(1, delta * 60 * lerpFactor);

    groupRef.current.position.copy(smoothPosRef.current);
    groupRef.current.rotation.set(0, smoothRotRef.current!, 0);

    if (vehicle.state === "moving") {
      wheelAngleRef.current += delta * 18;
      const a = wheelAngleRef.current;
      if (rfRef.current) rfRef.current.rotation.x = a;
      if (lfRef.current) lfRef.current.rotation.x = a;
      if (rrRef.current) rrRef.current.rotation.x = a;
      if (lrRef.current) lrRef.current.rotation.x = a;
    }
  });

  const wz = type === "sportscar" ? 0.28 : type === "suv" ? 0.26 : 0.24;
  const wy = -0.02;

  return (
    <group ref={groupRef}>
      <CarBody type={type} mats={mats} />

      <mesh position={[-0.14, 0.07, 0.43]} material={mats.headlight} castShadow>
        <boxGeometry args={[0.06, 0.04, 0.01]} />
      </mesh>
      <mesh position={[0.14, 0.07, 0.43]} material={mats.headlight} castShadow>
        <boxGeometry args={[0.06, 0.04, 0.01]} />
      </mesh>

      <mesh position={[-0.14, 0.07, -0.43]} material={mats.brakelight} castShadow>
        <boxGeometry args={[0.06, 0.04, 0.01]} />
      </mesh>
      <mesh position={[0.14, 0.07, -0.43]} material={mats.brakelight} castShadow>
        <boxGeometry args={[0.06, 0.04, 0.01]} />
      </mesh>

      <mesh
        ref={rfRef}
        geometry={wheelGeo}
        material={mats.wheel}
        position={[0.22, wy, wz]}
        rotation={[0, 0, Math.PI / 2]}
        castShadow
      />
      <mesh
        ref={lfRef}
        geometry={wheelGeo}
        material={mats.wheel}
        position={[-0.22, wy, wz]}
        rotation={[0, 0, Math.PI / 2]}
        castShadow
      />
      <mesh
        ref={rrRef}
        geometry={wheelGeo}
        material={mats.wheel}
        position={[0.22, wy, -wz]}
        rotation={[0, 0, Math.PI / 2]}
        castShadow
      />
      <mesh
        ref={lrRef}
        geometry={wheelGeo}
        material={mats.wheel}
        position={[-0.22, wy, -wz]}
        rotation={[0, 0, Math.PI / 2]}
        castShadow
      />
    </group>
  );
}