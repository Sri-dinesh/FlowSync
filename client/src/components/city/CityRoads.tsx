"use client";

import React, { useEffect, useMemo } from "react";
import { BoxGeometry, CylinderGeometry, MeshStandardMaterial, PlaneGeometry, SphereGeometry } from "three";

interface BoundaryGantryProps {
  position: [number, number, number];
  rotation: [number, number, number];
}

function BoundaryGantry({ position, rotation }: BoundaryGantryProps) {
  return (
    <group position={position} rotation={rotation}>
      {/* Left Steel Pylon */}
      <mesh position={[-3.15, 1.6, 0]}>
        <cylinderGeometry args={[0.08, 0.10, 3.2, 8]} />
        <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.3} />
      </mesh>
      {/* Right Steel Pylon */}
      <mesh position={[3.15, 1.6, 0]}>
        <cylinderGeometry args={[0.08, 0.10, 3.2, 8]} />
        <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.3} />
      </mesh>
      {/* Overhead Steel Truss Crossbar */}
      <mesh position={[0, 3.2, 0]}>
        <boxGeometry args={[6.5, 0.20, 0.25]} />
        <meshStandardMaterial color="#334155" metalness={0.85} roughness={0.25} />
      </mesh>
      {/* Electronic Overhead Sign Plate */}
      <mesh position={[0, 2.75, 0]}>
        <boxGeometry args={[4.2, 0.65, 0.12]} />
        <meshStandardMaterial color="#0a0f1d" metalness={0.7} roughness={0.3} />
      </mesh>
      {/* Glowing HUD Electronic Display Panel */}
      <mesh position={[0, 2.75, 0.07]}>
        <planeGeometry args={[4.0, 0.50]} />
        <meshStandardMaterial
          color="#06b6d4"
          emissive="#06b6d4"
          emissiveIntensity={1.5}
          toneMapped={false}
        />
      </mesh>
      {/* Amber Clearance Beacons */}
      <mesh position={[-1.8, 3.35, 0]}>
        <sphereGeometry args={[0.06, 6, 6]} />
        <meshStandardMaterial color="#f59e0b" emissive="#f59e0b" emissiveIntensity={3.0} toneMapped={false} />
      </mesh>
      <mesh position={[1.8, 3.35, 0]}>
        <sphereGeometry args={[0.06, 6, 6]} />
        <meshStandardMaterial color="#f59e0b" emissive="#f59e0b" emissiveIntensity={3.0} toneMapped={false} />
      </mesh>
    </group>
  );
}

