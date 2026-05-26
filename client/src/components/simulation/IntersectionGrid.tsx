import { useEffect, useMemo } from "react";
import { GridHelper, MeshStandardMaterial, PlaneGeometry } from "three";

export default function IntersectionGrid() {
  const geometry = useMemo(() => new PlaneGeometry(20, 20), []);
  const material = useMemo(
    () => new MeshStandardMaterial({ color: "#111827" }),
    [],
  );
  const grid = useMemo(() => new GridHelper(20, 20, "#1f2937", "#0f172a"), []);

  useEffect(() => {
    return () => {
      geometry.dispose();
      material.dispose();
      grid.geometry.dispose();
      if (Array.isArray(grid.material)) {
        grid.material.forEach((mat) => mat.dispose());
      } else {
        grid.material.dispose();
      }
    };
  }, [geometry, material, grid]);

  return (
    <group>
      <mesh
        geometry={geometry}
        material={material}
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow
      />
      <primitive object={grid} rotation={[-Math.PI / 2, 0, 0]} />
    </group>
  );
}
