"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import {
  BoxGeometry,
  CylinderGeometry,
  MeshStandardMaterial,
  Group,
  Mesh,
  Vector3,
  CurvePath,
  LineCurve3,
  QuadraticBezierCurve3,
} from "three";
import type { VehicleState } from "@/types/simulation";

const SPAWN_DIST = 20;
const EXIT_DIST = 20;
const Y = 0.12;

type Turn = "straight" | "left" | "right";

function buildCurve(lane: string, turn: Turn): CurvePath<Vector3> {
  const path = new CurvePath<Vector3>();
  const STOP = 3.5;
  
  // Lane offsets from center (0): left=0.5, straight=1.5, right=2.5
  const off = turn === "left" ? 0.5 : turn === "straight" ? 1.5 : 2.5;

  let start: Vector3, enter: Vector3, exit: Vector3, end: Vector3, control: Vector3;

  switch (lane) {
    case "north": // Southbound, starting North (-Z)
      start = new Vector3(-off, Y, -SPAWN_DIST);
      enter = new Vector3(-off, Y, -STOP);
      if (turn === "straight") {
        exit = new Vector3(-off, Y, STOP);
        end = new Vector3(-off, Y, EXIT_DIST);
        control = new Vector3(-off, Y, 0);
      } else if (turn === "right") { // To Westbound (-X)
        exit = new Vector3(-STOP, Y, -off);
        end = new Vector3(-EXIT_DIST, Y, -off);
        control = new Vector3(-off, Y, -off);
      } else { // To Eastbound (+X)
        exit = new Vector3(STOP, Y, off);
        end = new Vector3(EXIT_DIST, Y, off);
        control = new Vector3(-off, Y, off);
      }
      break;

    case "south": // Northbound, starting South (+Z)
      start = new Vector3(off, Y, SPAWN_DIST);
      enter = new Vector3(off, Y, STOP);
      if (turn === "straight") {
        exit = new Vector3(off, Y, -STOP);
        end = new Vector3(off, Y, -EXIT_DIST);
        control = new Vector3(off, Y, 0);
      } else if (turn === "right") { // To Eastbound (+X)
        exit = new Vector3(STOP, Y, off);
        end = new Vector3(EXIT_DIST, Y, off);
        control = new Vector3(off, Y, off);
      } else { // To Westbound (-X)
        exit = new Vector3(-STOP, Y, -off);
        end = new Vector3(-EXIT_DIST, Y, -off);
        control = new Vector3(off, Y, -off);
      }
      break;

    case "east": // Westbound, starting East (+X)
      start = new Vector3(SPAWN_DIST, Y, -off);
      enter = new Vector3(STOP, Y, -off);
      if (turn === "straight") {
        exit = new Vector3(-STOP, Y, -off);
        end = new Vector3(-EXIT_DIST, Y, -off);
        control = new Vector3(0, Y, -off);
      } else if (turn === "right") { // To Northbound (-Z)
        exit = new Vector3(off, Y, -STOP);
        end = new Vector3(off, Y, -EXIT_DIST);
        control = new Vector3(off, Y, -off);
      } else { // To Southbound (+Z)
        exit = new Vector3(-off, Y, STOP);
        end = new Vector3(-off, Y, EXIT_DIST);
        control = new Vector3(-off, Y, -off);
      }
      break;

    case "west": // Eastbound, starting West (-X)
      start = new Vector3(-SPAWN_DIST, Y, off);
      enter = new Vector3(-STOP, Y, off);
      if (turn === "straight") {
        exit = new Vector3(STOP, Y, off);
        end = new Vector3(EXIT_DIST, Y, off);
        control = new Vector3(0, Y, off);
      } else if (turn === "right") { // To Southbound (+Z)
        exit = new Vector3(-off, Y, STOP);
        end = new Vector3(-off, Y, EXIT_DIST);
        control = new Vector3(-off, Y, off);
      } else { // To Northbound (-Z)
        exit = new Vector3(off, Y, -STOP);
        end = new Vector3(off, Y, -EXIT_DIST);
        control = new Vector3(off, Y, off);
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

// ── Static Precomputed Curve Cache (Zero allocation during simulation) ───────
const LANES = ["north", "south", "east", "west"] as const;
const TURNS = ["straight", "left", "right"] as const;
const CURVE_CACHE = new Map<string, { curve: CurvePath<Vector3>; t_stop: number }>();

for (const lane of LANES) {
  for (const turn of TURNS) {
    const curve = buildCurve(lane, turn);
    const t_stop = (SPAWN_DIST - 3.5) / curve.getLength();
    CURVE_CACHE.set(`${lane}_${turn}`, { curve, t_stop });
  }
}

function getCachedCurve(lane: string, turn: Turn) {
  const key = `${lane}_${turn}`;
  const hit = CURVE_CACHE.get(key);
  if (hit) return hit;
  const curve = buildCurve(lane, turn);
  const t_stop = (SPAWN_DIST - 3.5) / curve.getLength();
  CURVE_CACHE.set(key, { curve, t_stop });
  return { curve, t_stop };
}

// ── Color & Vehicle Type Generator ──────────────────────────────────────────
const VEHICLE_COLORS = [
  "#dc2626", "#2563eb", "#16a34a", "#ea580c",
  "#9333ea", "#0891b2", "#db2777", "#e2e8f0",
  "#292524", "#facc15",
] as const;

const VEHICLE_TYPES = ["sedan", "suv", "hatchback", "sportscar", "bike"] as const;

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
  return {
    paintColor: VEHICLE_COLORS[Math.abs(hash) % VEHICLE_COLORS.length],
    type: VEHICLE_TYPES[Math.abs(hash >> 3) % VEHICLE_TYPES.length],
  };
}

// ── Shared Module Geometries (0 GC Churn & 0 GPU Buffer Re-allocations) ──────
const WHEEL_GEO = new CylinderGeometry(0.09, 0.09, 0.07, 8);

// Sedan
const SEDAN_BODY_GEO = new BoxGeometry(0.42, 0.14, 0.84);
const SEDAN_CABIN_GEO = new BoxGeometry(0.38, 0.11, 0.46);
const SEDAN_WINDOW_GEO = new BoxGeometry(0.39, 0.08, 0.43);

// SUV
const SUV_BODY_GEO = new BoxGeometry(0.44, 0.18, 0.82);
const SUV_CABIN_GEO = new BoxGeometry(0.40, 0.13, 0.50);
const SUV_WINDOW_GEO = new BoxGeometry(0.41, 0.09, 0.47);

// Hatchback
const HATCH_BODY_GEO = new BoxGeometry(0.42, 0.14, 0.74);
const HATCH_CABIN_GEO = new BoxGeometry(0.38, 0.11, 0.44);
const HATCH_WINDOW_GEO = new BoxGeometry(0.39, 0.08, 0.41);

// Sportscar
const SPORT_BODY_GEO = new BoxGeometry(0.46, 0.10, 0.88);
const SPORT_CABIN_GEO = new BoxGeometry(0.38, 0.09, 0.40);
const SPORT_WINDOW_GEO = new BoxGeometry(0.39, 0.07, 0.37);

// Bike
const BIKE_FRAME_GEO = new BoxGeometry(0.12, 0.20, 0.45);
const BIKE_TANK_GEO = new BoxGeometry(0.11, 0.08, 0.18);
const BIKE_SEAT_GEO = new BoxGeometry(0.10, 0.03, 0.16);
const BIKE_BAR_GEO = new CylinderGeometry(0.015, 0.015, 0.26, 8);

// Ambulance
const AMBULANCE_BODY_GEO = new BoxGeometry(0.46, 0.28, 0.85);
const AMBULANCE_CAB_GEO = new BoxGeometry(0.44, 0.14, 0.25);
const AMBULANCE_WINDOW_GEO = new BoxGeometry(0.41, 0.08, 0.18);
const AMBULANCE_CROSS_H_GEO = new BoxGeometry(0.12, 0.03, 0.005);
const AMBULANCE_CROSS_V_GEO = new BoxGeometry(0.03, 0.12, 0.005);
const AMBULANCE_SIREN_BAR_GEO = new BoxGeometry(0.3, 0.03, 0.06);
const AMBULANCE_FLASHER_GEO = new BoxGeometry(0.1, 0.03, 0.05);

// Lights
const HEADLIGHT_GEO = new BoxGeometry(0.06, 0.04, 0.01);
const BRAKELIGHT_GEO = new BoxGeometry(0.06, 0.04, 0.01);
const BIKE_HEADLIGHT_GEO = new BoxGeometry(0.08, 0.06, 0.01);
const BIKE_BRAKELIGHT_GEO = new BoxGeometry(0.06, 0.04, 0.01);

// ── Shared Static Materials Singletons (0 Shader Re-compilations) ────────────
const WINDOW_MAT = new MeshStandardMaterial({
  color: "#0a0a14",
  roughness: 0.02,
  metalness: 0.97,
  transparent: true,
  opacity: 0.88,
});

const WHEEL_MAT = new MeshStandardMaterial({
  color: "#0f0f0f",
  roughness: 0.7,
  metalness: 0.3,
});

const BIKE_BAR_MAT = new MeshStandardMaterial({
  color: "#0f0f0f",
  roughness: 0.5,
});

const HEADLIGHT_MAT = new MeshStandardMaterial({
  color: "#fffde7",
  emissive: "#fffde7",
  emissiveIntensity: 2.2,
});

const BRAKELIGHT_NORMAL_MAT = new MeshStandardMaterial({
  color: "#ff0000",
  emissive: "#ff0000",
  emissiveIntensity: 0.25,
});

const BRAKELIGHT_WAITING_MAT = new MeshStandardMaterial({
  color: "#ff0000",
  emissive: "#ff0000",
  emissiveIntensity: 3.5,
});

const CROSS_MAT = new MeshStandardMaterial({
  color: "#dc2626",
  roughness: 0.3,
});

const SIREN_BAR_MAT = new MeshStandardMaterial({
  color: "#1f2937",
  metalness: 0.8,
  roughness: 0.2,
});

// Paint material palette cache (10 colors + ambulance white = 11 cached instances)
const PAINT_MAT_CACHE = new Map<string, MeshStandardMaterial>();

function getPaintMaterial(paintColor: string): MeshStandardMaterial {
  let mat = PAINT_MAT_CACHE.get(paintColor);
  if (!mat) {
    mat = new MeshStandardMaterial({
      color: paintColor,
      roughness: 0.25,
      metalness: 0.75,
      emissive: paintColor,
      emissiveIntensity: 0.08,
    });
    PAINT_MAT_CACHE.set(paintColor, mat);
  }
  return mat;
}

// ── Car Body Component (Zero GC, Reuses Module Singletons) ───────────────────
function CarBody({
  type,
  paintMat,
}: {
  type: "sedan" | "suv" | "hatchback" | "sportscar" | "bike" | "ambulance";
  paintMat: MeshStandardMaterial;
}) {
  switch (type) {
    case "suv":
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.1, 0]} geometry={SUV_BODY_GEO} material={paintMat} />
          <mesh castShadow position={[0, 0.24, -0.05]} geometry={SUV_CABIN_GEO} material={paintMat} />
          <mesh position={[0, 0.24, -0.05]} geometry={SUV_WINDOW_GEO} material={WINDOW_MAT} />
        </>
      );
    case "hatchback":
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.08, 0]} geometry={HATCH_BODY_GEO} material={paintMat} />
          <mesh castShadow position={[0, 0.19, -0.07]} geometry={HATCH_CABIN_GEO} material={paintMat} />
          <mesh position={[0, 0.19, -0.07]} geometry={HATCH_WINDOW_GEO} material={WINDOW_MAT} />
        </>
      );
    case "sportscar":
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.06, 0]} geometry={SPORT_BODY_GEO} material={paintMat} />
          <mesh castShadow position={[0, 0.14, -0.03]} geometry={SPORT_CABIN_GEO} material={paintMat} />
          <mesh position={[0, 0.14, -0.03]} geometry={SPORT_WINDOW_GEO} material={WINDOW_MAT} />
        </>
      );
    case "bike":
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.12, 0]} geometry={BIKE_FRAME_GEO} material={WINDOW_MAT} />
          <mesh castShadow position={[0, 0.22, 0.08]} geometry={BIKE_TANK_GEO} material={paintMat} />
          <mesh position={[0, 0.2, -0.08]} geometry={BIKE_SEAT_GEO} material={WHEEL_MAT} />
          <mesh position={[0, 0.25, 0.16]} rotation={[0, 0, Math.PI / 2]} geometry={BIKE_BAR_GEO} material={BIKE_BAR_MAT} />
        </>
      );
    case "ambulance":
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.18, -0.05]} geometry={AMBULANCE_BODY_GEO} material={paintMat} />
          <mesh castShadow position={[0, 0.11, 0.35]} geometry={AMBULANCE_CAB_GEO} material={paintMat} />
          <mesh position={[0, 0.13, 0.38]} geometry={AMBULANCE_WINDOW_GEO} material={WINDOW_MAT} />
          {/* Red Cross Left Side */}
          <group position={[-0.231, 0.18, -0.05]} rotation={[0, -Math.PI / 2, 0]}>
            <mesh geometry={AMBULANCE_CROSS_H_GEO} material={CROSS_MAT} />
            <mesh geometry={AMBULANCE_CROSS_V_GEO} material={CROSS_MAT} />
          </group>
          {/* Red Cross Right Side */}
          <group position={[0.231, 0.18, -0.05]} rotation={[0, Math.PI / 2, 0]}>
            <mesh geometry={AMBULANCE_CROSS_H_GEO} material={CROSS_MAT} />
            <mesh geometry={AMBULANCE_CROSS_V_GEO} material={CROSS_MAT} />
          </group>
        </>
      );
    default: // sedan
      return (
        <>
          <mesh castShadow receiveShadow position={[0, 0.08, 0]} geometry={SEDAN_BODY_GEO} material={paintMat} />
          <mesh castShadow position={[0, 0.19, -0.03]} geometry={SEDAN_CABIN_GEO} material={paintMat} />
          <mesh position={[0, 0.19, -0.03]} geometry={SEDAN_WINDOW_GEO} material={WINDOW_MAT} />
        </>
      );
  }
}

