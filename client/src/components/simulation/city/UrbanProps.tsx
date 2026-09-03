"use client";

import { useMemo } from "react";
import {
  BoxGeometry,
  CylinderGeometry,
  MeshStandardMaterial,
  TorusGeometry,
} from "three";

// ── 1. Modern Minimalist Gooseneck Streetlight ──────────────────────────────
interface StreetlightProps {
  position: [number, number, number];
  rotationY?: number;
  lightColor?: string;
}

export function Streetlight({
  position,
  rotationY = 0,
  lightColor = "#fef08a",
}: StreetlightProps) {
  const poleGeo = useMemo(() => new CylinderGeometry(0.035, 0.05, 2.3, 8), []);
  const baseGeo = useMemo(() => new CylinderGeometry(0.09, 0.12, 0.15, 8), []);
  const armGeo  = useMemo(() => new CylinderGeometry(0.025, 0.025, 0.6, 6), []);
  const lampHeadGeo = useMemo(() => new BoxGeometry(0.12, 0.05, 0.25), []);
  const lensGeo = useMemo(() => new BoxGeometry(0.09, 0.015, 0.2), []);

  const poleMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#1e293b", // dark slate industrial steel
        roughness: 0.4,
        metalness: 0.8,
      }),
    []
  );

  const luminaireMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: lightColor,
        emissive: lightColor,
        emissiveIntensity: 3.5,
        toneMapped: false,
      }),
    [lightColor]
  );

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* Base collar */}
      <mesh geometry={baseGeo} material={poleMat} position={[0, 0.075, 0]} castShadow />
      {/* Vertical pole */}
      <mesh geometry={poleGeo} material={poleMat} position={[0, 1.15, 0]} castShadow />
      {/* Horizontal cantilever arm extending towards street */}
      <mesh
        geometry={armGeo}
        material={poleMat}
        position={[0, 2.25, 0.25]}
        rotation={[Math.PI / 2.3, 0, 0]}
        castShadow
      />
      {/* Lamp Head housing */}
      <mesh geometry={lampHeadGeo} material={poleMat} position={[0, 2.35, 0.5]} castShadow />
      {/* Emissive LED Light Lens */}
      <mesh geometry={lensGeo} material={luminaireMat} position={[0, 2.32, 0.5]} />
    </group>
  );
}

// ── 2. City Park Bench (Wood & Cast Iron) ────────────────────────────────────
interface ParkBenchProps {
  position: [number, number, number];
  rotationY?: number;
}

export function ParkBench({ position, rotationY = 0 }: ParkBenchProps) {
  const slatGeo = useMemo(() => new BoxGeometry(1.2, 0.035, 0.1), []);
  const backSlatGeo = useMemo(() => new BoxGeometry(1.2, 0.12, 0.035), []);
  const legGeo = useMemo(() => new BoxGeometry(0.05, 0.35, 0.35), []);

  const woodMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#b45309", // warm polished teak/cedar
        roughness: 0.6,
        metalness: 0.1,
      }),
    []
  );

  const ironMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#0f172a", // black cast iron
        roughness: 0.5,
        metalness: 0.8,
      }),
    []
  );

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* Iron Side Legs */}
      <mesh geometry={legGeo} material={ironMat} position={[-0.5, 0.175, 0]} castShadow />
      <mesh geometry={legGeo} material={ironMat} position={[0.5, 0.175, 0]} castShadow />

      {/* Seat Slats */}
      <mesh geometry={slatGeo} material={woodMat} position={[0, 0.35, -0.08]} castShadow />
      <mesh geometry={slatGeo} material={woodMat} position={[0, 0.35, 0.08]} castShadow />

      {/* Backrest */}
      <mesh geometry={backSlatGeo} material={woodMat} position={[0, 0.55, -0.16]} castShadow />
    </group>
  );
}

// ── 3. Street Corner Fire Hydrant ───────────────────────────────────────────
export function FireHydrant({
  position,
  rotationY = 0,
}: {
  position: [number, number, number];
  rotationY?: number;
}) {
  const bodyGeo = useMemo(() => new CylinderGeometry(0.07, 0.085, 0.38, 8), []);
  const capGeo  = useMemo(() => new CylinderGeometry(0.06, 0.07, 0.08, 8), []);
  const nozzleGeo = useMemo(() => new CylinderGeometry(0.03, 0.03, 0.22, 6), []);

  const redMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#dc2626", // safety red
        roughness: 0.3,
        metalness: 0.5,
      }),
    []
  );

  const brassMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#eab308", // brass caps
        roughness: 0.3,
        metalness: 0.9,
      }),
    []
  );

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* Main barrel */}
      <mesh geometry={bodyGeo} material={redMat} position={[0, 0.19, 0]} castShadow />
      {/* Top cap */}
      <mesh geometry={capGeo} material={brassMat} position={[0, 0.39, 0]} castShadow />
      {/* Side connection nozzles */}
      <mesh
        geometry={nozzleGeo}
        material={brassMat}
        position={[0, 0.26, 0]}
        rotation={[0, 0, Math.PI / 2]}
        castShadow
      />
    </group>
  );
}

// ── 4. Granite Planter Box with Shrub ────────────────────────────────────────
export function PlanterBox({
  position,
  size = [1.2, 0.4, 0.5],
  rotationY = 0,
}: {
  position: [number, number, number];
  size?: [number, number, number];
  rotationY?: number;
}) {
  const [w, h, d] = size;
  const stoneGeo = useMemo(() => new BoxGeometry(w, h, d), [w, h, d]);
  const soilGeo  = useMemo(() => new BoxGeometry(w - 0.08, 0.04, d - 0.08), [w, d]);
  const bushGeo  = useMemo(() => new BoxGeometry(w - 0.12, 0.22, d - 0.12), [w, d]);

  const stoneMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#334155", // dark granite
        roughness: 0.8,
        metalness: 0.1,
      }),
    []
  );

  const soilMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#1c1917", // dark soil
        roughness: 0.95,
      }),
    []
  );

  const foliageMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#15803d",
        roughness: 0.6,
        emissive: "#052e16",
        emissiveIntensity: 0.15,
        flatShading: true,
      }),
    []
  );

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* Stone Planter Frame */}
      <mesh geometry={stoneGeo} material={stoneMat} position={[0, h / 2, 0]} castShadow receiveShadow />
      {/* Soil */}
      <mesh geometry={soilGeo} material={soilMat} position={[0, h - 0.02, 0]} />
      {/* Foliage Hedge in Planter */}
      <mesh geometry={bushGeo} material={foliageMat} position={[0, h + 0.11, 0]} castShadow />
    </group>
  );
}

// ── 5. Sidewalk Security Bollard ────────────────────────────────────────────
export function Bollard({
  position,
}: {
  position: [number, number, number];
}) {
  const postGeo = useMemo(() => new CylinderGeometry(0.04, 0.04, 0.5, 8), []);
  const ringGeo = useMemo(() => new TorusGeometry(0.042, 0.008, 4, 12), []);

  const steelMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#475569",
        roughness: 0.3,
        metalness: 0.8,
      }),
    []
  );

  const reflectMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#f59e0b",
        emissive: "#f59e0b",
        emissiveIntensity: 0.8,
      }),
    []
  );

  return (
    <group position={position}>
      <mesh geometry={postGeo} material={steelMat} position={[0, 0.25, 0]} castShadow />
      <mesh
        geometry={ringGeo}
        material={reflectMat}
        position={[0, 0.42, 0]}
        rotation={[Math.PI / 2, 0, 0]}
      />
    </group>
  );
}
