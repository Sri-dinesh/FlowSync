"use client";

import React, { useMemo, useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import {
  MeshStandardMaterial,
  Group,
  Mesh,
  MathUtils,
  Color,
  CylinderGeometry,
  Vector3,
  CurvePath,
  LineCurve3,
  QuadraticBezierCurve3,
} from "three";
import * as THREE from "three";

const Y = 0.12;

type Turn = "straight" | "left" | "right";

function buildCurve(lane: string, turn: Turn, SPAWN_DIST: number, EXIT_DIST: number): CurvePath<Vector3> {
  const path = new CurvePath<Vector3>();
  const STOP = 3.5;
  const off = turn === "left" ? 0.5 : turn === "straight" ? 1.5 : 2.5;
  let start: Vector3, enter: Vector3, exit: Vector3, end: Vector3, control: Vector3;

  switch (lane) {
    case "north":
      start = new Vector3(-off, Y, -SPAWN_DIST);
      enter = new Vector3(-off, Y, -STOP);
      if (turn === "straight") {
        exit = new Vector3(-off, Y, STOP); end = new Vector3(-off, Y, EXIT_DIST); control = new Vector3(-off, Y, 0);
      } else if (turn === "right") {
        exit = new Vector3(-STOP, Y, -off); end = new Vector3(-EXIT_DIST, Y, -off); control = new Vector3(-off, Y, -off);
      } else {
        exit = new Vector3(STOP, Y, off); end = new Vector3(EXIT_DIST, Y, off); control = new Vector3(-off, Y, off);
      }
      break;
    case "south":
      start = new Vector3(off, Y, SPAWN_DIST);
      enter = new Vector3(off, Y, STOP);
      if (turn === "straight") {
        exit = new Vector3(off, Y, -STOP); end = new Vector3(off, Y, -EXIT_DIST); control = new Vector3(off, Y, 0);
      } else if (turn === "right") {
        exit = new Vector3(STOP, Y, off); end = new Vector3(EXIT_DIST, Y, off); control = new Vector3(off, Y, off);
      } else {
        exit = new Vector3(-STOP, Y, -off); end = new Vector3(-EXIT_DIST, Y, -off); control = new Vector3(off, Y, -off);
      }
      break;
    case "east":
      start = new Vector3(SPAWN_DIST, Y, -off);
      enter = new Vector3(STOP, Y, -off);
      if (turn === "straight") {
        exit = new Vector3(-STOP, Y, -off); end = new Vector3(-EXIT_DIST, Y, -off); control = new Vector3(0, Y, -off);
      } else if (turn === "right") {
        exit = new Vector3(off, Y, -STOP); end = new Vector3(off, Y, -EXIT_DIST); control = new Vector3(off, Y, -off);
      } else {
        exit = new Vector3(-off, Y, STOP); end = new Vector3(-off, Y, EXIT_DIST); control = new Vector3(-off, Y, -off);
      }
      break;
    case "west":
      start = new Vector3(-SPAWN_DIST, Y, off);
      enter = new Vector3(-STOP, Y, off);
      if (turn === "straight") {
        exit = new Vector3(STOP, Y, off); end = new Vector3(EXIT_DIST, Y, off); control = new Vector3(0, Y, off);
      } else if (turn === "right") {
        exit = new Vector3(-off, Y, STOP); end = new Vector3(-off, Y, EXIT_DIST); control = new Vector3(-off, Y, off);
      } else {
        exit = new Vector3(off, Y, -STOP); end = new Vector3(off, Y, -EXIT_DIST); control = new Vector3(off, Y, off);
      }
      break;
    default:
      start = enter = exit = end = control = new Vector3(0, Y, 0);
  }

  path.add(new LineCurve3(start, enter));
  if (turn === "straight") {
    path.add(new LineCurve3(enter, exit));
  } else {
    path.add(new QuadraticBezierCurve3(enter, control, exit));
  }
  path.add(new LineCurve3(exit, end));
  return path;
}

interface CityVehicleState {
  id: string;
  lane: string;      // "north" | "south" | "east" | "west"
  turn: "straight" | "left" | "right";
  position: number;
  state: string;     // "waiting" | "moving" | "braking"
  wait_time: number;
  world_x: number;
  world_z: number;
  is_emergency?: boolean;
}

// ── Color and Model Picker ───────────────────────────────────────────────────
function getVehicleProps(id: string, isEmergency?: boolean) {
  if (isEmergency) {
    return {
      paintColor: "#f8fafc",
      type: "ambulance" as const,
    };
  }
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  const colors = [
    "#dc2626", "#2563eb", "#16a34a", "#ea580c",
    "#9333ea", "#0891b2", "#db2777", "#e2e8f0",
    "#292524", "#facc15",
  ];
  const types = ["sedan", "suv", "hatchback", "sportscar", "bike"] as const;
  return {
    paintColor: colors[Math.abs(hash) % colors.length],
    type: types[Math.abs(hash >> 3) % types.length],
  };
}

// ── Materials Cache ──────────────────────────────────────────────────────────
function useMaterials(paintColor: string, isWaiting: boolean) {
  return useMemo(() => ({
    paint: new MeshStandardMaterial({
      color: paintColor,
      roughness: 0.25,
      metalness: 0.75,
      emissive: paintColor,
      emissiveIntensity: 0.08,
    }),
    window: new MeshStandardMaterial({
      color: "#0a0a14",
      roughness: 0.02,
      metalness: 0.97,
      transparent: true,
      opacity: 0.88,
    }),
    wheel: new MeshStandardMaterial({ color: "#0f0f0f", roughness: 0.7, metalness: 0.3 }),
    headlight: new MeshStandardMaterial({
      color: "#fffde7",
      emissive: "#fffde7",
      emissiveIntensity: 2.2,
    }),
    brakelight: new MeshStandardMaterial({
      color: "#ff0000",
      emissive: "#ff0000",
      emissiveIntensity: isWaiting ? 3.5 : 0.25,
    }),
  }), [paintColor, isWaiting]);
}

// ── 3D Geometry Composers ────────────────────────────────────────────────────
function CarBody({ type, mats }: {
  type: "sedan" | "suv" | "hatchback" | "sportscar" | "bike" | "ambulance";
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
            <boxGeometry args={[0.4, 0.13, 0.50]} />
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
    case "bike":
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.12, 0]} material={mats.window}>
            <boxGeometry args={[0.12, 0.20, 0.45]} />
          </mesh>
          <mesh castShadow position={[0, 0.22, 0.08]} material={mats.paint}>
            <boxGeometry args={[0.11, 0.08, 0.18]} />
          </mesh>
          <mesh castShadow position={[0, 0.20, -0.08]} material={mats.wheel}>
            <boxGeometry args={[0.10, 0.03, 0.16]} />
          </mesh>
          <mesh position={[0, 0.25, 0.16]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.015, 0.015, 0.26, 8]} />
            <meshStandardMaterial color="#0f0f0f" roughness={0.5} />
          </mesh>
        </>
      );
    case "ambulance":
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.18, -0.05]} material={mats.paint}>
            <boxGeometry args={[0.46, 0.28, 0.85]} />
          </mesh>
          <mesh castShadow position={[0, 0.11, 0.35]} material={mats.paint}>
            <boxGeometry args={[0.44, 0.14, 0.25]} />
          </mesh>
          <mesh position={[0, 0.13, 0.38]} material={mats.window}>
            <boxGeometry args={[0.41, 0.08, 0.18]} />
          </mesh>
          {/* Red Cross Left Side */}
          <group position={[-0.231, 0.18, -0.05]} rotation={[0, -Math.PI / 2, 0]}>
            <mesh castShadow position={[0, 0, 0.002]}>
              <boxGeometry args={[0.12, 0.03, 0.005]} />
              <meshStandardMaterial color="#dc2626" roughness={0.3} />
            </mesh>
            <mesh castShadow position={[0, 0, 0.002]}>
              <boxGeometry args={[0.03, 0.12, 0.005]} />
              <meshStandardMaterial color="#dc2626" roughness={0.3} />
            </mesh>
          </group>
          {/* Red Cross Right Side */}
          <group position={[0.231, 0.18, -0.05]} rotation={[0, Math.PI / 2, 0]}>
            <mesh castShadow position={[0, 0, 0.002]}>
              <boxGeometry args={[0.12, 0.03, 0.005]} />
              <meshStandardMaterial color="#dc2626" roughness={0.3} />
            </mesh>
            <mesh castShadow position={[0, 0, 0.002]}>
              <boxGeometry args={[0.03, 0.12, 0.005]} />
              <meshStandardMaterial color="#dc2626" roughness={0.3} />
            </mesh>
          </group>
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

