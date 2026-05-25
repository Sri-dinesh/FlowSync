import { useMemo } from "react";
import { MeshStandardMaterial } from "three";

import type { VehicleState } from "@/types/simulation";

interface VehicleProps {
  vehicle: VehicleState;
}

function mapRange(
  value: number,
  inMin: number,
  inMax: number,
  outMin: number,
  outMax: number,
) {
  return outMin + ((value - inMin) * (outMax - outMin)) / (inMax - inMin);
}

function getVehiclePosition(lane: string, position: number) {
  const progress = Math.min(Math.max(position, 0), 1);

  switch (lane) {
    case "north":
      return [-0.5, 0.12, mapRange(progress, 0, 1, 8, 0)] as const;
    case "south":
      return [0.5, 0.12, mapRange(progress, 0, 1, -8, 0)] as const;
    case "east":
      return [mapRange(progress, 0, 1, 8, 0), 0.12, -0.5] as const;
    case "west":
      return [mapRange(progress, 0, 1, -8, 0), 0.12, 0.5] as const;
    default:
      return [0, 0.12, 0] as const;
  }
}

function getRotation(lane: string) {
  switch (lane) {
    case "north":
      return [0, Math.PI, 0] as const;
    case "south":
      return [0, 0, 0] as const;
    case "east":
      return [0, -Math.PI / 2, 0] as const;
    case "west":
      return [0, Math.PI / 2, 0] as const;
    default:
      return [0, 0, 0] as const;
  }
}

export default function Vehicle({ vehicle }: VehicleProps) {
  const position = getVehiclePosition(vehicle.lane, vehicle.position);
  const rotation = getRotation(vehicle.lane);
  const material = useMemo(
    () =>
      new MeshStandardMaterial({
        color: vehicle.state === "waiting" ? "#fbbf24" : "#f8fafc",
      }),
    [vehicle.state],
  );

  return (
    <mesh position={position} rotation={rotation} material={material}>
      <boxGeometry args={[0.4, 0.2, 0.8]} />
    </mesh>
  );
}
