"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { BoxGeometry, CylinderGeometry, Color, MathUtils, MeshStandardMaterial, SphereGeometry } from "three";

interface TrafficLightProps {
  color: "green" | "yellow" | "red";
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

  const redMaterial = useRef<MeshStandardMaterial>(null);
  const yellowMaterial = useRef<MeshStandardMaterial>(null);
  const greenMaterial = useRef<MeshStandardMaterial>(null);

  useEffect(() => {
    return () => {
      poleGeometry.dispose();
      lensGeometry.dispose();
      housingGeometry.dispose();
      poleMaterial.dispose();
      housingMaterial.dispose();
    };
  }, [poleGeometry, lensGeometry, housingGeometry, poleMaterial, housingMaterial]);

  useFrame((_, delta) => {
    const lerpFactor = Math.min(1, delta * 8);
    const targets = [
      { ref: redMaterial, active: color === "red" },
      { ref: yellowMaterial, active: color === "yellow" },
      { ref: greenMaterial, active: color === "green" },
    ];

    for (const target of targets) {
      const material = target.ref.current;
      if (material) {
        const targetIntensity = target.active ? 6.0 : 0.0;
        material.emissiveIntensity = MathUtils.lerp(
          material.emissiveIntensity,
          targetIntensity,
          lerpFactor,
        );
      }
    }
  });

  const offsets = useMemo(() => {
    switch (direction) {
      case "north":
        return {
          bracketPos: [0.4, 0.7, 0] as [number, number, number],
          bracketSize: [0.8, 0.05, 0.05] as [number, number, number],
          housingPos: [0.8, 0.7, 0] as [number, number, number],
          lensOffset: [0.8, 0] as [number, number],
          zSign: 1,
          lightPos: [0.8, -0.3, 0.3] as [number, number, number],
        };
      case "south":
        return {
          bracketPos: [-0.4, 0.7, 0] as [number, number, number],
          bracketSize: [0.8, 0.05, 0.05] as [number, number, number],
          housingPos: [-0.8, 0.7, 0] as [number, number, number],
          lensOffset: [-0.8, 0] as [number, number],
          zSign: -1,
          lightPos: [-0.8, -0.3, -0.3] as [number, number, number],
        };
      case "east":
        return {
          bracketPos: [0, 0.7, -0.4] as [number, number, number],
          bracketSize: [0.05, 0.05, 0.8] as [number, number, number],
          housingPos: [0, 0.7, -0.8] as [number, number, number],
          lensOffset: [0, -0.8] as [number, number],
          zSign: 1,
          lightPos: [0.3, -0.3, -0.8] as [number, number, number],
        };
      case "west":
        return {
          bracketPos: [0, 0.7, 0.4] as [number, number, number],
          bracketSize: [0.05, 0.05, 0.8] as [number, number, number],
          housingPos: [0, 0.7, 0.8] as [number, number, number],
          lensOffset: [0, 0.8] as [number, number],
          zSign: -1,
          lightPos: [-0.3, -0.3, 0.8] as [number, number, number],
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

  const pointLightIntensity = color === "red" || color === "yellow" || color === "green" ? 4.5 : 0;

  return (
    <group position={position}>
      <mesh geometry={poleGeometry} material={poleMaterial} position={[0, 0.8, 0]} castShadow />
      <mesh position={offsets.bracketPos} castShadow>
        <boxGeometry args={offsets.bracketSize} />
        <meshStandardMaterial color="#374151" roughness={0.3} metalness={0.4} />
      </mesh>
      <mesh geometry={housingGeometry} material={housingMaterial} position={offsets.housingPos} castShadow />
      {lensElement(red, color === "red", 0.25, redMaterial)}
      {lensElement(yellow, color === "yellow", 0.1, yellowMaterial)}
      {lensElement(green, color === "green", -0.15, greenMaterial)}
      <pointLight
        position={offsets.lightPos}
        color={lightColorHex}
        intensity={pointLightIntensity}
        distance={6}
        decay={2}
      />
    </group>
  );
}
