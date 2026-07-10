"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import {
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
    case "bike":
      return (
        <>
          {/* Main frame block */}
          <mesh castShadow receiveShadow position={[0, 0.12, 0]} material={mats.window}>
            <boxGeometry args={[0.12, 0.20, 0.45]} />
          </mesh>
          {/* Fuel tank */}
          <mesh castShadow position={[0, 0.22, 0.08]} material={mats.paint}>
            <boxGeometry args={[0.11, 0.08, 0.18]} />
          </mesh>
          {/* Rider seat */}
          <mesh castShadow position={[0, 0.20, -0.08]} material={mats.wheel}>
            <boxGeometry args={[0.10, 0.03, 0.16]} />
          </mesh>
          {/* Handlebars */}
          <mesh position={[0, 0.25, 0.16]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.015, 0.015, 0.26, 8]} />
            <meshStandardMaterial color="#0f0f0f" roughness={0.5} />
          </mesh>
        </>
      );
    case "ambulance":
      return (
        <>
          {/* Main Ambulance Body */}
          <mesh castShadow receiveShadow position={[0, 0.18, -0.05]} material={mats.paint}>
            <boxGeometry args={[0.46, 0.28, 0.85]} />
          </mesh>
          {/* Driver Cab (Front) */}
          <mesh castShadow position={[0, 0.11, 0.35]} material={mats.paint}>
            <boxGeometry args={[0.44, 0.14, 0.25]} />
          </mesh>
          {/* Cab Window */}
          <mesh position={[0, 0.13, 0.38]} material={mats.window}>
            <boxGeometry args={[0.41, 0.08, 0.18]} />
          </mesh>
          {/* Red Cross Left Side */}
          <group position={[-0.231, 0.18, -0.05]} rotation={[0, -Math.PI / 2, 0]}>
            <mesh castShadow>
              <boxGeometry args={[0.12, 0.03, 0.005]} />
              <meshStandardMaterial color="#dc2626" roughness={0.3} />
            </mesh>
            <mesh castShadow>
              <boxGeometry args={[0.03, 0.12, 0.005]} />
              <meshStandardMaterial color="#dc2626" roughness={0.3} />
            </mesh>
          </group>
          {/* Red Cross Right Side */}
          <group position={[0.231, 0.18, -0.05]} rotation={[0, Math.PI / 2, 0]}>
            <mesh castShadow>
              <boxGeometry args={[0.12, 0.03, 0.005]} />
              <meshStandardMaterial color="#dc2626" roughness={0.3} />
            </mesh>
            <mesh castShadow>
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

interface VehicleProps {
  vehicle: VehicleState;
}

export default function Vehicle({ vehicle }: VehicleProps) {
  const turn = (vehicle.turn ?? "straight") as Turn;
  const { paintColor, type } = useMemo(() => getVehicleProps(vehicle.id, vehicle.is_emergency), [vehicle.id, vehicle.is_emergency]);
  const mats = useMaterials(paintColor, vehicle.state === "waiting");

  const curve = useMemo(() => buildCurve(vehicle.lane, turn), [vehicle.lane, turn]);
  const t_stop = useMemo(() => (SPAWN_DIST - 3.5) / curve.getLength(), [curve]);

  const groupRef = useRef<Group>(null);
  const smoothRotRef = useRef<number | null>(null);
  const wheelAngleRef = useRef(0);
  const rfRef = useRef<Mesh>(null);
  const lfRef = useRef<Mesh>(null);
  const rrRef = useRef<Mesh>(null);
  const lrRef = useRef<Mesh>(null);

  // Siren refs for emergency vehicles
  const sirenRedMeshRef = useRef<any>(null);
  const sirenBlueMeshRef = useRef<any>(null);
  const sirenRedLightRef = useRef<any>(null);
  const sirenBlueLightRef = useRef<any>(null);

  // Smooth interpolation refs
  const lastTargetPosRef = useRef(vehicle.position);
  const startPosRef = useRef(vehicle.position);
  const lastVisualTRef = useRef(vehicle.position);
  const lastUpdateTimeRef = useRef<number | null>(null);
  const lastUpdateIntervalRef = useRef(0.1);

  const wheelGeo = useMemo(() => new CylinderGeometry(0.09, 0.09, 0.07, 10), []);

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
      <CarBody type={type} mats={mats} />

      {/* Sirens for emergency vehicle (Ambulance) */}
      {type === "ambulance" && (
        <group position={[0, 0.33, 0.1]}>
          {/* Siren Base Bar */}
          <mesh castShadow>
            <boxGeometry args={[0.3, 0.03, 0.06]} />
            <meshStandardMaterial color="#1f2937" metalness={0.8} roughness={0.2} />
          </mesh>
          {/* Red Flasher */}
          <mesh position={[-0.08, 0.02, 0]}>
            <boxGeometry args={[0.1, 0.03, 0.05]} />
            <meshStandardMaterial ref={sirenRedMeshRef} color="#ff0000" emissive="#ff0000" emissiveIntensity={0.2} />
          </mesh>
          {/* Blue Flasher */}
          <mesh position={[0.08, 0.02, 0]}>
            <boxGeometry args={[0.1, 0.03, 0.05]} />
            <meshStandardMaterial ref={sirenBlueMeshRef} color="#0000ff" emissive="#0000ff" emissiveIntensity={0.2} />
          </mesh>
          {/* Sirens point lights */}
          <pointLight ref={sirenRedLightRef} color="#ff0000" intensity={0} distance={4} decay={2} position={[-0.08, 0.05, 0]} />
          <pointLight ref={sirenBlueLightRef} color="#0066ff" intensity={0} distance={4} decay={2} position={[0.08, 0.05, 0]} />
        </group>
      )}

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