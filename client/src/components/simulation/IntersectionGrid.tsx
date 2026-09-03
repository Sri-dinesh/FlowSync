"use client";

import { useMemo } from "react";
import { BoxGeometry, MeshPhysicalMaterial, MeshStandardMaterial, PlaneGeometry } from "three";
import { Tree, Hedge } from "./city/Tree";
import { Streetlight, ParkBench, FireHydrant, PlanterBox, Bollard } from "./city/UrbanProps";
import { GlassTower, SteppedTower, MidRiseBlock, PlazaTower } from "./city/BuildingModels";
import { CityPark } from "./city/CityPark";

export default function IntersectionGrid() {
  // Underlying asphalt/bedrock ground plate
  const groundGeo = useMemo(() => new PlaneGeometry(50, 50), []);
  const groundMat = useMemo(
    () =>
      new MeshPhysicalMaterial({
        color: "#080c14",
        roughness: 0.85,
        metalness: 0.2,
        clearcoat: 0.1,
        clearcoatRoughness: 0.9,
      }),
    []
  );

  // Concrete sidewalk curb platform (16 x 0.08 x 16 units)
  const curbGeo = useMemo(() => new BoxGeometry(16.0, 0.08, 16.0), []);
  const curbMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#334155", // polished urban sidewalk slate
        roughness: 0.65,
        metalness: 0.2,
      }),
    []
  );

  // Paver tile inlay on sidewalk top
  const paverGeo = useMemo(() => new BoxGeometry(15.8, 0.02, 15.8), []);
  const paverMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#475569", // stone paver tone
        roughness: 0.7,
        metalness: 0.1,
      }),
    []
  );

  return (
    <group>
      {/* ── Base Ground Plane ── */}
      <mesh
        geometry={groundGeo}
        material={groundMat}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0, 0]}
        receiveShadow
      />

      {/* ===================================================================
          QUADRANT 1: NORTH-WEST (Financial & Corporate District)
          Center: [-11.5, 0.04, -11.5]
      ==================================================================== */}
      <group position={[-11.5, 0.04, -11.5]}>
        {/* Concrete sidewalk platform & Paver top */}
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={paverGeo} material={paverMat} position={[0, 0.045, 0]} receiveShadow />

        {/* ── Main Glass Corporate Skyscraper ── */}
        <GlassTower position={[-2.4, 0.04, -2.4]} size={[3.8, 8.6, 3.8]} accentColor="#38bdf8" />

        {/* ── Adjacent Mid-Rise Commercial Office ── */}
        <MidRiseBlock position={[3.2, 0.04, -2.4]} size={[3.4, 4.4, 3.2]} rotationY={0} />

        {/* ── Contemporary Tech Lab ── */}
        <PlazaTower position={[-2.5, 0.04, 3.2]} size={[3.0, 5.8, 2.8]} neonColor="#06b6d4" />

        {/* ── Street-level greenery & amenities ── */}
        <Tree position={[3.5, 0.04, 3.5]} scale={1.15} variant="lush" rotationY={0.8} />
        <Tree position={[0.5, 0.04, 3.8]} scale={0.95} variant="blossom" rotationY={-0.5} />
        <Tree position={[3.8, 0.04, 0.8]} scale={1.0} variant="autumn" rotationY={1.4} />

        {/* Entrance Planters */}
        <PlanterBox position={[-2.4, 0.04, 1.2]} size={[1.4, 0.4, 0.45]} />
        <PlanterBox position={[1.0, 0.04, -2.4]} size={[1.4, 0.4, 0.45]} rotationY={Math.PI / 2} />

        {/* Streetlights along pedestrian curbs (illuminates corner at night) */}
        <Streetlight position={[7.1, 0.04, 0]} rotationY={Math.PI / 2} />
        <Streetlight position={[0, 0.04, 7.1]} rotationY={Math.PI} />

        {/* Corner Fire Hydrant & Bollards near crosswalk */}
        <FireHydrant position={[7.2, 0.04, 7.2]} rotationY={-Math.PI / 4} />
        <Bollard position={[6.5, 0.04, 7.4]} />
        <Bollard position={[7.4, 0.04, 6.5]} />
      </group>

      {/* ===================================================================
          QUADRANT 2: NORTH-EAST (Tech Innovation Plaza & High-Rise)
          Center: [11.5, 0.04, -11.5]
      ==================================================================== */}
      <group position={[11.5, 0.04, -11.5]}>
        {/* Concrete sidewalk platform & Paver top */}
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={paverGeo} material={paverMat} position={[0, 0.045, 0]} receiveShadow />

        {/* ── Modernist Stepped Tower ── */}
        <SteppedTower position={[2.6, 0.04, -2.6]} rotationY={-Math.PI / 4} />

        {/* ── Tech Innovation Plaza Tower ── */}
        <PlazaTower position={[-2.8, 0.04, -2.2]} size={[3.2, 7.2, 3.0]} neonColor="#f59e0b" />

        {/* ── Corner Commercial Retail ── */}
        <MidRiseBlock position={[2.4, 0.04, 3.0]} size={[3.6, 3.8, 3.0]} rotationY={Math.PI / 2} />

        {/* ── Landscaped Plaza Greenery ── */}
        <Tree position={[-3.5, 0.04, 3.5]} scale={1.2} variant="lush" rotationY={1.6} />
        <Tree position={[-1.0, 0.04, 3.8]} scale={0.9} variant="blossom" rotationY={-1.2} />
        <Tree position={[-3.8, 0.04, 1.0]} scale={1.05} variant="pine" rotationY={0.4} />

        {/* Park Bench for Plaza */}
        <ParkBench position={[-2.4, 0.04, 2.0]} rotationY={0} />

        {/* Streetlights along pedestrian curbs */}
        <Streetlight position={[-7.1, 0.04, 0]} rotationY={-Math.PI / 2} />
        <Streetlight position={[0, 0.04, 7.1]} rotationY={Math.PI} />

        {/* Corner Fire Hydrant & Bollards */}
        <FireHydrant position={[-7.2, 0.04, 7.2]} rotationY={Math.PI / 4} />
        <Bollard position={[-6.5, 0.04, 7.4]} />
        <Bollard position={[-7.4, 0.04, 6.5]} />
      </group>

      {/* ===================================================================
          QUADRANT 3: SOUTH-WEST (Urban Mixed-Use & Residential District)
          Center: [-11.5, 0.04, 11.5]
      ==================================================================== */}
      <group position={[-11.5, 0.04, 11.5]}>
        {/* Concrete sidewalk platform & Paver top */}
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={paverGeo} material={paverMat} position={[0, 0.045, 0]} receiveShadow />

        {/* ── Residential Stepped High-Rise ── */}
        <SteppedTower position={[-2.6, 0.04, 2.6]} rotationY={Math.PI / 2} />

        {/* ── Modern Glass Tower with Fuchsia Accents ── */}
        <GlassTower position={[3.0, 0.04, 2.4]} size={[3.4, 7.0, 3.4]} accentColor="#d946ef" />

        {/* ── Street Corner Retail Block with Awnings ── */}
        <MidRiseBlock position={[-2.4, 0.04, -2.8]} size={[3.4, 4.0, 3.0]} rotationY={Math.PI} />

        {/* ── Street Amenities & Landscape ── */}
        <Tree position={[3.5, 0.04, -3.5]} scale={1.1} variant="autumn" rotationY={-0.8} />
        <Tree position={[3.8, 0.04, -1.0]} scale={0.9} variant="lush" rotationY={1.1} />
        <Tree position={[1.0, 0.04, -3.8]} scale={1.05} variant="blossom" rotationY={0.3} />

        {/* Sidewalk Bench & Planters */}
        <ParkBench position={[2.0, 0.04, -2.4]} rotationY={Math.PI / 2} />
        <PlanterBox position={[-2.4, 0.04, -0.9]} size={[1.4, 0.4, 0.45]} />

        {/* Streetlights along pedestrian curbs */}
        <Streetlight position={[7.1, 0.04, 0]} rotationY={Math.PI / 2} />
        <Streetlight position={[0, 0.04, -7.1]} rotationY={0} />

        {/* Corner Fire Hydrant & Bollards */}
        <FireHydrant position={[7.2, 0.04, -7.2]} rotationY={-3 * Math.PI / 4} />
        <Bollard position={[6.5, 0.04, -7.4]} />
        <Bollard position={[7.4, 0.04, -6.5]} />
      </group>

      {/* ===================================================================
          QUADRANT 4: SOUTH-EAST (Grand Civic Park & Botanical Plaza)
          Center: [11.5, 0.04, 11.5]
      ==================================================================== */}
      <group position={[11.5, 0.04, 11.5]}>
        {/* Concrete sidewalk perimeter platform */}
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />

        {/* ── Complete Civic Park (Lawn, Fountain, Paths, Trees, Benches) ── */}
        <CityPark position={[0, 0.04, 0]} />

        {/* Streetlights along street edges */}
        <Streetlight position={[-7.1, 0.04, 0]} rotationY={-Math.PI / 2} />
        <Streetlight position={[0, 0.04, -7.1]} rotationY={0} />

        {/* Corner Hydrant & Bollards */}
        <FireHydrant position={[-7.2, 0.04, -7.2]} rotationY={3 * Math.PI / 4} />
        <Bollard position={[-6.5, 0.04, -7.4]} />
        <Bollard position={[-7.4, 0.04, -6.5]} />
      </group>
    </group>
  );
}

