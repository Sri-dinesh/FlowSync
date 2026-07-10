"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import { BoxGeometry, CylinderGeometry, Color, MathUtils, MeshStandardMaterial, SphereGeometry, DoubleSide } from "three";

interface TrafficLightProps {
  color: "green" | "yellow" | "red" | "left-green" | "left-yellow";
  position: [number, number, number];
  direction: "north" | "south" | "east" | "west";
}

export default function TrafficLight({ color, position, direction }: TrafficLightProps) {
  const red = useMemo(() => new Color("#ff0000"), []);
  const yellow = useMemo(() => new Color("#ffcc00"), []);
  const green = useMemo(() => new Color("#00ff00"), []);

  const poleGeometry = useMemo(() => new CylinderGeometry(0.08, 0.08, 2.5, 12), []);
  const lensGeometry = useMemo(() => new SphereGeometry(0.15, 20, 20), []);
  const housingGeometry = useMemo(() => new BoxGeometry(0.38, 1.0, 0.38), []);
  
  const poleMaterial = useMemo(() => new MeshStandardMaterial({ 
    color: "#2d3748", 
    metalness: 0.7, 
    roughness: 0.2 
  }), []);
  const housingMaterial = useMemo(() => new MeshStandardMaterial({ 
    color: "#1a1a1a", 
    roughness: 0.3, 
    metalness: 0.4 
  }), []);

  // CCTV Camera Geometries & Materials
  const cctvBodyGeometry = useMemo(() => new CylinderGeometry(0.05, 0.05, 0.2, 12), []);
  const cctvVisorGeometry = useMemo(() => new BoxGeometry(0.12, 0.02, 0.22), []);
  const cctvLensGeometry = useMemo(() => new CylinderGeometry(0.04, 0.04, 0.02, 12), []);
  const cctvLedGeometry = useMemo(() => new SphereGeometry(0.02, 8, 8), []);

  const cctvHousingMaterial = useMemo(() => new MeshStandardMaterial({
    color: "#27272a", // Sleek dark charcoal to match poles
    roughness: 0.3,
    metalness: 0.4
  }), []);
  const cctvVisorMaterial = useMemo(() => new MeshStandardMaterial({
    color: "#18181b", // Dark visor
    roughness: 0.4,
    metalness: 0.2
  }), []);
  const cctvLensMaterial = useMemo(() => new MeshStandardMaterial({
    color: "#09090b", // Glossy camera lens face
    roughness: 0.05,
    metalness: 0.9
  }), []);
  const cctvLedMaterial = useMemo(() => new MeshStandardMaterial({
    color: "#ef4444",
    emissive: "#ef4444",
    emissiveIntensity: 0.2,
    roughness: 0.5
  }), []);

  const redMaterial = useRef<MeshStandardMaterial>(null);
  const yellowMaterial = useRef<MeshStandardMaterial>(null);
  const greenMaterial = useRef<MeshStandardMaterial>(null);
  const cctvLedMaterialRef = useRef<MeshStandardMaterial>(null);

  useEffect(() => {
    return () => {
      poleGeometry.dispose();
      lensGeometry.dispose();
      housingGeometry.dispose();
      poleMaterial.dispose();
      housingMaterial.dispose();

      cctvBodyGeometry.dispose();
      cctvVisorGeometry.dispose();
      cctvLensGeometry.dispose();
      cctvLedGeometry.dispose();
      cctvHousingMaterial.dispose();
      cctvVisorMaterial.dispose();
      cctvLensMaterial.dispose();
      cctvLedMaterial.dispose();
    };
  }, [
    poleGeometry, lensGeometry, housingGeometry, poleMaterial, housingMaterial,
    cctvBodyGeometry, cctvVisorGeometry, cctvLensGeometry, cctvLedGeometry,
    cctvHousingMaterial, cctvVisorMaterial, cctvLensMaterial, cctvLedMaterial
  ]);

  useFrame((state, delta) => {
    const lerpFactor = Math.min(1, delta * 8);
    const targets = [
      { ref: redMaterial, active: color === "red" || color === "left-green" || color === "left-yellow" },
      { ref: yellowMaterial, active: color === "yellow" || color === "left-yellow" },
      { ref: greenMaterial, active: color === "green" || color === "left-green" },
    ];

    for (const target of targets) {
      const material = target.ref.current;
      if (material) {
        const targetIntensity = target.active ? 4.0 : 0.0;
        material.emissiveIntensity = MathUtils.lerp(
          material.emissiveIntensity,
          targetIntensity,
          lerpFactor,
        );
      }
    }

    // Blink status LED: lit for 0.4s every 1.2s
    if (cctvLedMaterialRef.current) {
      const elapsedTime = state.clock.getElapsedTime();
      const isLit = (elapsedTime % 1.2) < 0.4;
      cctvLedMaterialRef.current.emissiveIntensity = isLit ? 2.0 : 0.05;
    }
  });

  const offsets = useMemo(() => {
    switch (direction) {
      case "north":
        return {
          bracketPos: [0.85, 0.7, 0] as [number, number, number],
          bracketSize: [1.7, 0.05, 0.05] as [number, number, number],
          housingPos: [1.7, 0.7, 0] as [number, number, number],
          lensOffset: [1.7, 0] as [number, number],
          zSign: 1,
          lightPos: [1.7, -0.3, 0.3] as [number, number, number],
          // CCTV offsets
          cctvPos: [0.85, 0.95, -0.2] as [number, number, number],
          cctvMountPos: [0.85, 0.825, -0.1] as [number, number, number],
          cctvMountSize: [0.03, 0.25, 0.2] as [number, number, number],
          cctvRot: [0.35, Math.PI + 0.3, 0] as [number, number, number],
        };
      case "south":
        return {
          bracketPos: [-0.85, 0.7, 0] as [number, number, number],
          bracketSize: [1.7, 0.05, 0.05] as [number, number, number],
          housingPos: [-1.7, 0.7, 0] as [number, number, number],
          lensOffset: [-1.7, 0] as [number, number],
          zSign: -1,
          lightPos: [-1.7, -0.3, -0.3] as [number, number, number],
          // CCTV offsets
          cctvPos: [-0.85, 0.95, 0.2] as [number, number, number],
          cctvMountPos: [-0.85, 0.825, 0.1] as [number, number, number],
          cctvMountSize: [0.03, 0.25, 0.2] as [number, number, number],
          cctvRot: [0.35, -0.3, 0] as [number, number, number],
        };
      case "east":
        return {
          bracketPos: [0, 0.7, 0.85] as [number, number, number],
          bracketSize: [0.05, 0.05, 1.7] as [number, number, number],
          housingPos: [0, 0.7, 1.7] as [number, number, number],
          lensOffset: [0, 1.7] as [number, number],
          zSign: 1,
          lightPos: [0.3, -0.3, 1.7] as [number, number, number],
          // CCTV offsets
          cctvPos: [0.2, 0.95, 0.85] as [number, number, number],
          cctvMountPos: [0.1, 0.825, 0.85] as [number, number, number],
          cctvMountSize: [0.2, 0.25, 0.03] as [number, number, number],
          cctvRot: [0.35, Math.PI / 2 + 0.3, 0] as [number, number, number],
        };
      case "west":
        return {
          bracketPos: [0, 0.7, -0.85] as [number, number, number],
          bracketSize: [0.05, 0.05, 1.7] as [number, number, number],
          housingPos: [0, 0.7, -1.7] as [number, number, number],
          lensOffset: [0, -1.7] as [number, number],
          zSign: -1,
          lightPos: [-0.3, -0.3, -1.7] as [number, number, number],
          // CCTV offsets
          cctvPos: [-0.2, 0.95, -0.85] as [number, number, number],
          cctvMountPos: [-0.1, 0.825, -0.85] as [number, number, number],
          cctvMountSize: [0.2, 0.25, 0.03] as [number, number, number],
          cctvRot: [0.35, -Math.PI / 2 - 0.3, 0] as [number, number, number],
        };
    }
  }, [direction]);

  const lightColorHex = useMemo(() => {
    if (color === "red") return "#ff0000";
    if (color === "yellow") return "#ffcc00";
    return "#00ff00";
  }, [color]);

  const lensElement = (
    lensColor: Color,
    isActive: boolean,
    localY: number,
    materialRef: React.RefObject<MeshStandardMaterial | null>,
  ) => {
    const lensPos: [number, number, number] = direction === "north" || direction === "south"
      ? [offsets.lensOffset[0], 0.7 + localY, offsets.zSign * 0.15]
      : [offsets.zSign * 0.15, 0.7 + localY, offsets.lensOffset[1]];

    return (
      <mesh geometry={lensGeometry} position={lensPos}>
        <meshStandardMaterial
          ref={materialRef}
          color={lensColor}
          emissive={lensColor}
          emissiveIntensity={isActive ? 6.0 : 0.0}
          roughness={0.05}
          metalness={0.05}
        />
      </mesh>
    );
  };

  const arrowElement = (localY: number, arrowColor: string, isActive: boolean, symbol: string = "←") => {
    if (!isActive) return null;

    const textPos: [number, number, number] = direction === "north" || direction === "south"
      ? [offsets.lensOffset[0], 0.7 + localY, offsets.zSign * 0.17]
      : [offsets.zSign * 0.17, 0.7 + localY, offsets.lensOffset[1]];

    const textRot: [number, number, number] = direction === "north"
      ? [0, 0, 0]
      : direction === "south"
      ? [0, Math.PI, 0]
      : direction === "east"
      ? [0, -Math.PI / 2, 0]
      : [0, Math.PI / 2, 0];

    return (
      <Text
        position={textPos}
        rotation={textRot}
        fontSize={symbol.length > 1 ? 0.18 : 0.25}
        color={arrowColor}
        anchorX="center"
        anchorY="middle"
        fontWeight="bold"
      >
        {symbol}
      </Text>
    );
  };

  const pointLightIntensity = color === "red" || color === "yellow" || color === "green" || color === "left-green" || color === "left-yellow" ? 2.0 : 0;

  return (
    <group position={position}>
      {/* Main vertical pole */}
      <mesh geometry={poleGeometry} material={poleMaterial} position={[0, 0.8, 0]} castShadow />
      
      {/* Traffic light extension arm */}
      <mesh position={offsets.bracketPos} castShadow>
        <boxGeometry args={offsets.bracketSize} />
        <meshStandardMaterial color="#374151" roughness={0.3} metalness={0.4} />
      </mesh>
      
      {/* Traffic light housing & lenses */}
      <mesh geometry={housingGeometry} material={housingMaterial} position={offsets.housingPos} castShadow />
      {lensElement(red, color === "red" || color === "left-green" || color === "left-yellow", 0.25, redMaterial)}
      {lensElement(yellow, color === "yellow" || color === "left-yellow", 0.1, yellowMaterial)}
      {lensElement(green, color === "green" || color === "left-green", -0.15, greenMaterial)}
      {arrowElement(-0.15, "#00ff00", color === "left-green", "←")}
      {arrowElement(-0.15, "#00ff00", color === "green", "↑ →")}
      {arrowElement(0.1, "#ffcc00", color === "left-yellow", "←")}
      {arrowElement(0.1, "#ffcc00", color === "yellow", "↑ →")}
      <pointLight
        position={offsets.lightPos}
        color={lightColorHex}
        intensity={pointLightIntensity}
        distance={6}
        decay={2}
      />

      {/* CCTV Camera bracket arm */}
      <mesh position={offsets.cctvMountPos} castShadow>
        <boxGeometry args={offsets.cctvMountSize} />
        <meshStandardMaterial color="#374151" roughness={0.3} metalness={0.4} />
      </mesh>

      {/* CCTV Camera Unit */}
      <group position={offsets.cctvPos} rotation={offsets.cctvRot}>
        {/* Camera Body */}
        <mesh geometry={cctvBodyGeometry} material={cctvHousingMaterial} rotation={[Math.PI / 2, 0, 0]} castShadow />
        
        {/* Sun Visor / Shield */}
        <mesh geometry={cctvVisorGeometry} material={cctvVisorMaterial} position={[0, 0.06, 0]} castShadow />
        
        {/* Lens */}
        <mesh geometry={cctvLensGeometry} material={cctvLensMaterial} position={[0, 0, 0.101]} rotation={[Math.PI / 2, 0, 0]} />
        
        {/* Blinking Status LED */}
        <mesh geometry={cctvLedGeometry} material={cctvLedMaterial} ref={cctvLedMaterialRef} position={[0, 0.04, -0.101]} />
      </group>
    </group>
  );
}
