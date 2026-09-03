"use client";

import React, { useMemo } from "react";
import {
  BoxGeometry,
  CylinderGeometry,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  PlaneGeometry,
} from "three";
import { Tree, Hedge } from "@/components/simulation/city/Tree";
import {
  Streetlight,
  ParkBench,
  FireHydrant,
  PlanterBox,
  Bollard,
} from "@/components/simulation/city/UrbanProps";
import {
  GlassTower,
  SteppedTower,
  MidRiseBlock,
  PlazaTower,
} from "@/components/simulation/city/BuildingModels";

export default React.memo(function CityGrid() {
  // Underlying dark bedrock ground plane (covers 60x60 city boundary)
  const groundGeo = useMemo(() => new PlaneGeometry(60, 60), []);
  const groundMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#080c14",
        roughness: 0.9,
        metalness: 0.1,
      }),
    []
  );

  // Standard 14x14 block concrete sidewalk base
  const curbGeo = useMemo(() => new BoxGeometry(14.0, 0.08, 14.0), []);
  const curbMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#334155", // polished urban sidewalk slate
        roughness: 0.65,
        metalness: 0.2,
      }),
    []
  );

  // Stone paver top inlay
  const paverGeo = useMemo(() => new BoxGeometry(13.8, 0.02, 13.8), []);
  const paverMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#475569", // stone paver tone
        roughness: 0.7,
        metalness: 0.1,
      }),
    []
  );

  // Reusable promenade path geometries
  const pathLongGeo = useMemo(() => new BoxGeometry(13.4, 0.035, 1.6), []);
  const pathCrossGeo = useMemo(() => new BoxGeometry(1.6, 0.035, 13.4), []);
  const pathDiagGeo = useMemo(() => new BoxGeometry(12.0, 0.035, 1.4), []);

  // Central park lawn plate (13.4 x 13.4)
  const parkLawnGeo = useMemo(() => new BoxGeometry(13.4, 0.035, 13.4), []);
  const parkLawnMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#166534",
        roughness: 0.9,
        metalness: 0.05,
        emissive: "#052e16",
        emissiveIntensity: 0.1,
      }),
    []
  );

  // Central Civic Fountain Basin & Water
  const fountainBasinGeo = useMemo(() => new CylinderGeometry(1.6, 1.7, 0.26, 16), []);
  const fountainWaterGeo = useMemo(() => new CylinderGeometry(1.48, 1.48, 0.22, 16), []);
  const fountainSpoutGeo = useMemo(() => new CylinderGeometry(0.3, 0.4, 0.6, 8), []);

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
      new MeshStandardMaterial({
        color: "#0284c7",
        roughness: 0.1,
        metalness: 0.2,
        emissive: "#0369a1",
        emissiveIntensity: 0.4,
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
          POCKET 1: CENTER CIVIC PARK & PLAZA [0, 0]
      ==================================================================== */}
      <group position={[0, 0.04, 0]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={parkLawnGeo} material={parkLawnMat} position={[0, 0.045, 0]} receiveShadow />

        {/* Diagonal and cross stone promenades */}
        <mesh geometry={pathLongGeo} material={paverMat} position={[0, 0.05, 0]} receiveShadow />
        <mesh geometry={pathCrossGeo} material={paverMat} position={[0, 0.05, 0]} receiveShadow />

        {/* Central Fountain */}
        <group position={[0, 0.05, 0]}>
          <mesh geometry={fountainBasinGeo} material={stoneBasinMat} position={[0, 0.13, 0]} castShadow receiveShadow />
          <mesh geometry={fountainWaterGeo} material={waterMat} position={[0, 0.14, 0]} receiveShadow />
          <mesh geometry={fountainSpoutGeo} material={stoneBasinMat} position={[0, 0.42, 0]} castShadow />
        </group>

        {/* Plaza Benches */}
        <ParkBench position={[-2.2, 0.05, 0]} rotationY={Math.PI / 2} />
        <ParkBench position={[2.2, 0.05, 0]} rotationY={-Math.PI / 2} />
        <ParkBench position={[0, 0.05, -2.2]} rotationY={0} />
        <ParkBench position={[0, 0.05, 2.2]} rotationY={Math.PI} />

        {/* Trees in Lawn Quadrants */}
        <Tree position={[-4.2, 0.05, -4.2]} scale={1.2} variant="lush" rotationY={0.5} />
        <Tree position={[4.2, 0.05, -4.2]} scale={1.15} variant="blossom" rotationY={-0.8} />
        <Tree position={[-4.2, 0.05, 4.2]} scale={1.1} variant="autumn" rotationY={1.4} />
        <Tree position={[4.2, 0.05, 4.2]} scale={1.25} variant="lush" rotationY={-1.8} />

        {/* Corner Streetlights */}
        <Streetlight position={[-5.8, 0.05, -5.8]} rotationY={Math.PI / 4} />
        <Streetlight position={[5.8, 0.05, 5.8]} rotationY={-3 * Math.PI / 4} />
      </group>

      {/* ===================================================================
          POCKET 2: NORTH-WEST BOTANICAL PARK [-20, -20]
      ==================================================================== */}
      <group position={[-20, 0.04, -20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={parkLawnGeo} material={parkLawnMat} position={[0, 0.045, 0]} receiveShadow />

        {/* Curved / diagonal walking paths */}
        <mesh
          geometry={pathDiagGeo}
          material={paverMat}
          position={[0, 0.05, 0]}
          rotation={[0, Math.PI / 4, 0]}
          receiveShadow
        />

        {/* Grove of diverse trees */}
        <Tree position={[-3.5, 0.05, -3.5]} scale={1.3} variant="lush" rotationY={0.6} />
        <Tree position={[3.5, 0.05, 3.5]} scale={1.2} variant="blossom" rotationY={-1.2} />
        <Tree position={[-3.8, 0.05, 3.2]} scale={1.0} variant="pine" rotationY={0.9} />
        <Tree position={[3.2, 0.05, -3.8]} scale={1.15} variant="autumn" rotationY={2.0} />
        <Tree position={[0, 0.05, 4.2]} scale={0.95} variant="blossom" rotationY={-0.4} />

        <ParkBench position={[1.5, 0.05, -1.5]} rotationY={-Math.PI / 4} />
        <ParkBench position={[-1.5, 0.05, 1.5]} rotationY={3 * Math.PI / 4} />
        <Streetlight position={[5.8, 0.05, 5.8]} rotationY={-3 * Math.PI / 4} />
      </group>

      {/* ===================================================================
          POCKET 3: SOUTH-EAST WATERFRONT PARK [20, 20]
      ==================================================================== */}
      <group position={[20, 0.04, 20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={parkLawnGeo} material={parkLawnMat} position={[0, 0.045, 0]} receiveShadow />

        {/* Paved path */}
        <mesh
          geometry={pathDiagGeo}
          material={paverMat}
          position={[0, 0.05, 0]}
          rotation={[0, -Math.PI / 4, 0]}
          receiveShadow
        />

        {/* Grove of trees */}
        <Tree position={[-3.5, 0.05, -3.5]} scale={1.2} variant="blossom" rotationY={1.1} />
        <Tree position={[3.5, 0.05, 3.5]} scale={1.3} variant="lush" rotationY={-0.5} />
        <Tree position={[-3.2, 0.05, 3.8]} scale={1.1} variant="autumn" rotationY={0.7} />
        <Tree position={[3.8, 0.05, -3.2]} scale={1.0} variant="pine" rotationY={-1.5} />
        <Tree position={[4.2, 0.05, 0]} scale={1.05} variant="lush" rotationY={0.2} />

        <ParkBench position={[-1.5, 0.05, -1.5]} rotationY={Math.PI / 4} />
        <ParkBench position={[1.5, 0.05, 1.5]} rotationY={-3 * Math.PI / 4} />
        <Streetlight position={[-5.8, 0.05, -5.8]} rotationY={Math.PI / 4} />
      </group>

      {/* ===================================================================
          POCKET 4: NORTH-EAST FINANCIAL TOWER DISTRICT [20, -20]
      ==================================================================== */}
      <group position={[20, 0.04, -20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={paverGeo} material={paverMat} position={[0, 0.045, 0]} receiveShadow />

        {/* Soaring Glass Corporate Tower */}
        <GlassTower position={[-2.4, 0.04, -2.4]} size={[3.6, 8.2, 3.6]} accentColor="#38bdf8" />
        {/* Plaza Tech Center */}
        <PlazaTower position={[2.6, 0.04, 2.6]} size={[3.0, 6.4, 2.8]} neonColor="#f59e0b" />
        {/* Mid-Rise Retail */}
        <MidRiseBlock position={[2.6, 0.04, -2.6]} size={[3.2, 4.0, 2.8]} rotationY={Math.PI / 2} />

        {/* Street furniture & landscaping */}
        <Tree position={[-2.8, 0.04, 3.2]} scale={1.1} variant="lush" rotationY={0.4} />
        <PlanterBox position={[-2.4, 0.04, 0.8]} size={[1.4, 0.4, 0.45]} />
        <Streetlight position={[-5.8, 0.04, 0]} rotationY={-Math.PI / 2} />
        <Streetlight position={[0, 0.04, 5.8]} rotationY={Math.PI} />
        <FireHydrant position={[-5.8, 0.04, 5.8]} rotationY={Math.PI / 4} />
        <Bollard position={[-5.2, 0.04, 6.0]} />
        <Bollard position={[-6.0, 0.04, 5.2]} />
      </group>

      {/* ===================================================================
          POCKET 5: SOUTH-WEST TECH INNOVATION CAMPUS [-20, 20]
      ==================================================================== */}
      <group position={[-20, 0.04, 20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={paverGeo} material={paverMat} position={[0, 0.045, 0]} receiveShadow />

        {/* Stepped Modernist High-Rise */}
        <SteppedTower position={[2.6, 0.04, 2.6]} rotationY={-Math.PI / 2} />
        {/* Contemporary Plaza Tower */}
        <PlazaTower position={[-2.6, 0.04, -2.6]} size={[3.0, 6.8, 2.8]} neonColor="#10b981" />
        {/* Retail MidRise Block */}
        <MidRiseBlock position={[-2.6, 0.04, 2.6]} size={[3.2, 4.2, 2.8]} rotationY={0} />

        {/* Street furniture & landscaping */}
        <Tree position={[2.8, 0.04, -3.2]} scale={1.1} variant="autumn" rotationY={1.2} />
        <PlanterBox position={[0.8, 0.04, 2.6]} size={[1.4, 0.4, 0.45]} rotationY={Math.PI / 2} />
        <Streetlight position={[5.8, 0.04, 0]} rotationY={Math.PI / 2} />
        <Streetlight position={[0, 0.04, -5.8]} rotationY={0} />
        <FireHydrant position={[5.8, 0.04, -5.8]} rotationY={-3 * Math.PI / 4} />
        <Bollard position={[5.2, 0.04, -6.0]} />
        <Bollard position={[6.0, 0.04, -5.2]} />
      </group>

      {/* ===================================================================
          POCKET 6: NORTH CORPORATE BLOCK [0, -20]
      ==================================================================== */}
      <group position={[0, 0.04, -20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={paverGeo} material={paverMat} position={[0, 0.045, 0]} receiveShadow />

        {/* Modern Glass Skyscraper */}
        <GlassTower position={[-2.6, 0.04, 0]} size={[3.4, 7.5, 3.4]} accentColor="#10b981" />
        {/* Commercial MidRise Block */}
        <MidRiseBlock position={[2.6, 0.04, 0]} size={[3.2, 4.4, 3.0]} rotationY={Math.PI} />

        {/* Street trees & lights */}
        <Tree position={[0, 0.04, 3.8]} scale={1.15} variant="lush" rotationY={-0.7} />
        <Tree position={[0, 0.04, -3.8]} scale={1.05} variant="blossom" rotationY={0.9} />
        <Streetlight position={[0, 0.04, 5.8]} rotationY={Math.PI} />
        <ParkBench position={[0, 0.04, 1.8]} rotationY={0} />
      </group>

      {/* ===================================================================
          POCKET 7: SOUTH MIXED-USE RESIDENTIAL BLOCK [0, 20]
      ==================================================================== */}
      <group position={[0, 0.04, 20]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={paverGeo} material={paverMat} position={[0, 0.045, 0]} receiveShadow />

        {/* Stepped Mixed-Use Tower */}
        <SteppedTower position={[2.6, 0.04, 0]} rotationY={Math.PI / 4} />
        {/* Plaza Center */}
        <PlazaTower position={[-2.6, 0.04, 0]} size={[3.0, 5.6, 2.8]} neonColor="#06b6d4" />

        {/* Street trees & lights */}
        <Tree position={[0, 0.04, -3.8]} scale={1.1} variant="lush" rotationY={0.8} />
        <Tree position={[0, 0.04, 3.8]} scale={1.0} variant="autumn" rotationY={-1.1} />
        <Streetlight position={[0, 0.04, -5.8]} rotationY={0} />
        <ParkBench position={[0, 0.04, -1.8]} rotationY={Math.PI} />
      </group>

      {/* ===================================================================
          POCKET 8: WEST COMMERCIAL DISTRICT [-20, 0]
      ==================================================================== */}
      <group position={[-20, 0.04, 0]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={paverGeo} material={paverMat} position={[0, 0.045, 0]} receiveShadow />

        {/* Contemporary Plaza Tower */}
        <PlazaTower position={[0, 0.04, -2.6]} size={[3.2, 7.0, 3.0]} neonColor="#f59e0b" />
        {/* MidRise Retail Block */}
        <MidRiseBlock position={[0, 0.04, 2.6]} size={[3.2, 4.0, 2.8]} rotationY={Math.PI / 2} />

        {/* Street trees & lights */}
        <Tree position={[3.8, 0.04, 0]} scale={1.15} variant="lush" rotationY={1.3} />
        <Tree position={[-3.8, 0.04, 0]} scale={1.05} variant="blossom" rotationY={-0.6} />
        <Streetlight position={[5.8, 0.04, 0]} rotationY={Math.PI / 2} />
        <ParkBench position={[1.8, 0.04, 0]} rotationY={Math.PI / 2} />
      </group>

      {/* ===================================================================
          POCKET 9: EAST METROPOLITAN BLOCK [20, 0]
      ==================================================================== */}
      <group position={[20, 0.04, 0]}>
        <mesh geometry={curbGeo} material={curbMat} castShadow receiveShadow />
        <mesh geometry={paverGeo} material={paverMat} position={[0, 0.045, 0]} receiveShadow />

        {/* Corporate Glass Tower */}
        <GlassTower position={[0, 0.04, 2.6]} size={[3.4, 7.2, 3.4]} accentColor="#d946ef" />
        {/* Plaza Tower */}
        <PlazaTower position={[0, 0.04, -2.6]} size={[2.8, 5.5, 2.8]} neonColor="#06b6d4" />

        {/* Street trees & lights */}
        <Tree position={[-3.8, 0.04, 0]} scale={1.2} variant="lush" rotationY={-0.9} />
        <Tree position={[3.8, 0.04, 0]} scale={1.0} variant="autumn" rotationY={1.5} />
        <Streetlight position={[-5.8, 0.04, 0]} rotationY={-Math.PI / 2} />
        <ParkBench position={[-1.8, 0.04, 0]} rotationY={-Math.PI / 2} />
      </group>
    </group>
  );
});
