"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { BoxGeometry, CylinderGeometry, MeshStandardMaterial, Group, Mesh, MathUtils, Vector3, CubicBezierCurve3 } from "three";
import type { VehicleState } from "@/types/simulation";

interface VehicleProps {
  vehicle: VehicleState;
  scaleProgress?: number; // Used for enter/exit scaling animations
}

function getVehicleProps(id: string) {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  const colors = [
    "#dc2626", "#2563eb", "#16a34a", "#ea580c", "#9333ea",
    "#0891b2", "#db2777", "#f1f5f9", "#18181b", "#facc15",
  ];
  const paintColor = colors[Math.abs(hash) % colors.length];
  const types = ["sedan", "suv", "hatchback", "sportscar"];
  const type = types[Math.abs(hash >> 3) % types.length];
  
  // Decide a turning direction: 50% straight, 25% left, 25% right
  const turnTypes = ["straight", "straight", "left", "right"] as const;
  const turn = turnTypes[Math.abs(hash >> 6) % turnTypes.length];
  
  return { paintColor, type, turn };
}

function getPathPoints(lane: string, turn: "straight" | "left" | "right") {
  let start: [number, number, number];
  let end: [number, number, number];
  let p1: [number, number, number];
  let p2: [number, number, number];

  const y = 0.1;
  const startDist = 12;
  const endDist = 12;

  switch (lane) {
    case "north": // Southbound
      start = [-0.5, y, startDist];
      if (turn === "straight") {
        end = [-0.5, y, -endDist];
        p1 = [-0.5, y, 2]; p2 = [-0.5, y, -2];
      } else if (turn === "left") { // Eastbound
        end = [endDist, y, 0.5];
        p1 = [-0.5, y, 0.5]; p2 = [-0.5, y, 0.5];
      } else { // Westbound
        end = [-endDist, y, -0.5];
        p1 = [-0.5, y, -0.5]; p2 = [-0.5, y, -0.5];
      }
      break;
    case "south": // Northbound
      start = [0.5, y, -startDist];
      if (turn === "straight") {
        end = [0.5, y, endDist];
        p1 = [0.5, y, -2]; p2 = [0.5, y, 2];
      } else if (turn === "left") { // Westbound
        end = [-endDist, y, -0.5];
        p1 = [0.5, y, -0.5]; p2 = [0.5, y, -0.5];
      } else { // Eastbound
        end = [endDist, y, 0.5];
        p1 = [0.5, y, 0.5]; p2 = [0.5, y, 0.5];
      }
      break;
    case "east": // Westbound
      start = [startDist, y, -0.5];
      if (turn === "straight") {
        end = [-endDist, y, -0.5];
        p1 = [2, y, -0.5]; p2 = [-2, y, -0.5];
      } else if (turn === "left") { // Southbound
        end = [-0.5, y, -endDist];
        p1 = [-0.5, y, -0.5]; p2 = [-0.5, y, -0.5];
      } else { // Northbound
        end = [0.5, y, endDist];
        p1 = [0.5, y, -0.5]; p2 = [0.5, y, -0.5];
      }
      break;
    case "west": // Eastbound
      start = [-startDist, y, 0.5];
      if (turn === "straight") {
        end = [endDist, y, 0.5];
        p1 = [-2, y, 0.5]; p2 = [2, y, 0.5];
      } else if (turn === "left") { // Northbound
        end = [0.5, y, endDist];
        p1 = [0.5, y, 0.5]; p2 = [0.5, y, 0.5];
      } else { // Southbound
        end = [-0.5, y, -endDist];
        p1 = [-0.5, y, 0.5]; p2 = [-0.5, y, 0.5];
      }
      break;
    default:
      start = [0, y, 0]; end = [0, y, 0]; p1 = [0, y, 0]; p2 = [0, y, 0];
  }
  
  return { p0: start, p1, p2, p3: end };
}

