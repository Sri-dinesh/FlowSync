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
  const roadWidth = 6;

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
  const yellowLineLength = 8;
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
        direction === "horizontal" ? 0.12 : 6.0,
        direction === "horizontal" ? 6.0 : 0.12,
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
            position={[-7, 0.021, 0.03]}
          />
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[-7, 0.021, -0.03]}
          />

          {/* Double Yellow Center Lines (Right side) */}
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[7, 0.021, 0.03]}
          />
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[7, 0.021, -0.03]}
          />

          {/* West entrance: Stop line for Eastbound traffic (z > 0) */}
          <mesh
            geometry={stopBarGeometry}
            material={stopBarMaterial}
            rotation={rotation}
            position={[-3.1, 0.021, 0]}
          />

          {/* East entrance: Stop line for Westbound traffic (z < 0) */}
          <mesh
            geometry={stopBarGeometry}
            material={stopBarMaterial}
            rotation={rotation}
            position={[3.1, 0.021, 0]}
          />


          {/* Painted road text labels flat on the road */}
          <Text
            position={[-5, 0.022, 1.5]}
            rotation={[-Math.PI / 2, 0, Math.PI / 2]}
            fontSize={0.28}
            color="#ffffff"
            fillOpacity={0.4}
          >
            EASTBOUND ▶
          </Text>
          <Text
            position={[5, 0.022, -1.5]}
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
            position={[-0.03, 0.021, -7]}
          />
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[0.03, 0.021, -7]}
          />

          {/* Double Yellow Center Lines (Top/North side) */}
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[-0.03, 0.021, 7]}
          />
          <mesh
            geometry={yellowLineGeometry}
            material={yellowLineMaterial}
            rotation={rotation}
            position={[0.03, 0.021, 7]}
          />

          {/* North entrance: Stop line for Southbound traffic (x < 0) */}
          <mesh
            geometry={stopBarGeometry}
            material={stopBarMaterial}
            rotation={rotation}
            position={[0, 0.021, -3.1]}
          />

          {/* South entrance: Stop line for Northbound traffic (x > 0) */}
          <mesh
            geometry={stopBarGeometry}
            material={stopBarMaterial}
            rotation={rotation}
            position={[0, 0.021, 3.1]}
          />


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