interface CityVehicleProps {
  vehicle: CityVehicleState;
  intersectionId?: string;
  cx?: number;
  cz?: number;
}

export default function CityVehicle({ vehicle, intersectionId, cx, cz }: CityVehicleProps) {
  const { paintColor, type } = useMemo(
    () => "is_emergency" in vehicle
      ? getVehicleProps(vehicle.id, vehicle.is_emergency)
      : getVehicleProps(vehicle.id, false),
    [vehicle.id, "is_emergency" in vehicle ? vehicle.is_emergency : false]
  );
  const mats = useMaterials(paintColor, vehicle.state === "waiting");

  const turn = (vehicle.turn ?? "straight") as Turn;

  const { spawnDist, exitDist } = useMemo(() => {
    if (!intersectionId) return { spawnDist: 20, exitDist: 20 };
    const id = intersectionId;
    const lane = vehicle.lane;
    const t = vehicle.turn ?? "straight";
    
    let isExtSpawn = false;
    if (id === "A" && (lane === "north" || lane === "west")) isExtSpawn = true;
    if (id === "B" && (lane === "north" || lane === "east")) isExtSpawn = true;
    if (id === "C" && (lane === "south" || lane === "west")) isExtSpawn = true;
    if (id === "D" && (lane === "south" || lane === "east")) isExtSpawn = true;

    let exitDir = "";
    if (lane === "north") exitDir = t === "straight" ? "south" : t === "right" ? "west" : "east";
    if (lane === "south") exitDir = t === "straight" ? "north" : t === "right" ? "east" : "west";
    if (lane === "east") exitDir = t === "straight" ? "west" : t === "right" ? "north" : "south";
    if (lane === "west") exitDir = t === "straight" ? "east" : t === "right" ? "south" : "north";

    let isExtExit = false;
    if (id === "A" && (exitDir === "north" || exitDir === "west")) isExtExit = true;
    if (id === "B" && (exitDir === "north" || exitDir === "east")) isExtExit = true;
    if (id === "C" && (exitDir === "south" || exitDir === "west")) isExtExit = true;
    if (id === "D" && (exitDir === "south" || exitDir === "east")) isExtExit = true;

    return { spawnDist: isExtSpawn ? 28 : 6.0, exitDist: isExtExit ? 28 : 6.0 };
  }, [intersectionId, vehicle.lane, vehicle.turn]);

  const curve = useMemo(() => buildCurve(vehicle.lane, turn, spawnDist, exitDist), [vehicle.lane, turn, spawnDist, exitDist]);
  const t_stop = useMemo(() => (spawnDist - 3.5) / curve.getLength(), [curve, spawnDist]);

  const groupRef = useRef<Group>(null);
  const smoothRotRef = useRef<number | null>(null);
  const wheelAngleRef = useRef(0);

  const rfRef = useRef<Mesh>(null);
  const lfRef = useRef<Mesh>(null);
  const rrRef = useRef<Mesh>(null);
  const lrRef = useRef<Mesh>(null);

  const sirenRedMeshRef = useRef<MeshStandardMaterial>(null);
  const sirenBlueMeshRef = useRef<MeshStandardMaterial>(null);
  const sirenRedLightRef = useRef<THREE.PointLight>(null);
  const sirenBlueLightRef = useRef<THREE.PointLight>(null);

  // For RoadVehicles (no center)
  const lastTargetPos = useRef({ x: vehicle.world_x, z: vehicle.world_z });
  const startVisualPos = useRef({ x: vehicle.world_x, z: vehicle.world_z });
  const currentVisualPos = useRef({ x: vehicle.world_x, z: vehicle.world_z });
  
  // For IntersectionVehicles (has center)
  const lastTargetTRef = useRef(vehicle.position);
  const startTRef = useRef(vehicle.position);
  const lastVisualTRef = useRef(vehicle.position);

  const lastUpdateTime = useRef<number | null>(null);
  const updateInterval = useRef(0.1);

  // Keep track of active wheels
  const wheelGeo = useMemo(() => new CylinderGeometry(0.09, 0.09, 0.07, 10), []);

  useEffect(() => {
    return () => {
      wheelGeo.dispose();
      Object.values(mats).forEach((m) => m.dispose());
    };
  }, [wheelGeo, mats]);

  // Set default heading based on lane
  const getDefaultHeading = (lane: string) => {
    switch (lane) {
      case "north": return 0;          // Southbound (+Z)
      case "south": return Math.PI;    // Northbound (-Z)
      case "east": return Math.PI / 2; // Westbound (-X)
      case "west": return -Math.PI / 2;// Eastbound (+X)
      default: return 0;
    }
  };

  useFrame((state, delta) => {
    if (!groupRef.current) return;

    const time = state.clock.getElapsedTime();
    if (lastUpdateTime.current === null) {
      lastUpdateTime.current = time;
    }

    if (intersectionId !== undefined && cx !== undefined && cz !== undefined) {
      // INTERSECTION VEHICLE LOGIC (CurvePath)
      if (vehicle.position !== lastTargetTRef.current) {
        const actualInterval = time - lastUpdateTime.current;
        updateInterval.current = Math.min(Math.max(actualInterval, 0.05), 2.0);

        startTRef.current = lastVisualTRef.current;
        lastTargetTRef.current = vehicle.position;
        lastUpdateTime.current = time - delta;
      }

      const elapsed = time - lastUpdateTime.current;
      const progress = Math.min(1.0, elapsed / updateInterval.current);

      let t = startTRef.current + (vehicle.position - startTRef.current) * progress;
      t = Math.min(Math.max(t, 0), 0.999);
      lastVisualTRef.current = t;

      let t_visual = 0;
      if (t <= 0.42) {
        t_visual = (t / 0.42) * t_stop;
      } else {
        t_visual = t_stop + ((t - 0.42) / 0.58) * (1.0 - t_stop);
      }
      t_visual = Math.min(Math.max(t_visual, 0), 0.999);

      const targetPos = curve.getPointAt(t_visual);
      const tAhead = Math.min(t_visual + 0.01, 1.0);
      const tangent = curve.getPointAt(tAhead).sub(targetPos).normalize();
      const targetRot = Math.atan2(tangent.x, tangent.z);

      if (smoothRotRef.current === null) {
        smoothRotRef.current = targetRot;
      }

      const currentRot = smoothRotRef.current;
      let dRot = targetRot - currentRot;
      while (dRot > Math.PI) dRot -= 2 * Math.PI;
      while (dRot < -Math.PI) dRot += 2 * Math.PI;
      const nextRot = currentRot + dRot * Math.min(1, delta * 15);
      smoothRotRef.current = nextRot;

      groupRef.current.position.set(cx + targetPos.x, targetPos.y, cz + targetPos.z);
      groupRef.current.rotation.set(0, nextRot, 0);

    } else {
      // ROAD VEHICLE LOGIC (Linear interpolation of world_x / world_z)
      if (
        vehicle.world_x !== lastTargetPos.current.x ||
        vehicle.world_z !== lastTargetPos.current.z
      ) {
        const interval = time - lastUpdateTime.current;
        updateInterval.current = Math.min(Math.max(interval, 0.05), 2.0);

        startVisualPos.current = { ...currentVisualPos.current };
        lastTargetPos.current = { x: vehicle.world_x, z: vehicle.world_z };
        startTRef.current = lastVisualTRef.current; // reusing startTRef for road progress
        lastTargetTRef.current = vehicle.position;  // reusing lastTargetTRef
        lastUpdateTime.current = time;
      }

      const elapsed = time - lastUpdateTime.current;
      const progress = Math.min(1.0, elapsed / updateInterval.current);

      const x = startVisualPos.current.x + (lastTargetPos.current.x - startVisualPos.current.x) * progress;
      const z = startVisualPos.current.z + (lastTargetPos.current.z - startVisualPos.current.z) * progress;
      
      const visual_progress = startTRef.current + (lastTargetTRef.current - startTRef.current) * progress;
      lastVisualTRef.current = visual_progress;

      const dx = x - currentVisualPos.current.x;
      const dz = z - currentVisualPos.current.z;
      const distanceMoved = Math.sqrt(dx * dx + dz * dz);

      let targetAngle = smoothRotRef.current ?? getDefaultHeading(vehicle.lane);
      if (distanceMoved > 0.005) {
        targetAngle = Math.atan2(dx, dz);
      } else if (vehicle.state === "waiting") {
        targetAngle = getDefaultHeading(vehicle.lane);
      }

      if (smoothRotRef.current === null) {
        smoothRotRef.current = targetAngle;
      } else {
        let diff = targetAngle - smoothRotRef.current;
        while (diff < -Math.PI) diff += Math.PI * 2;
        while (diff > Math.PI) diff -= Math.PI * 2;
        smoothRotRef.current += diff * Math.min(1, delta * 12);
      }

      const getOff = (t?: string) => t === "left" ? 0.5 : t === "straight" ? 1.5 : 2.5;
      const offStart = getOff(vehicle.prev_turn);
      const offEnd = getOff(vehicle.next_turn);
      const currentOff = offStart + (offEnd - offStart) * visual_progress;

      const path_dx = lastTargetPos.current.x - startVisualPos.current.x;
      const path_dz = lastTargetPos.current.z - startVisualPos.current.z;
      const path_dist = Math.sqrt(path_dx * path_dx + path_dz * path_dz);
      let nx = 0, nz = 1;
      if (path_dist > 0.001) {
        nx = path_dx / path_dist;
        nz = path_dz / path_dist;
      }
      
      const lat_x = -nz;
      const lat_z = nx;
      
      const final_x = x + lat_x * currentOff;
      const final_z = z + lat_z * currentOff;

      currentVisualPos.current = { x, z };
      groupRef.current.position.set(final_x, 0.08, final_z);
      groupRef.current.rotation.y = smoothRotRef.current;
    }

    if (vehicle.state !== "waiting" && vehicle.state !== "passed") {
      const speed = vehicle.state === "braking" ? 2 : 12;
      wheelAngleRef.current += delta * speed;
      const rotationX = wheelAngleRef.current;

      [rfRef, lfRef, rrRef, lrRef].forEach((ref) => {
        if (ref.current) {
          ref.current.rotation.x = rotationX;
        }
      });
    }

    if (type === "ambulance") {
      const flash = (time % 0.3) < 0.15;
      if (sirenRedMeshRef.current) sirenRedMeshRef.current.emissiveIntensity = flash ? 8.0 : 0.05;
      if (sirenBlueMeshRef.current) sirenBlueMeshRef.current.emissiveIntensity = flash ? 0.05 : 8.0;
      if (sirenRedLightRef.current) sirenRedLightRef.current.intensity = flash ? 3.0 : 0.0;
      if (sirenBlueLightRef.current) sirenBlueLightRef.current.intensity = flash ? 0.0 : 3.0;
    }
  });

  const isBike = type === "bike";
  const wz = type === "sportscar" ? 0.28 : (type === "suv" || type === "ambulance") ? 0.26 : 0.24;
  const wy = -0.02;

  return (
    <group ref={groupRef}>
      <CarBody type={type} mats={mats} />

      {/* Sirens for Ambulance */}
      {type === "ambulance" && (
        <group position={[0, 0.33, 0.1]}>
          <mesh castShadow>
            <boxGeometry args={[0.3, 0.03, 0.06]} />
            <meshStandardMaterial color="#1f2937" metalness={0.8} roughness={0.2} />
          </mesh>
          <mesh position={[-0.08, 0.02, 0]}>
            <boxGeometry args={[0.1, 0.03, 0.05]} />
            <meshStandardMaterial ref={sirenRedMeshRef} color="#ff0000" emissive="#ff0000" emissiveIntensity={0.2} />
          </mesh>
          <mesh position={[0.08, 0.02, 0]}>
            <boxGeometry args={[0.1, 0.03, 0.05]} />
            <meshStandardMaterial ref={sirenBlueMeshRef} color="#0000ff" emissive="#0000ff" emissiveIntensity={0.2} />
          </mesh>
          <pointLight ref={sirenRedLightRef} color="#ff0000" intensity={0} distance={4} decay={2} position={[-0.08, 0.05, 0]} />
          <pointLight ref={sirenBlueLightRef} color="#0066ff" intensity={0} distance={4} decay={2} position={[0.08, 0.05, 0]} />
        </group>
      )}

      {/* Headlights */}
      {isBike ? (
        <mesh position={[0, 0.22, 0.32]} material={mats.headlight} castShadow>
          <boxGeometry args={[0.08, 0.06, 0.01]} />
        </mesh>
      ) : (
        <>
          <mesh position={[-0.14, 0.07, 0.43]} material={mats.headlight} castShadow>
            <boxGeometry args={[0.06, 0.04, 0.01]} />
          </mesh>
          <mesh position={[0.14, 0.07, 0.43]} material={mats.headlight} castShadow>
            <boxGeometry args={[0.06, 0.04, 0.01]} />
          </mesh>
        </>
      )}

      {/* Brakelights */}
      {isBike ? (
        <mesh position={[0, 0.18, -0.32]} material={mats.brakelight} castShadow>
          <boxGeometry args={[0.06, 0.04, 0.01]} />
        </mesh>
      ) : (
        <>
          <mesh position={[-0.14, 0.07, -0.43]} material={mats.brakelight} castShadow>
            <boxGeometry args={[0.06, 0.04, 0.01]} />
          </mesh>
          <mesh position={[0.14, 0.07, -0.43]} material={mats.brakelight} castShadow>
            <boxGeometry args={[0.06, 0.04, 0.01]} />
          </mesh>
        </>
      )}

      {/* Wheels */}
      {isBike ? (
        <>
          <mesh
            ref={rfRef}
            geometry={wheelGeo}
            material={mats.wheel}
            position={[0, wy, 0.25]}
            rotation={[0, 0, Math.PI / 2]}
            castShadow
          />
          <mesh
            ref={rrRef}
            geometry={wheelGeo}
            material={mats.wheel}
            position={[0, wy, -0.25]}
            rotation={[0, 0, Math.PI / 2]}
            castShadow
          />
        </>
      ) : (
        <>
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
        </>
      )}
    </group>
  );
}
