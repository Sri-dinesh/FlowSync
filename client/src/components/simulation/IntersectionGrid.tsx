"use client";

import { useEffect, useMemo } from "react";
import { BoxGeometry, CylinderGeometry, MeshStandardMaterial, PlaneGeometry } from "three";

// Stylized Tree component to populate our parks
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
      {/* Trunk */}
      <mesh geometry={trunkGeo} material={trunkMat} position={[0, 0.35, 0]} castShadow />
      
      {/* Foliage (Low poly stacked boxes) */}
      <mesh geometry={foliageGeo1} material={foliageMat} position={[0, 0.75, 0]} castShadow receiveShadow />
      <mesh geometry={foliageGeo2} material={foliageMat} position={[0.08, 1.05, -0.05]} castShadow />
    </group>
  );
}

// Stylized Neon Skyscraper block
interface SkyscraperProps {
  position: [number, number, number];
  size: [number, number, number];
  neonColor: string;
}

function Skyscraper({ position, size, neonColor }: SkyscraperProps) {
  const [w, h, d] = size;
  const buildingGeo = useMemo(() => new BoxGeometry(w, h, d), [w, h, d]);
  const buildingMat = useMemo(() => new MeshStandardMaterial({ 
    color: "#18181b", 
    roughness: 0.2, 
    metalness: 0.8 
  }), []);

  // Glowing neon stripes running up the corners to simulate active windows/facade lights
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
      {/* Main Skyscraper body */}
      <mesh geometry={buildingGeo} material={buildingMat} position={[0, h / 2, 0]} castShadow receiveShadow />

      {/* Decorative vertical glowing lines at corners */}
      <mesh geometry={stripeGeo} material={stripeMat} position={[-w / 2 + 0.02, h / 2, -d / 2 + 0.02]} />
      <mesh geometry={stripeGeo} material={stripeMat} position={[w / 2 - 0.02, h / 2, -d / 2 + 0.02]} />
      <mesh geometry={stripeGeo} material={stripeMat} position={[-w / 2 + 0.02, h / 2, d / 2 - 0.02]} />
      <mesh geometry={stripeGeo} material={stripeMat} position={[w / 2 - 0.02, h / 2, d / 2 - 0.02]} />
    </group>
  );
}

export default function IntersectionGrid() {
  const groundGeo = useMemo(() => new PlaneGeometry(22, 22), []);
  const groundMat = useMemo(() => new MeshStandardMaterial({
    color: "#1a1f2e",
    roughness: 0.8,
    metalness: 0.2,
  }), []);

  // Sidewalk concrete curbs - lighter color
  const curbGeo = useMemo(() => new BoxGeometry(8.0, 0.06, 8.0), []);
  const curbMat = useMemo(() => new MeshStandardMaterial({
    color: "#52525b",
    roughness: 0.7,
    metalness: 0.1,
  }), []);

  // Park grass tiles - brighter green
  const parkGrassGeo = useMemo(() => new BoxGeometry(7.6, 0.02, 7.6), []);
  const parkGrassMat = useMemo(() => new MeshStandardMaterial({
    color: "#2d5016",
    roughness: 0.9,
    emissive: "#1a3a0f",
    emissiveIntensity: 0.3,
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

      {/* ================= CORNER 1: NORTH-WEST PARK ================= */}
      <group position={[-7.0, 0.03, -7.0]}>
        {/* Concrete sidewalk base */}
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        {/* Grass zone */}
        <mesh geometry={parkGrassGeo} material={parkGrassMat} position={[0, 0.04, 0]} receiveShadow />
        {/* Trees */}
        <LowPolyTree position={[-1.5, 0.04, -1.5]} />
        <LowPolyTree position={[1.5, 0.04, 1.5]} />
        <LowPolyTree position={[-2.0, 0.04, 2.0]} />
        <LowPolyTree position={[2.0, 0.04, -2.0]} />
      </group>

      {/* ================= CORNER 4: SOUTH-EAST PARK ================= */}
      <group position={[7.0, 0.03, 7.0]}>
        {/* Concrete sidewalk base */}
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        {/* Grass zone */}
        <mesh geometry={parkGrassGeo} material={parkGrassMat} position={[0, 0.04, 0]} receiveShadow />
        {/* Trees */}
        <LowPolyTree position={[-1.5, 0.04, -1.5]} />
        <LowPolyTree position={[1.5, 0.04, 1.5]} />
        <LowPolyTree position={[-2.2, 0.04, 2.2]} />
        <LowPolyTree position={[2.2, 0.04, -2.2]} />
      </group>

      {/* ================= CORNER 2: NORTH-EAST CITY BLOCK ================= */}
      <group position={[7.0, 0.03, -7.0]}>
        {/* Concrete sidewalk base */}
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        {/* Skyscrapers */}
        <Skyscraper position={[-1.5, 0.03, -1.5]} size={[2.2, 3.2, 2.2]} neonColor="#06b6d4" />
        <Skyscraper position={[1.8, 0.03, 1.8]} size={[2.0, 4.2, 2.0]} neonColor="#f59e0b" />
        <Skyscraper position={[1.8, 0.03, -1.8]} size={[1.8, 2.4, 1.8]} neonColor="#d946ef" />
      </group>

      {/* ================= CORNER 3: SOUTH-WEST CITY BLOCK ================= */}
      <group position={[-7.0, 0.03, 7.0]}>
        {/* Concrete sidewalk base */}
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        {/* Skyscrapers */}
        <Skyscraper position={[1.5, 0.03, 1.5]} size={[2.2, 3.2, 2.2]} neonColor="#06b6d4" />
        <Skyscraper position={[-1.8, 0.03, -1.8]} size={[2.0, 4.2, 2.0]} neonColor="#f59e0b" />
        <Skyscraper position={[-1.8, 0.03, 1.8]} size={[1.8, 2.4, 1.8]} neonColor="#d946ef" />
      </group>
    </group>
  );
}
