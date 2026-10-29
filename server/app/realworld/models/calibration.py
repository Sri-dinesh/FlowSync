"""User-supplied image geometry; structural validity is not field calibration accuracy."""
import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Coordinate = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False, strict=True)]
Point = tuple[Coordinate, Coordinate]
Direction = Literal["north", "south", "east", "west"]
Turn = Literal["straight", "left", "right", "u_turn"]
EPS = 1e-9


def cross(a, b, p):
    return (b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])


def on_segment(a, b, p):
    return (abs(cross(a, b, p)) <= EPS
            and min(a[0], b[0])-EPS <= p[0] <= max(a[0], b[0])+EPS
            and min(a[1], b[1])-EPS <= p[1] <= max(a[1], b[1])+EPS)


def edges(vertices):
    return zip(vertices, vertices[1:]+vertices[:1])


def orientation(vertices):
    return 1 if sum(a[0]*b[1]-b[0]*a[1] for a, b in edges(vertices)) > 0 else -1


def contains(vertices, point):
    sign = orientation(vertices)
    return all(sign*cross(a, b, point) >= -EPS for a, b in edges(vertices))


def interiors_overlap(first, second):
    for polygon, other in ((first, second), (second, first)):
        sign = orientation(polygon)
        if any(all(sign*cross(a, b, p) <= EPS for p in other) for a, b in edges(polygon)):
            return False
    return True


class ConvexRegion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    vertices: Annotated[tuple[Point, ...], Field(min_length=3, max_length=16)]

    @model_validator(mode="after")
    def valid_polygon(self):
        vertices = self.vertices
        if len(set(vertices)) != len(vertices):
            raise ValueError("Polygon vertices must be distinct; omit the repeated closing point.")
        sign = orientation(vertices)
        for i, (a, b) in enumerate(edges(vertices)):
            if any(sign*cross(a, b, p) <= EPS for j, p in enumerate(vertices)
                   if j not in (i, (i+1) % len(vertices))):
                raise ValueError("Regions must be simple, strictly convex, nonzero-area polygons in boundary order.")
        return self


class ExitRegion(ConvexRegion):
    exit_id: Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")]
    turns_from: Annotated[dict[Direction, Turn], Field(min_length=1, max_length=4)]


class ApproachRegion(ConvexRegion):
    approach: Direction
    stop_line: tuple[Point, Point]

    @model_validator(mode="after")
    def valid_stop_line(self):
        vertices = self.vertices
        start, end = self.stop_line
        if sum((a-b)**2 for a, b in zip(start, end)) <= EPS**2:
            raise ValueError("Stop-line endpoints must differ.")
        if not any(on_segment(a, b, start) and on_segment(a, b, end) for a, b in edges(vertices)):
            raise ValueError("The stop line must lie on one upstream-region boundary edge.")
        return self


class CameraCalibration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["camera_geometry_v1"] = "camera_geometry_v1"
    camera_id: Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")]
    source: Annotated[str, Field(min_length=1, max_length=4096)]
    frame_width: Annotated[int, Field(gt=0, le=16384, strict=True)]
    frame_height: Annotated[int, Field(gt=0, le=16384, strict=True)]
    approaches: Annotated[tuple[ApproachRegion, ...], Field(min_length=1, max_length=4)]
    exits: Annotated[tuple[ExitRegion, ...], Field(max_length=4)] = ()

    @model_validator(mode="after")
    def disjoint_approaches(self):
        if len({r.approach for r in self.approaches}) != len(self.approaches):
            raise ValueError("Each approach may have only one region.")
        for i, first in enumerate(self.approaches):
            for second in self.approaches[i+1:]:
                if interiors_overlap(first.vertices, second.vertices):
                    raise ValueError("Approach interiors must not overlap; shared edges are allowed but ambiguous.")
        if len({region.exit_id for region in self.exits}) != len(self.exits):
            raise ValueError("Exit IDs must be unique.")
        approaches = {region.approach for region in self.approaches}
        for i, region in enumerate(self.exits):
            if not set(region.turns_from) <= approaches:
                raise ValueError("Exit turn mappings must name configured approaches.")
            if any(interiors_overlap(region.vertices, other.vertices) for other in (*self.approaches, *self.exits[i+1:])):
                raise ValueError("Exit interiors must not overlap approaches or other exits.")
        return self

    def canonical_json(self):
        # Preserve existing approach-only configuration identities.
        return json.dumps(self.model_dump(mode="json", exclude={"exits"} if not self.exits else set()),
                          sort_keys=True, separators=(",", ":"), allow_nan=False)

    @property
    def sha256(self):
        return hashlib.sha256(self.canonical_json().encode()).hexdigest()


class GeometryObservation(BaseModel):
    status: Literal["matched", "frame_size_mismatch", "detector_unavailable"]
    calibration_sha256: str
    configured_approaches: tuple[Direction, ...]
    approach_counts: dict[Direction, int]
    ambiguous_boxes: int = 0
    unassigned_boxes: int = 0
    assigned_boxes: int = 0