interface VehicleProps {
  vehicle: VehicleState;
}

export default function Vehicle({ vehicle }: VehicleProps) {
  const turn = (vehicle.turn ?? "straight") as Turn;
  const { paintColor, type } = useMemo(
    () => getVehicleProps(vehicle.id, vehicle.is_emergency),
    [vehicle.id, vehicle.is_emergency]
  );

  const paintMat = useMemo(() => getPaintMaterial(paintColor), [paintColor]);
  const isWaiting = vehicle.state === "waiting";
  const brakelightMat = isWaiting ? BRAKELIGHT_WAITING_MAT : BRAKELIGHT_NORMAL_MAT;

  const { curve, t_stop } = useMemo(
    () => getCachedCurve(vehicle.lane, turn),
    [vehicle.lane, turn]
  );

  const groupRef = useRef<Group>(null);
  const smoothRotRef = useRef<number | null>(null);
  const wheelAngleRef = useRef(0);
  const rfRef = useRef<Mesh>(null);
  const lfRef = useRef<Mesh>(null);
  const rrRef = useRef<Mesh>(null);
  const lrRef = useRef<Mesh>(null);

  // Siren refs for emergency vehicles
  const sirenRedMeshRef = useRef<MeshStandardMaterial>(null);
  const sirenBlueMeshRef = useRef<MeshStandardMaterial>(null);
  const sirenRedLightRef = useRef<import("three").PointLight>(null);
  const sirenBlueLightRef = useRef<import("three").PointLight>(null);

  // Smooth interpolation refs
  const lastTargetPosRef = useRef(vehicle.position);
  const startPosRef = useRef(vehicle.position);
  const lastVisualTRef = useRef(vehicle.position);
  const lastUpdateTimeRef = useRef<number | null>(null);
  const lastUpdateIntervalRef = useRef(0.1);

  useFrame((state, delta) => {
    if (!groupRef.current) return;

    const time = state.clock.getElapsedTime();
    if (lastUpdateTimeRef.current === null) {
      lastUpdateTimeRef.current = time;
    }

    if (vehicle.position !== lastTargetPosRef.current) {
      const actualInterval = time - lastUpdateTimeRef.current;
      lastUpdateIntervalRef.current = Math.min(Math.max(actualInterval, 0.05), 0.5);

      startPosRef.current = lastVisualTRef.current;
      lastTargetPosRef.current = vehicle.position;
      lastUpdateTimeRef.current = time - delta;
    }

    const elapsed = time - lastUpdateTimeRef.current;
    const duration = lastUpdateIntervalRef.current;
    const progress = Math.min(1.0, elapsed / duration);

    let t = startPosRef.current + (vehicle.position - startPosRef.current) * progress;
    t = Math.min(Math.max(t, 0), 0.999);
    lastVisualTRef.current = t;

    // Piecewise mapping from unitless backend position to arclength parameterized t_visual
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

    groupRef.current.position.copy(targetPos);
    groupRef.current.rotation.set(0, nextRot, 0);

    if (vehicle.state === "moving") {
      wheelAngleRef.current += delta * 18;
      const a = wheelAngleRef.current;
      if (rfRef.current) rfRef.current.rotation.x = a;
      if (lfRef.current) lfRef.current.rotation.x = a;
      if (rrRef.current) rrRef.current.rotation.x = a;
      if (lrRef.current) lrRef.current.rotation.x = a;
    }

    // Siren blinking for emergency vehicle
    if (vehicle.is_emergency) {
      const flash = Math.floor(time * 8) % 2 === 0;
      if (sirenRedMeshRef.current) {
        sirenRedMeshRef.current.emissiveIntensity = flash ? 8.0 : 0.05;
      }
      if (sirenBlueMeshRef.current) {
        sirenBlueMeshRef.current.emissiveIntensity = flash ? 0.05 : 8.0;
      }
      if (sirenRedLightRef.current) {
        sirenRedLightRef.current.intensity = flash ? 4.0 : 0.0;
      }
      if (sirenBlueLightRef.current) {
        sirenBlueLightRef.current.intensity = flash ? 0.0 : 4.0;
      }
    }
  });

  const isBike = type === "bike";
  const wz = type === "sportscar" ? 0.28 : (type === "suv" || type === "ambulance") ? 0.26 : 0.24;
  const wy = -0.02;

  return (
    <group ref={groupRef}>
      <CarBody type={type} paintMat={paintMat} />

      {/* Sirens for emergency vehicle (Ambulance) */}
      {type === "ambulance" && (
        <group position={[0, 0.33, 0.1]}>
          <mesh geometry={AMBULANCE_SIREN_BAR_GEO} material={SIREN_BAR_MAT} />
          {/* Red Flasher */}
          <mesh position={[-0.08, 0.02, 0]} geometry={AMBULANCE_FLASHER_GEO}>
            <meshStandardMaterial ref={sirenRedMeshRef} color="#ff0000" emissive="#ff0000" emissiveIntensity={0.2} />
          </mesh>
          {/* Blue Flasher */}
          <mesh position={[0.08, 0.02, 0]} geometry={AMBULANCE_FLASHER_GEO}>
            <meshStandardMaterial ref={sirenBlueMeshRef} color="#0000ff" emissive="#0000ff" emissiveIntensity={0.2} />
          </mesh>
          {/* Sirens point lights */}
          <pointLight ref={sirenRedLightRef} color="#ff0000" intensity={0} distance={4} decay={2} position={[-0.08, 0.05, 0]} />
          <pointLight ref={sirenBlueLightRef} color="#0066ff" intensity={0} distance={4} decay={2} position={[0.08, 0.05, 0]} />
        </group>
      )}

      {/* Headlights (selective shadow removal for performance) */}
      {isBike ? (
        <mesh position={[0, 0.22, 0.32]} geometry={BIKE_HEADLIGHT_GEO} material={HEADLIGHT_MAT} />
      ) : (
        <>
          <mesh position={[-0.14, 0.07, 0.43]} geometry={HEADLIGHT_GEO} material={HEADLIGHT_MAT} />
          <mesh position={[0.14, 0.07, 0.43]} geometry={HEADLIGHT_GEO} material={HEADLIGHT_MAT} />
        </>
      )}

      {/* Brakelights */}
      {isBike ? (
        <mesh position={[0, 0.18, -0.32]} geometry={BIKE_BRAKELIGHT_GEO} material={brakelightMat} />
      ) : (
        <>
          <mesh position={[-0.14, 0.07, -0.43]} geometry={BRAKELIGHT_GEO} material={brakelightMat} />
          <mesh position={[0.14, 0.07, -0.43]} geometry={BRAKELIGHT_GEO} material={brakelightMat} />
        </>
      )}

      {/* Wheels */}
      {isBike ? (
        <>
          <mesh
            ref={rfRef}
            geometry={WHEEL_GEO}
            material={WHEEL_MAT}
            position={[0, wy, 0.25]}
            rotation={[0, 0, Math.PI / 2]}
          />
          <mesh
            ref={rrRef}
            geometry={WHEEL_GEO}
            material={WHEEL_MAT}
            position={[0, wy, -0.25]}
            rotation={[0, 0, Math.PI / 2]}
          />
        </>
      ) : (
        <>
          <mesh
            ref={rfRef}
            geometry={WHEEL_GEO}
            material={WHEEL_MAT}
            position={[0.22, wy, wz]}
            rotation={[0, 0, Math.PI / 2]}
          />
          <mesh
            ref={lfRef}
            geometry={WHEEL_GEO}
            material={WHEEL_MAT}
            position={[-0.22, wy, wz]}
            rotation={[0, 0, Math.PI / 2]}
          />
          <mesh
            ref={rrRef}
            geometry={WHEEL_GEO}
            material={WHEEL_MAT}
            position={[0.22, wy, -wz]}
            rotation={[0, 0, Math.PI / 2]}
          />
          <mesh
            ref={lrRef}
            geometry={WHEEL_GEO}
            material={WHEEL_MAT}
            position={[-0.22, wy, -wz]}
            rotation={[0, 0, Math.PI / 2]}
          />
        </>
      )}
    </group>
  );
}