export default function Vehicle({ vehicle, scaleProgress = 1 }: VehicleProps) {
  const { paintColor, type, turn } = useMemo(() => getVehicleProps(vehicle.id), [vehicle.id]);

  const curve = useMemo(() => {
    const pts = getPathPoints(vehicle.lane, turn);
    return new CubicBezierCurve3(
      new Vector3(...pts.p0),
      new Vector3(...pts.p1),
      new Vector3(...pts.p2),
      new Vector3(...pts.p3)
    );
  }, [vehicle.lane, turn]);

  const groupRef = useRef<Group>(null);
  const currentPosRef = useRef<Vector3 | null>(null);
  const currentRotRef = useRef<number | null>(null);
  const wheelRFRef = useRef<Mesh>(null);
  const wheelLFRef = useRef<Mesh>(null);
  const wheelRRRef = useRef<Mesh>(null);
  const wheelLRRef = useRef<Mesh>(null);
  const rotationAngle = useRef(0);

  useFrame((_, delta) => {
    const progress = Math.min(Math.max(vehicle.position, 0), 1);
    const targetPos = curve.getPoint(progress);
    const tangent = curve.getTangent(progress).normalize();
    const targetRot = Math.atan2(tangent.x, tangent.z);

    if (!currentPosRef.current) {
      currentPosRef.current = targetPos.clone();
      currentRotRef.current = targetRot;
    } else {
      const lerpFactor = 0.15;
      currentPosRef.current.lerp(targetPos, lerpFactor);
      
      // Smooth angle interpolation handling wrap-around
      let rotDiff = targetRot - currentRotRef.current!;
      while (rotDiff > Math.PI) rotDiff -= 2 * Math.PI;
      while (rotDiff < -Math.PI) rotDiff += 2 * Math.PI;
      currentRotRef.current! += rotDiff * lerpFactor;
    }

    if (groupRef.current) {
      groupRef.current.position.copy(currentPosRef.current);
      groupRef.current.rotation.set(0, currentRotRef.current!, 0);
    }

    if (vehicle.state === "moving") {
      rotationAngle.current += delta * 15;
      const rot = rotationAngle.current;
      if (wheelRFRef.current) wheelRFRef.current.rotation.x = rot;
      if (wheelLFRef.current) wheelLFRef.current.rotation.x = rot;
      if (wheelRRRef.current) wheelRRRef.current.rotation.x = rot;
      if (wheelLRRef.current) wheelLRRef.current.rotation.x = rot;
    }
  });

  const paintMaterial = useMemo(() => new MeshStandardMaterial({ 
    color: paintColor, 
    roughness: 0.2, 
    metalness: 0.8,
    emissive: paintColor,
    emissiveIntensity: 0.1
  }), [paintColor]);
  
  const windowMaterial = useMemo(() => new MeshStandardMaterial({ 
    color: "#0a0a0f", 
    roughness: 0.02,
    metalness: 0.98,
    transparent: true,
    opacity: 0.85
  }), []);

  const wheelMaterial = useMemo(() => new MeshStandardMaterial({ 
    color: "#0f0f0f", 
    roughness: 0.7,
    metalness: 0.3
  }), []);

  const headlightMaterial = useMemo(() => new MeshStandardMaterial({ 
    color: "#fffacd",
    emissive: "#fffacd",
    emissiveIntensity: 2.5,
  }), []);

  const brakeLightIntensity = vehicle.state === "waiting" ? 3.5 : 0.3;
  const brakeLightMaterial = useMemo(() => new MeshStandardMaterial({ 
    color: "#ff0000",
    emissive: "#ff0000",
    emissiveIntensity: brakeLightIntensity
  }), [brakeLightIntensity]);

  const wheelGeometry = useMemo(() => new CylinderGeometry(0.08, 0.08, 0.06, 8), []);

  useEffect(() => {
    return () => {
      paintMaterial.dispose();
      windowMaterial.dispose();
      wheelMaterial.dispose();
      headlightMaterial.dispose();
      brakeLightMaterial.dispose();
      wheelGeometry.dispose();
    };
  }, [paintMaterial, windowMaterial, wheelMaterial, headlightMaterial, brakeLightMaterial, wheelGeometry]);

  const renderWheel = (ref: React.RefObject<Mesh | null>, localPos: [number, number, number]) => (
    <mesh ref={ref} position={localPos} rotation={[0, 0, Math.PI / 2]} castShadow geometry={wheelGeometry} material={wheelMaterial} />
  );

  const renderCarBody = () => {
    switch (type) {
      case "suv":
        return (
          <>
            <mesh castShadow receiveShadow position={[0, 0.1, 0]} material={paintMaterial}>
              <boxGeometry args={[0.44, 0.18, 0.8]} />
            </mesh>
            <mesh castShadow position={[0, 0.23, -0.06]} material={paintMaterial}>
              <boxGeometry args={[0.4, 0.12, 0.5]} />
            </mesh>
            <mesh position={[0, 0.23, -0.05]} material={windowMaterial}>
              <boxGeometry args={[0.41, 0.08, 0.46]} />
            </mesh>
          </>
        );
      case "hatchback":
        return (
          <>
            <mesh castShadow receiveShadow position={[0, 0.08, 0]} material={paintMaterial}>
              <boxGeometry args={[0.42, 0.14, 0.72]} />
            </mesh>
            <mesh castShadow position={[0, 0.18, -0.08]} material={paintMaterial}>
              <boxGeometry args={[0.38, 0.1, 0.42]} />
            </mesh>
            <mesh position={[0, 0.18, -0.08]} material={windowMaterial}>
              <boxGeometry args={[0.39, 0.07, 0.38]} />
            </mesh>
          </>
        );
      case "sportscar":
        return (
          <>
            <mesh castShadow receiveShadow position={[0, 0.05, 0]} material={paintMaterial}>
              <boxGeometry args={[0.46, 0.1, 0.86]} />
            </mesh>
            <mesh castShadow position={[0, 0.13, -0.04]} material={paintMaterial}>
              <boxGeometry args={[0.38, 0.08, 0.38]} />
            </mesh>
            <mesh position={[0, 0.13, -0.04]} material={windowMaterial}>
              <boxGeometry args={[0.39, 0.06, 0.34]} />
            </mesh>
            <group position={[0, 0.13, -0.38]}>
              <mesh position={[-0.16, -0.03, 0]}>
                <boxGeometry args={[0.02, 0.06, 0.02]} />
                <meshStandardMaterial color="#18181b" />
              </mesh>
              <mesh position={[0.16, -0.03, 0]}>
                <boxGeometry args={[0.02, 0.06, 0.02]} />
                <meshStandardMaterial color="#18181b" />
              </mesh>
              <mesh position={[0, 0, 0]} castShadow>
                <boxGeometry args={[0.42, 0.015, 0.08]} />
                <meshStandardMaterial color="#18181b" roughness={0.1} />
              </mesh>
            </group>
          </>
        );
      case "sedan":
      default:
        return (
          <>
            <mesh castShadow receiveShadow position={[0, 0.08, 0]} material={paintMaterial}>
              <boxGeometry args={[0.42, 0.14, 0.82]} />
            </mesh>
            <mesh castShadow position={[0, 0.18, -0.04]} material={paintMaterial}>
              <boxGeometry args={[0.38, 0.1, 0.44]} />
            </mesh>
            <mesh position={[0, 0.18, -0.04]} material={windowMaterial}>
              <boxGeometry args={[0.39, 0.07, 0.4]} />
            </mesh>
          </>
        );
    }
  };

  const wheelZOffset = type === "sportscar" ? 0.25 : type === "suv" ? 0.23 : 0.21;
  const wheelYOffset = -0.02;

  return (
    <group ref={groupRef} scale={[scaleProgress, scaleProgress, scaleProgress]}>
      {renderCarBody()}
      <mesh position={[-0.15, 0.06, 0.4]} castShadow material={headlightMaterial}>
        <boxGeometry args={[0.05, 0.04, 0.01]} />
      </mesh>
      <mesh position={[0.15, 0.06, 0.4]} castShadow material={headlightMaterial}>
        <boxGeometry args={[0.05, 0.04, 0.01]} />
      </mesh>
      <mesh position={[-0.15, 0.06, -0.4]} castShadow material={brakeLightMaterial}>
        <boxGeometry args={[0.05, 0.04, 0.01]} />
      </mesh>
      <mesh position={[0.15, 0.06, -0.4]} castShadow material={brakeLightMaterial}>
        <boxGeometry args={[0.05, 0.04, 0.01]} />
      </mesh>
      {renderWheel(wheelRFRef, [0.21, wheelYOffset, wheelZOffset])}
      {renderWheel(wheelLFRef, [-0.21, wheelYOffset, wheelZOffset])}
      {renderWheel(wheelRRRef, [0.21, wheelYOffset, -wheelZOffset])}
      {renderWheel(wheelLRRef, [-0.21, wheelYOffset, -wheelZOffset])}
    </group>
  );
}