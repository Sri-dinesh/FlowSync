"use client";

import { useEffect, useMemo } from "react";
import { BoxGeometry, CylinderGeometry, MeshPhysicalMaterial, MeshStandardMaterial, PlaneGeometry } from "three";

// Stylized Tree component to populate parks
function LowPolyTree({ position }: { position: [number, number, number] }) {
  const trunkGeo = useMemo(() => new CylinderGeometry(0.08, 0.12, 0.7, 5), []);
  const trunkMat = useMemo(() => new MeshStandardMaterial({ color: "#5c2d17", roughness: 0.8, metalness: 0.2 }), []);
  
  const foliageGeo1 = useMemo(() => new BoxGeometry(0.5, 0.5, 0.5), []);
  const foliageGeo2 = useMemo(() => new BoxGeometry(0.35, 0.35, 0.35), []);
  const foliageMat = useMemo(() => new MeshStandardMaterial({ 
    color: "#059669", 
    roughness: 0.5,
    emissive: "#064e3b",
    emissiveIntensity: 0.3
  }), []);

  useEffect(() => {
    return () => {
      trunkGeo.dispose();
      trunkMat.dispose();
      foliageGeo1.dispose();
      foliageGeo2.dispose();
      foliageMat.dispose();
    };
  }, [trunkGeo, trunkMat, foliageGeo1, foliageGeo2, foliageMat]);

  return (
    <group position={position}>
      <mesh geometry={trunkGeo} material={trunkMat} position={[0, 0.35, 0]} castShadow />
      <mesh geometry={foliageGeo1} material={foliageMat} position={[0, 0.75, 0]} castShadow receiveShadow />
      <mesh geometry={foliageGeo2} material={foliageMat} position={[0.08, 1.05, -0.05]} castShadow />
    </group>
  );
}

// Stylized Skyscraper
interface SkyscraperProps {
  position: [number, number, number];
  size: [number, number, number];
  neonColor: string;
}

function Skyscraper({ position, size, neonColor }: SkyscraperProps) {
  const [w, h, d] = size;
  const buildingGeo = useMemo(() => new BoxGeometry(w, h, d), [w, h, d]);
  const buildingMat = useMemo(() => new MeshPhysicalMaterial({ 
    color: "#0a0a0c", 
    roughness: 0.1, 
    metalness: 0.9,
    clearcoat: 1.0,
    clearcoatRoughness: 0.1,
    reflectivity: 1.0
  }), []);

  const stripeGeo = useMemo(() => new BoxGeometry(0.04, h - 0.2, 0.04), [h]);
  const stripeMat = useMemo(() => new MeshStandardMaterial({
    color: neonColor,
    emissive: neonColor,
    emissiveIntensity: 3.5,
  }), [neonColor]);

  useEffect(() => {
    return () => {
      buildingGeo.dispose();
      buildingMat.dispose();
      stripeGeo.dispose();
      stripeMat.dispose();
    };
  }, [buildingGeo, buildingMat, stripeGeo, stripeMat]);

  return (
    <group position={position}>
      <mesh geometry={buildingGeo} material={buildingMat} position={[0, h / 2, 0]} castShadow receiveShadow />
      <mesh geometry={stripeGeo} material={stripeMat} position={[-w / 2 + 0.02, h / 2, -d / 2 + 0.02]} />
      <mesh geometry={stripeGeo} material={stripeMat} position={[w / 2 - 0.02, h / 2, -d / 2 + 0.02]} />
      <mesh geometry={stripeGeo} material={stripeMat} position={[-w / 2 + 0.02, h / 2, d / 2 - 0.02]} />
      <mesh geometry={stripeGeo} material={stripeMat} position={[w / 2 - 0.02, h / 2, d / 2 - 0.02]} />
    </group>
  );
}

