"use client";

import { useMemo } from "react";
import {
  BoxGeometry,
  CylinderGeometry,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
} from "three";
import { Tree, Hedge } from "./Tree";
import { ParkBench, Streetlight } from "./UrbanProps";

export function CityPark({
  position,
}: {
  position: [number, number, number];
}) {
  // Base grass lawn plate
  const lawnGeo = useMemo(() => new BoxGeometry(14.8, 0.04, 14.8), []);
  const lawnMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#166534", // rich emerald lawn
        roughness: 0.9,
        metalness: 0.05,
        emissive: "#052e16",
        emissiveIntensity: 0.1,
      }),
    []
  );

  // Stone Promenade pathways
  const pathLongGeo  = useMemo(() => new BoxGeometry(14.8, 0.05, 1.8), []);
  const pathCrossGeo = useMemo(() => new BoxGeometry(1.8, 0.05, 14.8), []);
  const pathDiagonalGeo = useMemo(() => new BoxGeometry(9.0, 0.05, 1.6), []);

  const stonePathMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#475569", // smooth cobblestone / slate
        roughness: 0.7,
        metalness: 0.15,
      }),
    []
  );

  // Central Civic Fountain Basin & Reflective Water
  const basinGeo = useMemo(() => new CylinderGeometry(1.8, 1.9, 0.28, 16), []);
  const waterGeo = useMemo(() => new CylinderGeometry(1.65, 1.65, 0.24, 16), []);
  const spoutGeo = useMemo(() => new CylinderGeometry(0.35, 0.45, 0.65, 8), []);

  const stoneBasinMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#334155",
        roughness: 0.5,
        metalness: 0.2,
      }),
    []
  );

  const waterMat = useMemo(
    () =>
      new MeshPhysicalMaterial({
        color: "#0284c7",
        roughness: 0.05,
        metalness: 0.1,
        clearcoat: 1.0,
        clearcoatRoughness: 0.05,
        transmission: 0.6,
        ior: 1.333,
        emissive: "#0369a1",
        emissiveIntensity: 0.3,
      }),
    []
  );

  return (
    <group position={position}>
      {/* ── Grass Lawn Bed ── */}
      <mesh geometry={lawnGeo} material={lawnMat} position={[0, 0.02, 0]} receiveShadow />

      {/* ── Paved Stone Promenades ── */}
      <mesh geometry={pathLongGeo} material={stonePathMat} position={[0, 0.025, 0]} receiveShadow />
      <mesh geometry={pathCrossGeo} material={stonePathMat} position={[0, 0.025, 0]} receiveShadow />
      <mesh
        geometry={pathDiagonalGeo}
        material={stonePathMat}
        position={[0, 0.025, 0]}
        rotation={[0, Math.PI / 4, 0]}
        receiveShadow
      />

      {/* ── Central Civic Fountain ── */}
      <group position={[0, 0.025, 0]}>
        <mesh geometry={basinGeo} material={stoneBasinMat} position={[0, 0.14, 0]} castShadow receiveShadow />
        <mesh geometry={waterGeo} material={waterMat} position={[0, 0.15, 0]} receiveShadow />
        <mesh geometry={spoutGeo} material={stoneBasinMat} position={[0, 0.45, 0]} castShadow />
      </group>

      {/* ── Benches Surrounding Central Plaza ── */}
      <ParkBench position={[-2.4, 0.05, 0]} rotationY={Math.PI / 2} />
      <ParkBench position={[2.4, 0.05, 0]} rotationY={-Math.PI / 2} />
      <ParkBench position={[0, 0.05, -2.4]} rotationY={0} />
      <ParkBench position={[0, 0.05, 2.4]} rotationY={Math.PI} />

      {/* ── Garden Pedestrian Lamps ── */}
      <Streetlight position={[-3.6, 0.05, -3.6]} rotationY={Math.PI / 4} lightColor="#fed7aa" />
      <Streetlight position={[3.6, 0.05, 3.6]} rotationY={-3 * Math.PI / 4} lightColor="#fed7aa" />

      {/* ── Layered Tree Plantings (Diverse Species) ── */}
      {/* Northwest Lawn Pocket */}
      <Tree position={[-4.5, 0.04, -4.5]} scale={1.25} variant="lush" rotationY={0.5} />
      <Tree position={[-3.2, 0.04, -5.2]} scale={1.0} variant="blossom" rotationY={1.2} />
      <Tree position={[-5.5, 0.04, -2.8]} scale={0.9} variant="pine" rotationY={0.8} />

      {/* Northeast Lawn Pocket */}
      <Tree position={[4.5, 0.04, -4.5]} scale={1.2} variant="lush" rotationY={-0.4} />
      <Tree position={[5.2, 0.04, -3.0]} scale={0.95} variant="autumn" rotationY={2.1} />
      <Tree position={[3.2, 0.04, -5.5]} scale={1.05} variant="blossom" rotationY={-1.5} />

      {/* Southwest Lawn Pocket */}
      <Tree position={[-4.5, 0.04, 4.5]} scale={1.2} variant="lush" rotationY={1.8} />
      <Tree position={[-5.2, 0.04, 3.2]} scale={0.95} variant="autumn" rotationY={0.3} />
      <Tree position={[-3.0, 0.04, 5.2]} scale={1.1} variant="blossom" rotationY={-0.7} />

      {/* Southeast Lawn Pocket */}
      <Tree position={[4.5, 0.04, 4.5]} scale={1.3} variant="lush" rotationY={-2.1} />
      <Tree position={[3.2, 0.04, 5.2]} scale={1.0} variant="pine" rotationY={0.9} />
      <Tree position={[5.2, 0.04, 3.2]} scale={0.9} variant="blossom" rotationY={1.4} />

      {/* ── Manicured Perimeter Hedges ── */}
      <Hedge position={[-4.0, 0.04, -6.6]} size={[3.2, 0.35, 0.35]} />
      <Hedge position={[4.0, 0.04, -6.6]} size={[3.2, 0.35, 0.35]} />
      <Hedge position={[-4.0, 0.04, 6.6]} size={[3.2, 0.35, 0.35]} />
      <Hedge position={[4.0, 0.04, 6.6]} size={[3.2, 0.35, 0.35]} />
    </group>
  );
}
