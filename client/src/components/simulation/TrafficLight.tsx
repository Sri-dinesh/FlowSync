"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import { BoxGeometry, CylinderGeometry, Color, MathUtils, MeshStandardMaterial, SphereGeometry } from "three";

interface TrafficLightProps {
  color: "green" | "yellow" | "red" | "left-green" | "left-yellow";
  position: [number, number, number];
  direction: "north" | "south" | "east" | "west";
}

export default function TrafficLight({ color, position, direction }: TrafficLightProps) {
  const red = useMemo(() => new Color("#ff0000"), []);
  const darkRed = useMemo(() => new Color("#220000"), []);
  const yellow = useMemo(() => new Color("#ffcc00"), []);
  const darkYellow = useMemo(() => new Color("#221a00"), []);
  const green = useMemo(() => new Color("#00ff00"), []);
  const darkGreen = useMemo(() => new Color("#002200"), []);

  const poleGeometry = useMemo(() => new CylinderGeometry(0.12, 0.12, 4.0, 12), []);
  const housingGeometry = useMemo(() => new BoxGeometry(0.38, 1.0, 0.38), []);
  const lensGeometry = useMemo(() => new SphereGeometry(0.15, 20, 20), []);
  
  const poleMaterial = useMemo(() => new MeshStandardMaterial({ 
    color: "#2d3748", 
    metalness: 0.7, 
    roughness: 0.2 
  }), []);
  const housingMaterial = useMemo(() => new MeshStandardMaterial({ 
    color: "#111111", 
    roughness: 0.4, 
    metalness: 0.8 
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
      housingGeometry.dispose();
      lensGeometry.dispose();
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
    poleGeometry, housingGeometry, lensGeometry, poleMaterial, housingMaterial,
    cctvBodyGeometry, cctvVisorGeometry, cctvLensGeometry, cctvLedGeometry,
    cctvHousingMaterial, cctvVisorMaterial, cctvLensMaterial, cctvLedMaterial
  ]);

  useFrame((state, delta) => {
    const lerpFactor = Math.min(1, delta * 8);

    const targets = [
      { ref: redMaterial, active: color === "red", light: red, dark: darkRed },
      { ref: yellowMaterial, active: color === "yellow" || color === "left-yellow", light: yellow, dark: darkYellow },
      { ref: greenMaterial, active: color === "green" || color === "left-green", light: green, dark: darkGreen },
    ];

    for (const target of targets) {
      const material = target.ref.current;
      if (material) {
        // Soft glow for the lens body so it doesn't swallow the arrows
        const targetIntensity = target.active ? 0.8 : 0.0;
        material.emissiveIntensity = MathUtils.lerp(
          material.emissiveIntensity,
          targetIntensity,
          lerpFactor,
        );
        material.color.lerpColors(target.dark, target.light, material.emissiveIntensity / 0.8);
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
          bracketPos: [1.35, 2.0, 0] as [number, number, number],
          bracketSize: [2.7, 0.1, 0.1] as [number, number, number],
          housingPos: [1.7, 2.0, 0] as [number, number, number],
          zSign: -1,
          lightPos: [1.7, 1.2, -0.3] as [number, number, number],
          // CCTV offsets
          cctvPos: [1.0, 2.25, -0.2] as [number, number, number],
          cctvMountPos: [1.0, 2.125, -0.1] as [number, number, number],
          cctvMountSize: [0.03, 0.25, 0.2] as [number, number, number],
          cctvRot: [0.35, Math.PI + 0.3, 0] as [number, number, number],
        };
      case "south":
        return {
          bracketPos: [-1.35, 2.0, 0] as [number, number, number],
          bracketSize: [2.7, 0.1, 0.1] as [number, number, number],
          housingPos: [-1.7, 2.0, 0] as [number, number, number],
          zSign: 1,
          lightPos: [-1.7, 1.2, 0.3] as [number, number, number],
          // CCTV offsets
          cctvPos: [-1.0, 2.25, 0.2] as [number, number, number],
          cctvMountPos: [-1.0, 2.125, 0.1] as [number, number, number],
          cctvMountSize: [0.03, 0.25, 0.2] as [number, number, number],
          cctvRot: [0.35, -0.3, 0] as [number, number, number],
        };
      case "east":
        return {
          bracketPos: [0, 2.0, 1.35] as [number, number, number],
          bracketSize: [0.1, 0.1, 2.7] as [number, number, number],
          housingPos: [0, 2.0, 1.7] as [number, number, number],
          zSign: 1,
          lightPos: [0.3, 1.2, 1.7] as [number, number, number],
          // CCTV offsets
          cctvPos: [0.2, 2.25, 1.0] as [number, number, number],
          cctvMountPos: [0.1, 2.125, 1.0] as [number, number, number],
          cctvMountSize: [0.2, 0.25, 0.03] as [number, number, number],
          cctvRot: [0.35, Math.PI / 2 + 0.3, 0] as [number, number, number],
        };
      case "west":
        return {
          bracketPos: [0, 2.0, -1.35] as [number, number, number],
          bracketSize: [0.1, 0.1, 2.7] as [number, number, number],
          housingPos: [0, 2.0, -1.7] as [number, number, number],
          zSign: -1,
          lightPos: [-0.3, 1.2, -1.7] as [number, number, number],
          // CCTV offsets
          cctvPos: [-0.2, 2.25, -1.0] as [number, number, number],
          cctvMountPos: [-0.1, 2.125, -1.0] as [number, number, number],
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

  const renderLens = (
    localY: number,
    lensColor: Color,
    ref: React.RefObject<MeshStandardMaterial | null>,
    isActive: boolean,
    isLeftTurn: boolean,
    isStandard: boolean
  ) => {
    const lensPos: [number, number, number] = direction === "north" || direction === "south"
      ? [offsets.housingPos[0], offsets.housingPos[1] + localY, offsets.zSign * 0.19]
      : [offsets.zSign * 0.19, offsets.housingPos[1] + localY, offsets.housingPos[2]];

    const textRot: [number, number, number] = direction === "north"
      ? [0, Math.PI, 0]
      : direction === "south"
      ? [0, 0, 0]
      : direction === "east"
      ? [0, Math.PI / 2, 0]
      : [0, -Math.PI / 2, 0];

    // Visual offset to place text exactly on the outer surface of the lens (radius 0.15)
    const tPos: [number, number, number] = direction === "north" || direction === "south"
      ? [lensPos[0], lensPos[1], lensPos[2] + (offsets.zSign * 0.16)]
      : [lensPos[0] + (offsets.zSign * 0.16), lensPos[1], lensPos[2]];

    // Base text props
    const textProps = {
      fontSize: 0.28, // Larger arrows for visibility
      anchorX: "center" as const,
      anchorY: "middle" as const,
      depthOffset: -10, // Prevent z-fighting
    };

    // Stencil active/inactive colors
    const activeHex = "ffffff";
    const inactiveHex = "111111";

    return (
      <group>
        <mesh geometry={lensGeometry} position={lensPos}>
          <meshStandardMaterial ref={ref} color={lensColor} emissive={lensColor} roughness={0.1} metalness={0.8} />
        </mesh>
        
        {/* Render Arrows as Glowing Stencils */}
        <group position={tPos} rotation={textRot}>
          {isLeftTurn ? (
            <Text position={[0, 0, 0]} {...textProps}>
              <meshBasicMaterial color={isActive ? `#${activeHex}` : `#${inactiveHex}`} toneMapped={false} />
              {"\u2190"}
            </Text>
          ) : isStandard ? (
            <group>
              {/* Up arrow via rotated right arrow */}
              <Text position={[-0.08, 0, 0]} rotation={[0, 0, Math.PI / 2]} {...textProps}>
                <meshBasicMaterial color={isActive ? `#${activeHex}` : `#${inactiveHex}`} toneMapped={false} />
                {"\u2192"}
              </Text>
              {/* Right arrow */}
              <Text position={[0.08, 0, 0]} {...textProps}>
                <meshBasicMaterial color={isActive ? `#${activeHex}` : `#${inactiveHex}`} toneMapped={false} />
                {"\u2192"}
              </Text>
            </group>
          ) : null}
        </group>
      </group>
    );
  };

  return (
    <group position={position}>
      {/* Main vertical pole */}
      <mesh geometry={poleGeometry} material={poleMaterial} position={[0, 2.0, 0]} castShadow />
      
      {/* Traffic light extension arm */}
      <mesh position={offsets.bracketPos} castShadow>
        <boxGeometry args={offsets.bracketSize} />
        <meshStandardMaterial color="#374151" roughness={0.3} metalness={0.4} />
      </mesh>
      
      {/* Single Traffic Light Housing */}
      <mesh geometry={housingGeometry} material={housingMaterial} position={offsets.housingPos} castShadow />
      
      {/* Lenses */}
      {renderLens(0.25, red, redMaterial, color === "red", false, false)}
      {renderLens(0.0, yellow, yellowMaterial, color === "yellow" || color === "left-yellow", color === "left-yellow", color === "yellow")}
      {renderLens(-0.25, green, greenMaterial, color === "green" || color === "left-green", color === "left-green", color === "green")}

      <pointLight
        position={offsets.lightPos}
        color={lightColorHex}
        intensity={2.0}
        distance={8}
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
