"use client";

import { useEffect, useMemo } from "react";
import { Text } from "@react-three/drei";
import { BoxGeometry, MeshStandardMaterial, PlaneGeometry } from "three";

interface RoadProps {
  direction: "horizontal" | "vertical";
}

export default function Road({ direction }: RoadProps) {
  // Road goes all the way across the grid (22 units)
  const roadLength = 22;
  const roadWidth = 3;

  const baseGeometry = useMemo(
    () =>
      new BoxGeometry(
        direction === "horizontal" ? roadLength : roadWidth,
        0.02,
        direction === "horizontal" ? roadWidth : roadLength,
      ),
    [direction],
  );

  const baseMaterial = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#2d3748", // Lighter asphalt grey
        roughness: 0.8,
        metalness: 0.1,
      }),
    [],
  );

  // Yellow double-center line geometry (split into two blocks, stopping at intersection)
  const yellowLineLength = 9.5;
  const yellowLineGeometry = useMemo(
    () =>
      new PlaneGeometry(
        direction === "horizontal" ? yellowLineLength : 0.02,
        direction === "horizontal" ? 0.02 : yellowLineLength,
      ),
    [direction],
  );

  const yellowLineMaterial = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#facc15",
        roughness: 0.7,
        emissive: "#facc15",
        emissiveIntensity: 0.3,
      }),
    [],
  );

  // White zebra stripes
  const zebraStripeGeo = useMemo(
    () =>
      new PlaneGeometry(
        direction === "horizontal" ? 0.12 : 0.6,
        direction === "horizontal" ? 0.6 : 0.12,
      ),
    [direction],
  );
  const whitePaintMaterial = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#f8fafc",
        roughness: 0.7,
        opacity: 0.9,
        transparent: true,
        emissive: "#f8fafc",
        emissiveIntensity: 0.2,
      }),
    [],
  );

  // Thick white stop bars
  const stopBarGeometry = useMemo(
    () =>
      new PlaneGeometry(
        direction === "horizontal" ? 0.12 : 1.5,
        direction === "horizontal" ? 1.5 : 0.12,
      ),
    [direction],
  );
  const stopBarMaterial = useMemo(
    () =>
      new MeshStandardMaterial({
        color: "#f8fafc",
        roughness: 0.7,
        opacity: 0.95,
        transparent: true,
        emissive: "#f8fafc",
        emissiveIntensity: 0.25,
      }),
    [],
  );

  useEffect(() => {
    return () => {
      baseGeometry.dispose();
      baseMaterial.dispose();
      yellowLineGeometry.dispose();
      yellowLineMaterial.dispose();
      zebraStripeGeo.dispose();
      whitePaintMaterial.dispose();
      stopBarGeometry.dispose();
      stopBarMaterial.dispose();
    };
  }, [
    baseGeometry,
    baseMaterial,
    yellowLineGeometry,
    yellowLineMaterial,
    zebraStripeGeo,
    whitePaintMaterial,
    stopBarGeometry,
    stopBarMaterial,
  ]);

  const rotation = [-Math.PI / 2, 0, 0] as const;

  // Render white zebra crossing stripes (spanning width of road, spacing = 0.35)
  const stripes = [-1.05, -0.7, -0.35, 0, 0.35, 0.7, 1.05];

  return (
    <group>
      {/* Main road asphalt base */}
      <mesh
        geometry={baseGeometry}
        material={baseMaterial}
        position={[0, 0.01, 0]}
        receiveShadow
      />

      {direction === "horizontal" ? (
        <>
          {/* Double Yellow Center Lines (Left side) */}
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[-6.25, 0.021, 0.03]}
          />
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[-6.25, 0.021, -0.03]}
          />

          {/* Double Yellow Center Lines (Right side) */}
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[6.25, 0.021, 0.03]}
          />
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[6.25, 0.021, -0.03]}
          />

          {/* West entrance: Stop line for Eastbound traffic (z > 0) */}
          <mesh
            geometry={stopBarGeometry}
            material={stopBarMaterial}
            rotation={rotation}
            position={[-1.6, 0.021, 0.75]}
          />

          {/* East entrance: Stop line for Westbound traffic (z < 0) */}
          <mesh
            geometry={stopBarGeometry}
            material={stopBarMaterial}
            rotation={rotation}
            position={[1.6, 0.021, -0.75]}
          />

          {/* West Zebra Crossing */}
          <group position={[-2.1, 0.021, 0]}>
            {stripes.map((zOffset, index) => (
              <mesh
                key={`w-zebra-${index}`}
                geometry={zebraStripeGeo}
                material={whitePaintMaterial}
                rotation={rotation}
                position={[0, 0, zOffset]}
              />
            ))}
          </group>

          {/* East Zebra Crossing */}
          <group position={[2.1, 0.021, 0]}>
            {stripes.map((zOffset, index) => (
              <mesh
                key={`e-zebra-${index}`}
                geometry={zebraStripeGeo}
                material={whitePaintMaterial}
                rotation={rotation}
                position={[0, 0, zOffset]}
              />
            ))}
          </group>

          {/* Painted road text labels flat on the road */}
          <Text
            position={[-5, 0.022, 0.75]}
            rotation={[-Math.PI / 2, 0, Math.PI / 2]}
            fontSize={0.28}
            color="#ffffff"
            fillOpacity={0.4}
          >
            EASTBOUND ▶
          </Text>
          <Text
            position={[5, 0.022, -0.75]}
            rotation={[-Math.PI / 2, 0, -Math.PI / 2]}
            fontSize={0.28}
            color="#ffffff"
            fillOpacity={0.4}
          >
            ◀ WESTBOUND
          </Text>
        </>
      ) : (
        <>
          {/* Double Yellow Center Lines (Bottom/South side) */}
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[-0.03, 0.021, -6.25]}
          />
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[0.03, 0.021, -6.25]}
          />

          {/* Double Yellow Center Lines (Top/North side) */}
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[-0.03, 0.021, 6.25]}
          />
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[0.03, 0.021, 6.25]}
          />

          {/* North entrance: Stop line for Southbound traffic (x < 0) */}
          <mesh
            geometry={stopBarGeometry}
            material={stopBarMaterial}
            rotation={rotation}
            position={[-0.75, 0.021, -1.6]}
          />

          {/* South entrance: Stop line for Northbound traffic (x > 0) */}
          <mesh
            geometry={stopBarGeometry}
            material={stopBarMaterial}
            rotation={rotation}
            position={[0.75, 0.021, 1.6]}
          />

          {/* North Zebra Crossing */}
          <group position={[0, 0.021, -2.1]}>
            {stripes.map((xOffset, index) => (
              <mesh
                key={`n-zebra-${index}`}
                geometry={zebraStripeGeo}
                material={whitePaintMaterial}
                rotation={rotation}
                position={[xOffset, 0, 0]}
              />
            ))}
          </group>

          {/* South Zebra Crossing */}
          <group position={[0, 0.021, 2.1]}>
            {stripes.map((xOffset, index) => (
              <mesh
                key={`s-zebra-${index}`}
                geometry={zebraStripeGeo}
                material={whitePaintMaterial}
                rotation={rotation}
                position={[xOffset, 0, 0]}
              />
            ))}
          </group>

          {/* Painted road text labels flat on the road */}
          <Text
            position={[-0.75, 0.022, -5]}
            rotation={[-Math.PI / 2, 0, Math.PI]}
            fontSize={0.28}
            color="#ffffff"
            fillOpacity={0.4}
          >
            ▼ SOUTHBOUND
          </Text>
          <Text
            position={[0.75, 0.022, 5]}
            rotation={[-Math.PI / 2, 0, 0]}
            fontSize={0.28}
            color="#ffffff"
            fillOpacity={0.4}
          >
            ▲ NORTHBOUND
          </Text>
        </>
      )}
    </group>
  );
}
