"use client";

import { useEffect, useMemo } from "react";
import { Text } from "@react-three/drei";
import { BoxGeometry, MeshStandardMaterial, PlaneGeometry } from "three";

export default function CityRoads() {
  const roadWidth = 6.0;
  
  // Geometries
  const roadLongGeo = useMemo(() => new BoxGeometry(56, 0.02, roadWidth), []); // horizontal continuous
  const roadVertGeo = useMemo(() => new BoxGeometry(roadWidth, 0.02, 56), []); // vertical continuous

  const baseMaterial = useMemo(() => new MeshStandardMaterial({
    color: "#2d3748", // asphalt gray
    roughness: 0.8,
    metalness: 0.1,
  }), []);

  // Markings Geometries
  const doubleYellowLineGeo = useMemo(() => new PlaneGeometry(15, 0.02), []); // for straight sections
  const doubleYellowVertLineGeo = useMemo(() => new PlaneGeometry(0.02, 15), []);

  const yellowMaterial = useMemo(() => new MeshStandardMaterial({
    color: "#facc15",
    roughness: 0.7,
    emissive: "#facc15",
    emissiveIntensity: 0.3,
  }), []);

  const stopBarHorizGeo = useMemo(() => new PlaneGeometry(0.12, roadWidth), []);
  const stopBarVertGeo = useMemo(() => new PlaneGeometry(roadWidth, 0.12), []);

  const whitePaintMaterial = useMemo(() => new MeshStandardMaterial({
    color: "#f8fafc",
    roughness: 0.7,
    opacity: 0.9,
    transparent: true,
    emissive: "#f8fafc",
    emissiveIntensity: 0.2,
  }), []);

  useEffect(() => {
    return () => {
      roadLongGeo.dispose();
      roadVertGeo.dispose();
      baseMaterial.dispose();
      doubleYellowLineGeo.dispose();
      doubleYellowVertLineGeo.dispose();
      yellowMaterial.dispose();
      stopBarHorizGeo.dispose();
      stopBarVertGeo.dispose();
      whitePaintMaterial.dispose();
    };
  }, [
    roadLongGeo, roadVertGeo, baseMaterial, doubleYellowLineGeo, doubleYellowVertLineGeo,
    yellowMaterial, stopBarHorizGeo, stopBarVertGeo, whitePaintMaterial
  ]);

  const rotation = [-Math.PI / 2, 0, 0] as const;

  return (
    <group>
      {/* ── Asphalt Bases ── */}
      {/* Horizontal roads */}
      <mesh geometry={roadLongGeo} material={baseMaterial} position={[0, 0.01, -10]} receiveShadow />
      <mesh geometry={roadLongGeo} material={baseMaterial} position={[0, 0.01, 10]} receiveShadow />
      {/* Vertical roads */}
      <mesh geometry={roadVertGeo} material={baseMaterial} position={[-10, 0.01, 0]} receiveShadow />
      <mesh geometry={roadVertGeo} material={baseMaterial} position={[10, 0.01, 0]} receiveShadow />

      {/* ── Double Yellow Center Lines ── */}
      {/* Horizontal lines (along Z = -10 and Z = 10) */}
      {[-10, 10].map((z) => (
        <group key={`h-yellow-${z}`} position={[0, 0.021, z]}>
          {/* West stubs (X: -28 to -13) */}
          <mesh geometry={doubleYellowLineGeo} material={yellowMaterial} rotation={rotation} position={[-20.5, 0, 0.03]} />
          <mesh geometry={doubleYellowLineGeo} material={yellowMaterial} rotation={rotation} position={[-20.5, 0, -0.03]} />
          {/* Middle segment (X: -7 to 7) */}
          <mesh geometry={doubleYellowLineGeo} material={yellowMaterial} rotation={rotation} position={[0, 0, 0.03]} />
          <mesh geometry={doubleYellowLineGeo} material={yellowMaterial} rotation={rotation} position={[0, 0, -0.03]} />
          {/* East stubs (X: 13 to 28) */}
          <mesh geometry={doubleYellowLineGeo} material={yellowMaterial} rotation={rotation} position={[20.5, 0, 0.03]} />
          <mesh geometry={doubleYellowLineGeo} material={yellowMaterial} rotation={rotation} position={[20.5, 0, -0.03]} />
        </group>
      ))}

      {/* Vertical lines (along X = -10 and X = 10) */}
      {[-10, 10].map((x) => (
        <group key={`v-yellow-${x}`} position={[x, 0.021, 0]}>
          {/* North stubs (Z: -28 to -13) */}
          <mesh geometry={doubleYellowVertLineGeo} material={yellowMaterial} rotation={rotation} position={[0.03, 0, -20.5]} />
          <mesh geometry={doubleYellowVertLineGeo} material={yellowMaterial} rotation={rotation} position={[-0.03, 0, -20.5]} />
          {/* Middle segment (Z: -7 to 7) */}
          <mesh geometry={doubleYellowVertLineGeo} material={yellowMaterial} rotation={rotation} position={[0.03, 0, 0]} />
          <mesh geometry={doubleYellowVertLineGeo} material={yellowMaterial} rotation={rotation} position={[-0.03, 0, 0]} />
          {/* South stubs (Z: 13 to 28) */}
          <mesh geometry={doubleYellowVertLineGeo} material={yellowMaterial} rotation={rotation} position={[0.03, 0, 20.5]} />
          <mesh geometry={doubleYellowVertLineGeo} material={yellowMaterial} rotation={rotation} position={[-0.03, 0, 20.5]} />
        </group>
      ))}

      {/* ── White Stop Bars ── */}
      {/* Horizontal road stop bars (at approaches to X = -10 and X = 10) */}
      {[-10, 10].map((z) => (
        <group key={`h-stops-${z}`}>
          {/* Intersect A/C: stop lines at X = -13.1 and X = -6.9 */}
          <mesh geometry={stopBarHorizGeo} material={whitePaintMaterial} rotation={rotation} position={[-13.1, 0.021, z]} />
          <mesh geometry={stopBarHorizGeo} material={whitePaintMaterial} rotation={rotation} position={[-6.9, 0.021, z]} />
          {/* Intersect B/D: stop lines at X = 6.9 and X = 13.1 */}
          <mesh geometry={stopBarHorizGeo} material={whitePaintMaterial} rotation={rotation} position={[6.9, 0.021, z]} />
          <mesh geometry={stopBarHorizGeo} material={whitePaintMaterial} rotation={rotation} position={[13.1, 0.021, z]} />
        </group>
      ))}

      {/* Vertical road stop bars (at approaches to Z = -10 and Z = 10) */}
      {[-10, 10].map((x) => (
        <group key={`v-stops-${x}`}>
          {/* Intersect A/B: stop lines at Z = -13.1 and Z = -6.9 */}
          <mesh geometry={stopBarVertGeo} material={whitePaintMaterial} rotation={rotation} position={[x, 0.021, -13.1]} />
          <mesh geometry={stopBarVertGeo} material={whitePaintMaterial} rotation={rotation} position={[x, 0.021, -6.9]} />
          {/* Intersect C/D: stop lines at Z = 6.9 and Z = 13.1 */}
          <mesh geometry={stopBarVertGeo} material={whitePaintMaterial} rotation={rotation} position={[x, 0.021, 6.9]} />
          <mesh geometry={stopBarVertGeo} material={whitePaintMaterial} rotation={rotation} position={[x, 0.021, 13.1]} />
        </group>
      ))}

      {/* ── Decorative Road Label Text (Flat) ── */}
      {/* Eastbound / Westbound label flat markings */}
      <Text position={[-20, 0.022, -8.5]} rotation={[-Math.PI / 2, 0, Math.PI / 2]} fontSize={0.25} color="#ffffff" fillOpacity={0.3}>
        EASTBOUND ▶
      </Text>
      <Text position={[-20, 0.022, -11.5]} rotation={[-Math.PI / 2, 0, -Math.PI / 2]} fontSize={0.25} color="#ffffff" fillOpacity={0.3}>
        ◀ WESTBOUND
      </Text>
      <Text position={[20, 0.022, 11.5]} rotation={[-Math.PI / 2, 0, Math.PI / 2]} fontSize={0.25} color="#ffffff" fillOpacity={0.3}>
        EASTBOUND ▶
      </Text>
      <Text position={[20, 0.022, 8.5]} rotation={[-Math.PI / 2, 0, -Math.PI / 2]} fontSize={0.25} color="#ffffff" fillOpacity={0.3}>
        ◀ WESTBOUND
      </Text>

      {/* Southbound / Northbound label flat markings */}
      <Text position={[-11.5, 0.022, -20]} rotation={[-Math.PI / 2, 0, Math.PI]} fontSize={0.25} color="#ffffff" fillOpacity={0.3}>
        ▼ SOUTHBOUND
      </Text>
      <Text position={[-8.5, 0.022, -20]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.25} color="#ffffff" fillOpacity={0.3}>
        ▲ NORTHBOUND
      </Text>
      <Text position={[8.5, 0.022, 20]} rotation={[-Math.PI / 2, 0, Math.PI]} fontSize={0.25} color="#ffffff" fillOpacity={0.3}>
        ▼ SOUTHBOUND
      </Text>
      <Text position={[11.5, 0.022, 20]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.25} color="#ffffff" fillOpacity={0.3}>
        ▲ NORTHBOUND
      </Text>
    </group>
  );
}
