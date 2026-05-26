import { useEffect, useMemo, useRef, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { Color, MathUtils, MeshStandardMaterial, SphereGeometry } from "three";

interface TrafficLightProps {
  color: "green" | "yellow" | "red";
  position: [number, number, number];
}

export default function TrafficLight({ color, position }: TrafficLightProps) {
  const red = useMemo(() => new Color("#ef4444"), []);
  const yellow = useMemo(() => new Color("#facc15"), []);
  const green = useMemo(() => new Color("#22c55e"), []);
  const lensGeometry = useMemo(() => new SphereGeometry(0.18, 16, 16), []);
  const redMaterial = useRef<MeshStandardMaterial>(null);
  const yellowMaterial = useRef<MeshStandardMaterial>(null);
  const greenMaterial = useRef<MeshStandardMaterial>(null);

  useEffect(() => {
    return () => {
      lensGeometry.dispose();
      redMaterial.current?.dispose();
      yellowMaterial.current?.dispose();
      greenMaterial.current?.dispose();
    };
  }, [lensGeometry]);

  useFrame((_, delta) => {
    const lerpFactor = Math.min(1, delta * 6);
    const targets = [
      { ref: redMaterial, active: color === "red" },
      { ref: yellowMaterial, active: color === "yellow" },
      { ref: greenMaterial, active: color === "green" },
    ];

    for (const target of targets) {
      const material = target.ref.current;
      if (!material) {
        continue;
      }
      const targetIntensity = target.active ? 2 : 0.25;
      material.emissiveIntensity = MathUtils.lerp(
        material.emissiveIntensity,
        targetIntensity,
        lerpFactor,
      );
    }
  });

  const lens = (
    lensColor: Color,
    isActive: boolean,
    y: number,
    materialRef: RefObject<MeshStandardMaterial>,
  ) => (
    <mesh position={[0, y, 0]}>
      <primitive object={lensGeometry} attach="geometry" />
      <meshStandardMaterial
        ref={materialRef}
        color={lensColor}
        emissive={lensColor}
        emissiveIntensity={isActive ? 2 : 0.25}
      />
    </mesh>
  );

  return (
    <group position={position}>
      {lens(red, color === "red", 0.35, redMaterial)}
      {lens(yellow, color === "yellow", 0, yellowMaterial)}
      {lens(green, color === "green", -0.35, greenMaterial)}
    </group>
  );
}