export default function CityGrid() {
  const groundGeo = useMemo(() => new PlaneGeometry(60, 60), []);
  const groundMat = useMemo(() => new MeshPhysicalMaterial({
    color: "#0f111a",
    roughness: 0.7,
    metalness: 0.3,
    clearcoat: 0.2,
    clearcoatRoughness: 0.8,
  }), []);

  // Shared sidewalk base for each 14x14 block
  const curbGeo = useMemo(() => new BoxGeometry(14.0, 0.06, 14.0), []);
  const curbMat = useMemo(() => new MeshStandardMaterial({
    color: "#52525b",
    roughness: 0.7,
    metalness: 0.1,
  }), []);

  // Park grass tiles
  const parkGrassGeo = useMemo(() => new BoxGeometry(13.6, 0.02, 13.6), []);
  const parkGrassMat = useMemo(() => new MeshPhysicalMaterial({
    color: "#1a3610",
    roughness: 0.9,
    metalness: 0.05,
    clearcoat: 0.0,
    emissive: "#0a1a05",
    emissiveIntensity: 0.2,
  }), []);

  useEffect(() => {
    return () => {
      groundGeo.dispose();
      groundMat.dispose();
      curbGeo.dispose();
      curbMat.dispose();
      parkGrassGeo.dispose();
      parkGrassMat.dispose();
    };
  }, [groundGeo, groundMat, curbGeo, curbMat, parkGrassGeo, parkGrassMat]);

  return (
    <group>
      {/* Underlying dark base ground plane */}
      <mesh
        geometry={groundGeo}
        material={groundMat}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0, 0]}
        receiveShadow
      />

      {/* ── Pocket 1: Center Park [0, 0] ── */}
      <group position={[0, 0.03, 0]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={parkGrassGeo} material={parkGrassMat} position={[0, 0.04, 0]} receiveShadow />
        {/* Monument in center */}
        <mesh position={[0, 0.8, 0]} castShadow>
          <boxGeometry args={[0.8, 1.5, 0.8]} />
          <meshStandardMaterial color="#27272a" roughness={0.2} metalness={0.8} />
        </mesh>
        <mesh position={[0, 1.6, 0]}>
          <sphereGeometry args={[0.3, 16, 16]} />
          <meshStandardMaterial color="#06b6d4" emissive="#06b6d4" emissiveIntensity={2.5} />
        </mesh>
        <LowPolyTree position={[-3.5, 0.04, -3.5]} />
        <LowPolyTree position={[3.5, 0.04, 3.5]} />
        <LowPolyTree position={[-3.5, 0.04, 3.5]} />
        <LowPolyTree position={[3.5, 0.04, -3.5]} />
      </group>

      {/* ── Pocket 2: NW Park [-20, -20] ── */}
      <group position={[-20, 0.03, -20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={parkGrassGeo} material={parkGrassMat} position={[0, 0.04, 0]} receiveShadow />
        <LowPolyTree position={[-2, 0.04, -2]} />
        <LowPolyTree position={[2, 0.04, 2]} />
        <LowPolyTree position={[-2.5, 0.04, 2.5]} />
        <LowPolyTree position={[2.5, 0.04, -2.5]} />
        <LowPolyTree position={[0, 0.04, 3.5]} />
      </group>

      {/* ── Pocket 3: SE Park [20, 20] ── */}
      <group position={[20, 0.03, 20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={parkGrassGeo} material={parkGrassMat} position={[0, 0.04, 0]} receiveShadow />
        <LowPolyTree position={[-2, 0.04, -2]} />
        <LowPolyTree position={[2, 0.04, 2]} />
        <LowPolyTree position={[-2.5, 0.04, 2.5]} />
        <LowPolyTree position={[2.5, 0.04, -2.5]} />
        <LowPolyTree position={[3.5, 0.04, 0]} />
      </group>

      {/* ── Pocket 4: NE Skyscraper Block [20, -20] ── */}
      <group position={[20, 0.03, -20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <Skyscraper position={[-2, 0.03, -2]} size={[2.2, 3.5, 2.2]} neonColor="#06b6d4" />
        <Skyscraper position={[2, 0.03, 2]} size={[2.0, 4.5, 2.0]} neonColor="#f59e0b" />
        <Skyscraper position={[2, 0.03, -2]} size={[1.8, 2.6, 1.8]} neonColor="#d946ef" />
      </group>

      {/* ── Pocket 5: SW Skyscraper Block [-20, 20] ── */}
      <group position={[-20, 0.03, 20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <Skyscraper position={[2, 0.03, 2]} size={[2.2, 3.5, 2.2]} neonColor="#06b6d4" />
        <Skyscraper position={[-2, 0.03, -2]} size={[2.0, 4.5, 2.0]} neonColor="#f59e0b" />
        <Skyscraper position={[-2, 0.03, 2]} size={[1.8, 2.6, 1.8]} neonColor="#d946ef" />
      </group>

      {/* ── Pocket 6: North Block [0, -20] ── */}
      <group position={[0, 0.03, -20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <Skyscraper position={[-2.5, 0.03, 0]} size={[2.2, 3.8, 2.2]} neonColor="#10b981" />
        <Skyscraper position={[2.5, 0.03, 0]} size={[2.0, 2.8, 2.0]} neonColor="#d946ef" />
      </group>

      {/* ── Pocket 7: South Block [0, 20] ── */}
      <group position={[0, 0.03, 20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <Skyscraper position={[2.5, 0.03, 0]} size={[2.2, 3.8, 2.2]} neonColor="#10b981" />
        <Skyscraper position={[-2.5, 0.03, 0]} size={[2.0, 2.8, 2.0]} neonColor="#06b6d4" />
      </group>

      {/* ── Pocket 8: West Block [-20, 0] ── */}
      <group position={[-20, 0.03, 0]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <Skyscraper position={[0, 0.03, -2.5]} size={[2.4, 4.2, 2.4]} neonColor="#f59e0b" />
        <Skyscraper position={[0, 0.03, 2.5]} size={[1.8, 2.8, 1.8]} neonColor="#10b981" />
      </group>

      {/* ── Pocket 9: East Block [20, 0] ── */}
      <group position={[20, 0.03, 0]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <Skyscraper position={[0, 0.03, 2.5]} size={[2.4, 4.2, 2.4]} neonColor="#f59e0b" />
        <Skyscraper position={[0, 0.03, -2.5]} size={[1.8, 2.8, 1.8]} neonColor="#06b6d4" />
      </group>
    </group>
  );
}
