"use client";

import { useMemo } from "react";
import {
  BoxGeometry,
  CylinderGeometry,
  ConeGeometry,
  MeshStandardMaterial,
  RingGeometry,
} from "three";

// ── 1. Industrial HVAC Chiller / Air-Handling Unit ──────────────────────────
export function HVACUnit({
  position,
  scale = 1,
}: {
  position: [number, number, number];
  scale?: number;
}) {
  const boxGeo = useMemo(() => new BoxGeometry(0.7 * scale, 0.35 * scale, 0.5 * scale), [scale]);
  const fanGeo = useMemo(() => new CylinderGeometry(0.14 * scale, 0.14 * scale, 0.06 * scale, 8), [scale]);

  const metalMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#475569", // industrial galvanized steel
        roughness: 0.5,
        metalness: 0.7,
      }),
    []
  );

  const fanMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#0f172a", // dark fan grill
        roughness: 0.7,
        metalness: 0.9,
      }),
    []
  );

  return (
    <group position={position}>
      {/* Main Chiller Body */}
      <mesh geometry={boxGeo} material={metalMat} position={[0, (0.35 * scale) / 2, 0]} castShadow />
      {/* Dual Exhaust Fans on top */}
      <mesh
        geometry={fanGeo}
        material={fanMat}
        position={[-0.18 * scale, 0.35 * scale + (0.03 * scale), 0]}
      />
      <mesh
        geometry={fanGeo}
        material={fanMat}
        position={[0.18 * scale, 0.35 * scale + (0.03 * scale), 0]}
      />
    </group>
  );
}

// ── 2. Elevator Shaft & Stairwell Access Penthouse ──────────────────────────
export function ElevatorPenthouse({
  position,
  size = [1.2, 0.7, 1.0],
}: {
  position: [number, number, number];
  size?: [number, number, number];
}) {
  const [w, h, d] = size;
  const houseGeo = useMemo(() => new BoxGeometry(w, h, d), [w, h, d]);
  const doorGeo  = useMemo(() => new BoxGeometry(0.25, 0.45, 0.02), []);

  const houseMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#1e293b",
        roughness: 0.8,
        metalness: 0.2,
      }),
    []
  );

  const doorMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#0f172a",
        roughness: 0.4,
        metalness: 0.8,
      }),
    []
  );

  return (
    <group position={position}>
      <mesh geometry={houseGeo} material={houseMat} position={[0, h / 2, 0]} castShadow receiveShadow />
      {/* Maintenance Access Door */}
      <mesh geometry={doorGeo} material={doorMat} position={[0, 0.225, d / 2 + 0.01]} />
    </group>
  );
}

// ── 3. Communications Tower & Red Aviation Beacon ──────────────────────────
export function AntennaSpire({
  position,
  height = 1.8,
}: {
  position: [number, number, number];
  height?: number;
}) {
  const mastGeo = useMemo(() => new CylinderGeometry(0.015, 0.045, height, 6), [height]);
  const tipGeo  = useMemo(() => new CylinderGeometry(0.035, 0.035, 0.06, 6), []);

  const mastMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#cbd5e1",
        roughness: 0.3,
        metalness: 0.9,
      }),
    []
  );

  const beaconMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#ef4444",
        emissive: "#ef4444",
        emissiveIntensity: 4.0,
        toneMapped: false,
      }),
    []
  );

  return (
    <group position={position}>
      <mesh geometry={mastGeo} material={mastMat} position={[0, height / 2, 0]} castShadow />
      {/* Glowing Red Warning Beacon */}
      <mesh geometry={tipGeo} material={beaconMat} position={[0, height + 0.03, 0]} />
    </group>
  );
}

// ── 4. Classic Urban Rooftop Water Tower ────────────────────────────────────
export function WaterTower({
  position,
}: {
  position: [number, number, number];
}) {
  const tankGeo = useMemo(() => new CylinderGeometry(0.38, 0.38, 0.6, 12), []);
  const roofGeo = useMemo(() => new ConeGeometry(0.44, 0.25, 12), []);
  const legGeo  = useMemo(() => new CylinderGeometry(0.02, 0.02, 0.5, 4), []);

  const woodTankMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#78350f", // cedar/redwood staves
        roughness: 0.8,
        metalness: 0.1,
      }),
    []
  );

  const steelLegMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#334155", // dark steel framework
        roughness: 0.5,
        metalness: 0.8,
      }),
    []
  );

  return (
    <group position={position}>
      {/* 4 Steel Stilt Legs */}
      <mesh geometry={legGeo} material={steelLegMat} position={[-0.22, 0.25, -0.22]} />
      <mesh geometry={legGeo} material={steelLegMat} position={[0.22, 0.25, -0.22]} />
      <mesh geometry={legGeo} material={steelLegMat} position={[-0.22, 0.25, 0.22]} />
      <mesh geometry={legGeo} material={steelLegMat} position={[0.22, 0.25, 0.22]} />

      {/* Cylindrical Water Tank */}
      <mesh geometry={tankGeo} material={woodTankMat} position={[0, 0.8, 0]} castShadow />
      {/* Conical Roof Cap */}
      <mesh geometry={roofGeo} material={steelLegMat} position={[0, 1.225, 0]} castShadow />
    </group>
  );
}

// ── 5. Rooftop Helipad ──────────────────────────────────────────────────────
export function Helipad({
  position,
  radius = 1.0,
}: {
  position: [number, number, number];
  radius?: number;
}) {
  const padGeo   = useMemo(() => new CylinderGeometry(radius, radius, 0.05, 16), [radius]);
  const ringGeo  = useMemo(() => new RingGeometry(radius * 0.7, radius * 0.78, 16), [radius]);
  const hBar1Geo = useMemo(() => new BoxGeometry(radius * 0.1, 0.01, radius * 0.7), [radius]);
  const hBar2Geo = useMemo(() => new BoxGeometry(radius * 0.4, 0.01, radius * 0.1), [radius]);

  const padMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#1e293b",
        roughness: 0.7,
      }),
    []
  );

  const markMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#f59e0b", // aviation yellow
        emissive: "#f59e0b",
        emissiveIntensity: 0.5,
      }),
    []
  );

  return (
    <group position={position}>
      <mesh geometry={padGeo} material={padMat} position={[0, 0.025, 0]} receiveShadow />
      {/* Yellow Landing Circle */}
      <mesh
        geometry={ringGeo}
        material={markMat}
        position={[0, 0.055, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      />
      {/* 'H' Marking */}
      <mesh geometry={hBar1Geo} material={markMat} position={[-radius * 0.18, 0.056, 0]} />
      <mesh geometry={hBar1Geo} material={markMat} position={[radius * 0.18, 0.056, 0]} />
      <mesh geometry={hBar2Geo} material={markMat} position={[0, 0.056, 0]} />
    </group>
  );
}
