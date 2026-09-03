"use client";

import React, { useMemo } from "react";
import {
  BoxGeometry,
  MeshStandardMaterial,
} from "three";
import {
  AntennaSpire,
  ElevatorPenthouse,
  Helipad,
  HVACUnit,
  WaterTower,
} from "./RooftopDetails";

// ── 1. Glass Curtain High-Rise (Corporate Skyscraper) ───────────────────────
interface GlassTowerProps {
  position: [number, number, number];
  size?: [number, number, number];
  accentColor?: string;
  rotationY?: number;
}

export const GlassTower = React.memo(function GlassTower({
  position,
  size = [3.2, 7.5, 3.2],
  accentColor = "#38bdf8",
  rotationY = 0,
}: GlassTowerProps) {
  const [w, h, d] = size;

  // Base Lobby podium
  const lobbyGeo = useMemo(() => new BoxGeometry(w + 0.2, 0.9, d + 0.2), [w, d]);
  const canopyGeo = useMemo(() => new BoxGeometry(1.4, 0.06, 0.6), []);
  const bodyGeo = useMemo(() => new BoxGeometry(w, h, d), [w, h, d]);
  const crownGeo = useMemo(() => new BoxGeometry(w - 0.4, 0.5, d - 0.4), [w, d]);

  // Window band horizontal spandrel strips
  const numFloors = Math.floor(h / 0.7);
  const floorSlabGeo = useMemo(() => new BoxGeometry(w + 0.04, 0.05, d + 0.04), [w, d]);

  // Facade Materials
  const glassMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#0f172a", // deep modern navy obsidian
        roughness: 0.15,
        metalness: 0.85,
      }),
    []
  );

  const lobbyGlassMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#1e293b",
        emissive: "#fef3c7",
        emissiveIntensity: 0.6,
        roughness: 0.2,
      }),
    []
  );

  const spandrelMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#1e293b",
        roughness: 0.4,
        metalness: 0.9,
      }),
    []
  );

  const accentMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: accentColor,
        emissive: accentColor,
        emissiveIntensity: 2.5,
        toneMapped: false,
      }),
    [accentColor]
  );

  const windowGlowMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#e0f2fe",
        emissive: "#7dd3fc",
        emissiveIntensity: 1.2,
        roughness: 0.2,
      }),
    []
  );

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* ── Ground Floor Glass Lobby & Canopy ── */}
      <mesh geometry={lobbyGeo} material={lobbyGlassMat} position={[0, 0.45, 0]} castShadow receiveShadow />
      <mesh geometry={canopyGeo} material={spandrelMat} position={[0, 0.75, d / 2 + 0.35]} castShadow />

      {/* ── Main Tower Body ── */}
      <mesh geometry={bodyGeo} material={glassMat} position={[0, h / 2 + 0.9, 0]} castShadow receiveShadow />

      {/* ── Horizontal Floor Spandrel Ribbons ── */}
      {Array.from({ length: numFloors }).map((_, i) => (
        <mesh
          key={i}
          geometry={floorSlabGeo}
          material={spandrelMat}
          position={[0, 0.9 + i * 0.7, 0]}
        />
      ))}

      {/* ── Vertical Architectural Accent Blades on Corners ── */}
      <mesh
        geometry={new BoxGeometry(0.06, h + 0.2, 0.06)}
        material={accentMat}
        position={[-w / 2, h / 2 + 0.9, -d / 2]}
      />
      <mesh
        geometry={new BoxGeometry(0.06, h + 0.2, 0.06)}
        material={accentMat}
        position={[w / 2, h / 2 + 0.9, -d / 2]}
      />
      <mesh
        geometry={new BoxGeometry(0.06, h + 0.2, 0.06)}
        material={accentMat}
        position={[-w / 2, h / 2 + 0.9, d / 2]}
      />
      <mesh
        geometry={new BoxGeometry(0.06, h + 0.2, 0.06)}
        material={accentMat}
        position={[w / 2, h / 2 + 0.9, d / 2]}
      />

      {/* ── Rooftop Mechanical Penthouse & Crown ── */}
      <mesh
        geometry={crownGeo}
        material={spandrelMat}
        position={[0, h + 0.9 + 0.25, 0]}
        castShadow
      />
      <ElevatorPenthouse position={[-0.4, h + 0.9 + 0.5, -0.3]} size={[1.0, 0.6, 0.8]} />
      <HVACUnit position={[0.6, h + 0.9 + 0.5, 0.4]} scale={0.9} />
      <AntennaSpire position={[0, h + 0.9 + 0.5, 0]} height={2.0} />
    </group>
  );
});

// ── 2. Stepped High-Rise Tower (Mixed-Use Commercial / Hotel) ───────────────
interface SteppedTowerProps {
  position: [number, number, number];
  rotationY?: number;
}