function CityRoadsComponent() {
  const roadWidth = 6.0;
  // Exact 54.0 road length matching the 3x3 city block footprint (-27 to +27) flush with zero overflow
  const roadLength = 54.0;

  // Geometries
  const roadLongGeo = useMemo(() => new BoxGeometry(roadLength, 0.02, roadWidth), [roadLength]);
  const roadVertGeo = useMemo(() => new BoxGeometry(roadWidth, 0.02, roadLength), [roadLength]);

  const baseMaterial = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#242d3d", // asphalt dark charcoal
        roughness: 0.85,
        metalness: 0.15,
      }),
    []
  );

  // Outer Concrete Shoulder Curbs (framing road stubs flush from 13 to 27)
  const curbStubGeo = useMemo(() => new BoxGeometry(14.0, 0.08, 0.3), []);
  const curbVertStubGeo = useMemo(() => new BoxGeometry(0.3, 0.08, 14.0), []);
  const curbMat = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#334155",
        roughness: 0.6,
        metalness: 0.2,
      }),
    []
  );

  // Yellow markings: 14m outer stubs (-27 to -13 and 13 to 27), 14m middle segment (-7 to 7)
  const doubleYellowStubGeo = useMemo(() => new PlaneGeometry(14, 0.02), []);
  const doubleYellowVertStubGeo = useMemo(() => new PlaneGeometry(0.02, 14), []);

  const yellowMaterial = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#facc15",
        roughness: 0.7,
        emissive: "#facc15",
        emissiveIntensity: 0.4,
      }),
    []
  );

  // White Fog / Shoulder Edge Lines (spanning full 54m road length flush with boundary)
  const whiteEdgeHorizGeo = useMemo(() => new PlaneGeometry(roadLength, 0.06), [roadLength]);
  const whiteEdgeVertGeo = useMemo(() => new PlaneGeometry(0.06, roadLength), [roadLength]);

  const stopBarHorizGeo = useMemo(() => new PlaneGeometry(0.14, roadWidth), []);
  const stopBarVertGeo = useMemo(() => new PlaneGeometry(roadWidth, 0.14), []);

  const whitePaintMaterial = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#f8fafc",
        roughness: 0.7,
        opacity: 0.92,
        transparent: true,
        emissive: "#f8fafc",
        emissiveIntensity: 0.25,
      }),
    []
  );

  useEffect(() => {
    return () => {
      roadLongGeo.dispose();
      roadVertGeo.dispose();
      baseMaterial.dispose();
      curbStubGeo.dispose();
      curbVertStubGeo.dispose();
      curbMat.dispose();
      doubleYellowStubGeo.dispose();
      doubleYellowVertStubGeo.dispose();
      yellowMaterial.dispose();
      whiteEdgeHorizGeo.dispose();
      whiteEdgeVertGeo.dispose();
      stopBarHorizGeo.dispose();
      stopBarVertGeo.dispose();
      whitePaintMaterial.dispose();
    };
  }, [
    roadLongGeo, roadVertGeo, baseMaterial, curbStubGeo, curbVertStubGeo, curbMat,
    doubleYellowStubGeo, doubleYellowVertStubGeo, yellowMaterial, whiteEdgeHorizGeo,
    whiteEdgeVertGeo, stopBarHorizGeo, stopBarVertGeo, whitePaintMaterial,
  ]);

  const rotation = [-Math.PI / 2, 0, 0] as const;

  return (
    <group>
      {/* ── Continuous Asphalt Bases (Flush with City Blocks from -27 to +27) ── */}
      <mesh geometry={roadLongGeo} material={baseMaterial} position={[0, 0.01, -10]} receiveShadow />
      <mesh geometry={roadLongGeo} material={baseMaterial} position={[0, 0.01, 10]} receiveShadow />
      <mesh geometry={roadVertGeo} material={baseMaterial} position={[-10, 0.01, 0]} receiveShadow />
      <mesh geometry={roadVertGeo} material={baseMaterial} position={[10, 0.01, 0]} receiveShadow />

      {/* ── Concrete Road Shoulder Curbs (Framing the 8 Perimeter Stubs from 13 to 27) ── */}
      {[-10, 10].map((z) => (
        <group key={`h-curbs-${z}`}>
          {/* West Stubs (-27 to -13) */}
          <mesh geometry={curbStubGeo} material={curbMat} position={[-20, 0.04, z - 3.15]} castShadow receiveShadow />
          <mesh geometry={curbStubGeo} material={curbMat} position={[-20, 0.04, z + 3.15]} castShadow receiveShadow />
          {/* East Stubs (13 to 27) */}
          <mesh geometry={curbStubGeo} material={curbMat} position={[20, 0.04, z - 3.15]} castShadow receiveShadow />
          <mesh geometry={curbStubGeo} material={curbMat} position={[20, 0.04, z + 3.15]} castShadow receiveShadow />
        </group>
      ))}

      {[-10, 10].map((x) => (
        <group key={`v-curbs-${x}`}>
          {/* North Stubs (-27 to -13) */}
          <mesh geometry={curbVertStubGeo} material={curbMat} position={[x - 3.15, 0.04, -20]} castShadow receiveShadow />
          <mesh geometry={curbVertStubGeo} material={curbMat} position={[x + 3.15, 0.04, -20]} castShadow receiveShadow />
          {/* South Stubs (13 to 27) */}
          <mesh geometry={curbVertStubGeo} material={curbMat} position={[x - 3.15, 0.04, 20]} castShadow receiveShadow />
          <mesh geometry={curbVertStubGeo} material={curbMat} position={[x + 3.15, 0.04, 20]} castShadow receiveShadow />
        </group>
      ))}

      {/* ── White Shoulder Fog Lines (Crisp Road Edges from -27 to +27) ── */}
      {[-10, 10].map((z) => (
        <group key={`h-fog-${z}`}>
          <mesh geometry={whiteEdgeHorizGeo} material={whitePaintMaterial} rotation={rotation} position={[0, 0.021, z - 2.85]} />
          <mesh geometry={whiteEdgeHorizGeo} material={whitePaintMaterial} rotation={rotation} position={[0, 0.021, z + 2.85]} />
        </group>
      ))}
      {[-10, 10].map((x) => (
        <group key={`v-fog-${x}`}>
          <mesh geometry={whiteEdgeVertGeo} material={whitePaintMaterial} rotation={rotation} position={[x - 2.85, 0.021, 0]} />
          <mesh geometry={whiteEdgeVertGeo} material={whitePaintMaterial} rotation={rotation} position={[x + 2.85, 0.021, 0]} />
        </group>
      ))}

      {/* ── Double Yellow Center Lines ── */}
      {[-10, 10].map((z) => (
        <group key={`h-yellow-${z}`} position={[0, 0.021, z]}>
          {/* West stubs (X: -27 to -13) */}
          <mesh geometry={doubleYellowStubGeo} material={yellowMaterial} rotation={rotation} position={[-20, 0, 0.03]} />
          <mesh geometry={doubleYellowStubGeo} material={yellowMaterial} rotation={rotation} position={[-20, 0, -0.03]} />
          {/* Middle segment (X: -7 to 7) */}
          <mesh geometry={doubleYellowStubGeo} material={yellowMaterial} rotation={rotation} position={[0, 0, 0.03]} />
          <mesh geometry={doubleYellowStubGeo} material={yellowMaterial} rotation={rotation} position={[0, 0, -0.03]} />
          {/* East stubs (X: 13 to 27) */}
          <mesh geometry={doubleYellowStubGeo} material={yellowMaterial} rotation={rotation} position={[20, 0, 0.03]} />
          <mesh geometry={doubleYellowStubGeo} material={yellowMaterial} rotation={rotation} position={[20, 0, -0.03]} />
        </group>
      ))}

      {[-10, 10].map((x) => (
        <group key={`v-yellow-${x}`} position={[x, 0.021, 0]}>
          {/* North stubs (Z: -27 to -13) */}
          <mesh geometry={doubleYellowVertStubGeo} material={yellowMaterial} rotation={rotation} position={[0.03, 0, -20]} />
          <mesh geometry={doubleYellowVertStubGeo} material={yellowMaterial} rotation={rotation} position={[-0.03, 0, -20]} />
          {/* Middle segment (Z: -7 to 7) */}
          <mesh geometry={doubleYellowVertStubGeo} material={yellowMaterial} rotation={rotation} position={[0.03, 0, 0]} />
          <mesh geometry={doubleYellowVertStubGeo} material={yellowMaterial} rotation={rotation} position={[-0.03, 0, 0]} />
          {/* South stubs (Z: 13 to 27) */}
          <mesh geometry={doubleYellowVertStubGeo} material={yellowMaterial} rotation={rotation} position={[0.03, 0, 20]} />
          <mesh geometry={doubleYellowVertStubGeo} material={yellowMaterial} rotation={rotation} position={[-0.03, 0, 20]} />
        </group>
      ))}

      {/* ── White Stop Bars ── */}
      {[-10, 10].map((z) => (
        <group key={`h-stops-${z}`}>
          <mesh geometry={stopBarHorizGeo} material={whitePaintMaterial} rotation={rotation} position={[-13.1, 0.021, z]} />
          <mesh geometry={stopBarHorizGeo} material={whitePaintMaterial} rotation={rotation} position={[-6.9, 0.021, z]} />
          <mesh geometry={stopBarHorizGeo} material={whitePaintMaterial} rotation={rotation} position={[6.9, 0.021, z]} />
          <mesh geometry={stopBarHorizGeo} material={whitePaintMaterial} rotation={rotation} position={[13.1, 0.021, z]} />
        </group>
      ))}

      {[-10, 10].map((x) => (
        <group key={`v-stops-${x}`}>
          <mesh geometry={stopBarVertGeo} material={whitePaintMaterial} rotation={rotation} position={[x, 0.021, -13.1]} />
          <mesh geometry={stopBarVertGeo} material={whitePaintMaterial} rotation={rotation} position={[x, 0.021, -6.9]} />
          <mesh geometry={stopBarVertGeo} material={whitePaintMaterial} rotation={rotation} position={[x, 0.021, 6.9]} />
          <mesh geometry={stopBarVertGeo} material={whitePaintMaterial} rotation={rotation} position={[x, 0.021, 13.1]} />
        </group>
      ))}

      {/* ── 8 Highway Boundary Gantries (Inside Road Corridors at +/- 25.5, Zero Overflow) ── */}
      {/* West Corridors */}
      <BoundaryGantry position={[-25.5, 0, -10]} rotation={[0, Math.PI / 2, 0]} />
      <BoundaryGantry position={[-25.5, 0, 10]} rotation={[0, Math.PI / 2, 0]} />

      {/* East Corridors */}
      <BoundaryGantry position={[25.5, 0, -10]} rotation={[0, -Math.PI / 2, 0]} />
      <BoundaryGantry position={[25.5, 0, 10]} rotation={[0, -Math.PI / 2, 0]} />

      {/* North Corridors */}
      <BoundaryGantry position={[-10, 0, -25.5]} rotation={[0, 0, 0]} />
      <BoundaryGantry position={[10, 0, -25.5]} rotation={[0, 0, 0]} />

      {/* South Corridors */}
      <BoundaryGantry position={[-10, 0, 25.5]} rotation={[0, Math.PI, 0]} />
      <BoundaryGantry position={[10, 0, 25.5]} rotation={[0, Math.PI, 0]} />
    </group>
  );
}

const CityRoads = React.memo(CityRoadsComponent);
export default CityRoads;
