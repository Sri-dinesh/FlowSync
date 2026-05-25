import { useMemo } from "react";
import { BoxGeometry, MeshStandardMaterial, PlaneGeometry } from "three";

interface RoadProps {
  direction: "horizontal" | "vertical";
}

export default function Road({ direction }: RoadProps) {
  const roadLength = 14;
  const roadWidth = 3;

  const baseGeometry = useMemo(
    () =>
      new BoxGeometry(
        direction === "horizontal" ? roadLength : roadWidth,
        0.1,
        direction === "horizontal" ? roadWidth : roadLength,
      ),
    [direction],
  );
  const baseMaterial = useMemo(
    () => new MeshStandardMaterial({ color: "#1a1a1a" }),
    [],
  );

  const laneGeometry = useMemo(
    () => new PlaneGeometry(roadLength - 2, 0.05),
    [roadLength],
  );
  const laneMaterial = useMemo(
    () => new MeshStandardMaterial({ color: "#f8fafc" }),
    [],
  );

  const stopGeometry = useMemo(() => new PlaneGeometry(0.2, 2), []);
  const stopMaterial = useMemo(
    () => new MeshStandardMaterial({ color: "#f8fafc" }),
    [],
  );

  const rotation = [-Math.PI / 2, 0, 0] as const;

  return (
    <group>
      <mesh
        geometry={baseGeometry}
        material={baseMaterial}
        position={[0, 0.02, 0]}
      />

      {direction === "horizontal" ? (
        <>
          <mesh
            geometry={laneGeometry}
            material={laneMaterial}
            rotation={rotation}
            position={[0, 0.06, 0.6]}
          />
          <mesh
            geometry={laneGeometry}
            material={laneMaterial}
            rotation={rotation}
            position={[0, 0.06, -0.6]}
          />
          <mesh
            geometry={stopGeometry}
            material={stopMaterial}
            rotation={rotation}
            position={[1.4, 0.06, 0]}
          />
          <mesh
            geometry={stopGeometry}
            material={stopMaterial}
            rotation={rotation}
            position={[-1.4, 0.06, 0]}
          />
        </>
      ) : (
        <>
          <mesh
            geometry={laneGeometry}
            material={laneMaterial}
            rotation={rotation}
            position={[0.6, 0.06, 0]}
          />
          <mesh
            geometry={laneGeometry}
            material={laneMaterial}
            rotation={rotation}
            position={[-0.6, 0.06, 0]}
          />
          <mesh
            geometry={stopGeometry}
            material={stopMaterial}
            rotation={rotation}
            position={[0, 0.06, 1.4]}
          />
          <mesh
            geometry={stopGeometry}
            material={stopMaterial}
            rotation={rotation}
            position={[0, 0.06, -1.4]}
          />
        </>
      )}
    </group>
  );
}