export const SteppedTower = React.memo(function SteppedTower({ position, rotationY = 0 }: SteppedTowerProps) {
  // 3-Tier Setback Geometry
  const tier1Geo = useMemo(() => new BoxGeometry(3.6, 2.5, 3.6), []);
  const tier2Geo = useMemo(() => new BoxGeometry(2.8, 3.0, 2.8), []);
  const tier3Geo = useMemo(() => new BoxGeometry(2.0, 2.2, 2.0), []);

  const stoneMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#1e293b",
        roughness: 0.5,
        metalness: 0.5,
      }),
    []
  );

  const glassWindowMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#38bdf8",
        emissive: "#0284c7",
        emissiveIntensity: 0.75,
        roughness: 0.2,
      }),
    []
  );

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* Tier 1 (Base Podium) */}
      <mesh geometry={tier1Geo} material={stoneMat} position={[0, 1.25, 0]} castShadow receiveShadow />
      <mesh position={[0, 1.25, 1.81]} material={glassWindowMat}>
        <planeGeometry args={[2.8, 1.4]} />
      </mesh>

      {/* Tier 2 (Mid Tower) */}
      <mesh geometry={tier2Geo} material={stoneMat} position={[0, 4.0, 0]} castShadow receiveShadow />
      <mesh position={[0, 4.0, 1.41]} material={glassWindowMat}>
        <planeGeometry args={[2.2, 1.8]} />
      </mesh>

      {/* Tier 3 (Pinnacle) */}
      <mesh geometry={tier3Geo} material={stoneMat} position={[0, 6.6, 0]} castShadow receiveShadow />
      <mesh position={[0, 6.6, 1.01]} material={glassWindowMat}>
        <planeGeometry args={[1.5, 1.4]} />
      </mesh>

      {/* Rooftop Helipad & Mechanicals */}
      <Helipad position={[0, 7.7, 0]} radius={0.85} />
      <HVACUnit position={[0.6, 7.7, 0.6]} scale={0.7} />
      <AntennaSpire position={[-0.6, 7.7, -0.6]} height={1.4} />
    </group>
  );
});

// ── 3. Mid-Rise Urban Commercial Block (Retail & Offices) ────────────────────
interface MidRiseBlockProps {
  position: [number, number, number];
  size?: [number, number, number];
  rotationY?: number;
}

export const MidRiseBlock = React.memo(function MidRiseBlock({
  position,
  size = [3.0, 3.8, 2.6],
  rotationY = 0,
}: MidRiseBlockProps) {
  const [w, h, d] = size;
  const mainGeo = useMemo(() => new BoxGeometry(w, h, d), [w, h, d]);
  const storefrontGeo = useMemo(() => new BoxGeometry(w - 0.4, 0.7, 0.06), [w]);
  const awningGeo = useMemo(() => new BoxGeometry(0.8, 0.08, 0.4), []);

  const facadeMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#334155", // limestone slate
        roughness: 0.85,
        metalness: 0.15,
      }),
    []
  );

  const storefrontMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#fde047",
        emissive: "#f59e0b",
        emissiveIntensity: 0.9,
        roughness: 0.3,
      }),
    []
  );

  const awningMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#0284c7", // deep blue fabric
        roughness: 0.9,
      }),
    []
  );

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* Main Building Body */}
      <mesh geometry={mainGeo} material={facadeMat} position={[0, h / 2, 0]} castShadow receiveShadow />

      {/* Street Frontage Storefront Display Windows */}
      <mesh
        geometry={storefrontGeo}
        material={storefrontMat}
        position={[0, 0.45, d / 2 + 0.01]}
      />
      {/* Retail Entrance Awning */}
      <mesh geometry={awningGeo} material={awningMat} position={[0, 0.95, d / 2 + 0.22]} castShadow />

      {/* Rooftop Classic Water Tower & Vent Pipes */}
      <WaterTower position={[-0.6, h, 0]} />
      <HVACUnit position={[0.6, h, 0.2]} scale={0.75} />
    </group>
  );
});

// ── 4. Contemporary Plaza Tower (Angled Tech Center) ─────────────────────────
interface PlazaTowerProps {
  position: [number, number, number];
  size?: [number, number, number];
  neonColor?: string;
  rotationY?: number;
}

export const PlazaTower = React.memo(function PlazaTower({
  position,
  size = [2.6, 5.8, 2.6],
  neonColor = "#06b6d4",
  rotationY = 0,
}: PlazaTowerProps) {
  const [w, h, d] = size;
  const towerGeo = useMemo(() => new BoxGeometry(w, h, d), [w, h, d]);
  const crownGeo = useMemo(() => new BoxGeometry(w + 0.1, 0.3, d + 0.1), [w, d]);

  const glassMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#090d16",
        roughness: 0.1,
        metalness: 0.9,
      }),
    []
  );

  const neonMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: neonColor,
        emissive: neonColor,
        emissiveIntensity: 3.0,
        toneMapped: false,
      }),
    [neonColor]
  );

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* Main Glass Tower */}
      <mesh geometry={towerGeo} material={glassMat} position={[0, h / 2, 0]} castShadow receiveShadow />

      {/* Illuminated Edge Fin Ribbons */}
      <mesh
        geometry={new BoxGeometry(0.04, h, 0.04)}
        material={neonMat}
        position={[-w / 2 + 0.02, h / 2, -d / 2 + 0.02]}
      />
      <mesh
        geometry={new BoxGeometry(0.04, h, 0.04)}
        material={neonMat}
        position={[w / 2 - 0.02, h / 2, -d / 2 + 0.02]}
      />
      <mesh
        geometry={new BoxGeometry(0.04, h, 0.04)}
        material={neonMat}
        position={[-w / 2 + 0.02, h / 2, d / 2 - 0.02]}
      />
      <mesh
        geometry={new BoxGeometry(0.04, h, 0.04)}
        material={neonMat}
        position={[w / 2 - 0.02, h / 2, d / 2 - 0.02]}
      />

      {/* Glowing Architectural Crown */}
      <mesh geometry={crownGeo} material={neonMat} position={[0, h + 0.15, 0]} />
      <AntennaSpire position={[0, h + 0.3, 0]} height={1.6} />
    </group>
  );
});
