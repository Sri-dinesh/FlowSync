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
    primary: "#15803d",
    secondary: "#166534",
    emissive: "#052e16",
    intensity: 0.15,
  },
  deep: {
    primary: "#14532d",
    secondary: "#0f3d21",
    emissive: "#052e16",
    intensity: 0.1,
  },
  blossom: {
    primary: "#f472b6",
    secondary: "#f9a8d4",
    emissive: "#831843",
    intensity: 0.2,
  },
  pine: {
    primary: "#164e63",
    secondary: "#0e3a47",
    emissive: "#042f2e",
    intensity: 0.1,
  },
  autumn: {
    primary: "#f59e0b",
    secondary: "#d97706",
    emissive: "#451a03",
    intensity: 0.2,
  },
};

// ── Shared Module Geometries (Zero GC Churn) ─────────────────────────────────
const TRUNK_GEO = new CylinderGeometry(0.09, 0.15, 0.9, 6);
const CROWN_GEO1 = new DodecahedronGeometry(0.55, 1);
const CROWN_GEO2 = new DodecahedronGeometry(0.42, 1);
const CROWN_GEO3 = new DodecahedronGeometry(0.35, 1);
const PINE_CONE1 = new ConeGeometry(0.65, 0.7, 6);
const PINE_CONE2 = new ConeGeometry(0.5, 0.6, 6);
const PINE_CONE3 = new ConeGeometry(0.35, 0.5, 6);

const TRUNK_MAT = new MeshStandardMaterial({
  color: TRUNK_COLOR,
  roughness: TRUNK_ROUGHNESS,
  metalness: 0.05,
});

// Precomputed foliage materials per variant
const FOLIAGE_MATS = Object.entries(FOLIAGE_CONFIG).reduce(
  (acc, [key, cfg]) => {
    acc[key as TreeVariant] = {
      primary: new MeshStandardMaterial({
        color: cfg.primary,
        roughness: 0.6,
        metalness: 0.05,
        emissive: cfg.emissive,
        emissiveIntensity: cfg.intensity,
        flatShading: true,
      }),
      secondary: new MeshStandardMaterial({
        color: cfg.secondary,
        roughness: 0.65,
        metalness: 0.05,
        emissive: cfg.emissive,
        emissiveIntensity: cfg.intensity * 0.8,
        flatShading: true,
      }),
    };
    return acc;
  },
  {} as Record<TreeVariant, { primary: MeshStandardMaterial; secondary: MeshStandardMaterial }>
);

export function Tree({
  position,
  scale = 1,
  variant = "lush",
  rotationY = 0,
}: TreeProps) {
  const mats = FOLIAGE_MATS[variant] ?? FOLIAGE_MATS.lush;

  return (
    <group position={position} scale={[scale, scale, scale]} rotation={[0, rotationY, 0]}>
      {/* Organic Trunk */}
      <mesh
        geometry={TRUNK_GEO}
        material={TRUNK_MAT}
        position={[0, 0.45, 0]}
        castShadow
        receiveShadow
      />

      {variant === "pine" ? (
        /* Stacked Conifer/Pine Crown */
        <group position={[0, 0.6, 0]}>
          <mesh geometry={PINE_CONE1} material={mats.primary} position={[0, 0.35, 0]} castShadow receiveShadow />
          <mesh geometry={PINE_CONE2} material={mats.secondary} position={[0, 0.75, 0]} castShadow receiveShadow />
          <mesh geometry={PINE_CONE3} material={mats.primary} position={[0, 1.15, 0]} castShadow />
        </group>
      ) : (
        /* Volumetric Multi-Lobed Crown */
        <group position={[0, 0.85, 0]}>
          {/* Main lower crown lobe */}
          <mesh
            geometry={CROWN_GEO1}
            material={mats.primary}
            position={[0, 0.3, 0]}
            rotation={[0.2, 0.4, -0.1]}
            castShadow
            receiveShadow
          />
          {/* Secondary upper-left lobe */}
          <mesh
            geometry={CROWN_GEO2}
            material={mats.secondary}
            position={[-0.15, 0.65, 0.1]}
            rotation={[-0.3, 0.1, 0.2]}
            castShadow
          />
          {/* Secondary upper-right lobe */}
          <mesh
            geometry={CROWN_GEO3}
            material={mats.primary}
            position={[0.18, 0.7, -0.12]}
            rotation={[0.1, -0.5, 0.3]}
            castShadow
          />
        </group>
      )}
    </group>
  );
}

const DEFAULT_HEDGE_GEO = new BoxGeometry(1.5, 0.35, 0.4);
const HEDGE_MAT = new MeshStandardMaterial({
  color: "#166534",
  roughness: 0.7,
  metalness: 0.05,
  emissive: "#052e16",
  emissiveIntensity: 0.12,
  flatShading: true,
});

interface HedgeProps {
  position: [number, number, number];
  size?: [number, number, number];
  rotationY?: number;
}

export function Hedge({ position, size = [1.5, 0.35, 0.4], rotationY = 0 }: HedgeProps) {
  const [w, h, d] = size;
  const isDefaultSize = w === 1.5 && h === 0.35 && d === 0.4;
  const hedgeGeo = useMemo(() => (isDefaultSize ? DEFAULT_HEDGE_GEO : new BoxGeometry(w, h, d)), [w, h, d, isDefaultSize]);

  return (
    <mesh
      geometry={hedgeGeo}
      material={HEDGE_MAT}
      position={[position[0], position[1] + h / 2, position[2]]}
      rotation={[0, rotationY, 0]}
      castShadow
      receiveShadow
    />
  );
}
