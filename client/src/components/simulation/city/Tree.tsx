"use client";

import { useMemo } from "react";
import {
  CylinderGeometry,
  DodecahedronGeometry,
  ConeGeometry,
  BoxGeometry,
  MeshStandardMaterial,
} from "three";

export type TreeVariant = "lush" | "deep" | "blossom" | "pine" | "autumn";

interface TreeProps {
  position: [number, number, number];
  scale?: number;
  variant?: TreeVariant;
  rotationY?: number;
}

const TRUNK_COLOR = "#3e2718";
const TRUNK_ROUGHNESS = 0.9;

const FOLIAGE_CONFIG: Record<
  TreeVariant,
  { primary: string; secondary: string; emissive: string; intensity: number }
> = {
  lush: {
    primary: "#15803d",    // vibrant emerald
    secondary: "#166534",  // deep forest
    emissive: "#052e16",
    intensity: 0.15,
  },
  deep: {
    primary: "#14532d",    // dark pine
    secondary: "#0f3d21",
    emissive: "#052e16",
    intensity: 0.1,
  },
  blossom: {
    primary: "#f472b6",    // sakura pink
    secondary: "#f9a8d4",
    emissive: "#831843",
    intensity: 0.2,
  },
  pine: {
    primary: "#164e63",    // blue-green fir
    secondary: "#0e3a47",
    emissive: "#042f2e",
    intensity: 0.1,
  },
  autumn: {
    primary: "#f59e0b",    // warm amber
    secondary: "#d97706",
    emissive: "#451a03",
    intensity: 0.2,
  },
};

export function Tree({
  position,
  scale = 1,
  variant = "lush",
  rotationY = 0,
}: TreeProps) {
  const cfg = FOLIAGE_CONFIG[variant] ?? FOLIAGE_CONFIG.lush;

  // Trunk geometry: slightly tapered cylinder
  const trunkGeo = useMemo(() => new CylinderGeometry(0.09, 0.15, 0.9, 6), []);
  const trunkMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: TRUNK_COLOR,
        roughness: TRUNK_ROUGHNESS,
        metalness: 0.05,
      }),
    []
  );

  // Deciduous canopy: 3 overlapping dodecahedrons forming a lush volumetric crown
  const crownGeo1 = useMemo(() => new DodecahedronGeometry(0.55, 1), []);
  const crownGeo2 = useMemo(() => new DodecahedronGeometry(0.42, 1), []);
  const crownGeo3 = useMemo(() => new DodecahedronGeometry(0.35, 1), []);

  // Pine canopy: 3 stacked cones
  const pineCone1 = useMemo(() => new ConeGeometry(0.65, 0.7, 6), []);
  const pineCone2 = useMemo(() => new ConeGeometry(0.5, 0.6, 6), []);
  const pineCone3 = useMemo(() => new ConeGeometry(0.35, 0.5, 6), []);

  const foliageMatPrimary = useMemo(
    () =>
      new MeshStandardMaterial({
        color: cfg.primary,
        roughness: 0.6,
        metalness: 0.05,
        emissive: cfg.emissive,
        emissiveIntensity: cfg.intensity,
        flatShading: true,
      }),
    [cfg]
  );

  const foliageMatSecondary = useMemo(
    () =>
      new MeshStandardMaterial({
        color: cfg.secondary,
        roughness: 0.65,
        metalness: 0.05,
        emissive: cfg.emissive,
        emissiveIntensity: cfg.intensity * 0.8,
        flatShading: true,
      }),
    [cfg]
  );

  return (
    <group position={position} scale={[scale, scale, scale]} rotation={[0, rotationY, 0]}>
      {/* Organic Trunk */}
      <mesh
        geometry={trunkGeo}
        material={trunkMat}
        position={[0, 0.45, 0]}
        castShadow
        receiveShadow
      />

      {variant === "pine" ? (
        /* Stacked Conifer/Pine Crown */
        <group position={[0, 0.6, 0]}>
          <mesh geometry={pineCone1} material={foliageMatPrimary} position={[0, 0.35, 0]} castShadow receiveShadow />
          <mesh geometry={pineCone2} material={foliageMatSecondary} position={[0, 0.75, 0]} castShadow receiveShadow />
          <mesh geometry={pineCone3} material={foliageMatPrimary} position={[0, 1.15, 0]} castShadow />
        </group>
      ) : (
        /* Volumetric Multi-Lobed Crown */
        <group position={[0, 0.85, 0]}>
          {/* Main lower crown lobe */}
          <mesh
            geometry={crownGeo1}
            material={foliageMatPrimary}
            position={[0, 0.3, 0]}
            rotation={[0.2, 0.4, -0.1]}
            castShadow
            receiveShadow
          />
          {/* Secondary upper-left lobe */}
          <mesh
            geometry={crownGeo2}
            material={foliageMatSecondary}
            position={[-0.15, 0.65, 0.1]}
            rotation={[-0.3, 0.1, 0.2]}
            castShadow
          />
          {/* Secondary upper-right lobe */}
          <mesh
            geometry={crownGeo3}
            material={foliageMatPrimary}
            position={[0.18, 0.7, -0.12]}
            rotation={[0.1, -0.5, 0.3]}
            castShadow
          />
        </group>
      )}
    </group>
  );
}

interface HedgeProps {
  position: [number, number, number];
  size?: [number, number, number];
  rotationY?: number;
}

export function Hedge({ position, size = [1.5, 0.35, 0.4], rotationY = 0 }: HedgeProps) {
  const [w, h, d] = size;
  const hedgeGeo = useMemo(() => new BoxGeometry(w, h, d), [w, h, d]);
  const hedgeMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#166534",
        roughness: 0.7,
        metalness: 0.05,
        emissive: "#052e16",
        emissiveIntensity: 0.12,
        flatShading: true,
      }),
    []
  );

  return (
    <mesh
      geometry={hedgeGeo}
      material={hedgeMat}
      position={[position[0], position[1] + h / 2, position[2]]}
      rotation={[0, rotationY, 0]}
      castShadow
      receiveShadow
    />
  );
}
