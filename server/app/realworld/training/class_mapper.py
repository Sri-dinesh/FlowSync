"""
ClassMapper — Converts class annotations from different dataset formats to the unified 7-class format.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.config import VEHICLE_CLASSES


class ClassMapper:
    """
    Maps class names/IDs across all datasets to the unified 7-class scheme:
    0: bicycle, 1: motorcycle, 2: car, 3: auto_rickshaw, 4: van, 5: bus, 6: truck
    """

    DATASET_MAPPINGS: Dict[str, Dict] = {
        "idd": {
            "car": "car", "truck": "truck", "bus": "bus",
            "motorcycle": "motorcycle", "autorickshaw": "auto_rickshaw",
            "bicycle": "bicycle", "vehicle_fallback": "car",
        },
        "coco": {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"},
        "ua_detrac": {"car": "car", "bus": "bus", "van": "van", "others": "car"},
        "mio_tcd": {
            "articulated_truck": "truck", "bicycle": "bicycle", "bus": "bus",
            "car": "car", "motorcycle": "motorcycle",
            "motorized_vehicle": "car", "pickup_truck": "van",
            "single_unit_truck": "truck", "work_van": "van",
            "non-motorized_vehicle": "bicycle", "pedestrian": None,  # skip
        },
        "roboflow": {
            "car": "car", "motorcycle": "motorcycle", "bus": "bus", "truck": "truck",
            "bicycle": "bicycle", "auto_rickshaw": "auto_rickshaw",
            "auto-rickshaw": "auto_rickshaw", "autorickshaw": "auto_rickshaw",
            "two-wheeler": "motorcycle", "two_wheeler": "motorcycle",
            "van": "van", "suv": "car", "jeep": "car",
        },
    }

    # Reverse map: unified class name -> unified class ID
    NAME_TO_ID: Dict[str, int] = {v: k for k, v in VEHICLE_CLASSES.items()}

    def map_annotation(
        self,
        source_class: Union[str, int],
        source_dataset: str,
    ) -> Optional[str]:
        """
        Map a source class (name or ID) from a dataset to unified class name.
        Returns None if class should be skipped.
        """
        mapping = self.DATASET_MAPPINGS.get(source_dataset, {})
        unified = mapping.get(source_class)
        if unified is None and isinstance(source_class, str):
            unified = mapping.get(source_class.lower())
        return unified

    def get_unified_id(self, unified_class_name: str) -> Optional[int]:
        """Returns unified integer class ID for a class name."""
        return self.NAME_TO_ID.get(unified_class_name)

    def convert_yolo_label_file(
        self, file_path: Path, source_dataset: str
    ) -> int:
        """
        In-place conversion of a YOLO .txt label file to unified class IDs.
        Returns number of lines converted.
        """
        if not file_path.exists():
            return 0

        lines = file_path.read_text().strip().splitlines()
        new_lines = []
        converted = 0

        for line in lines:
            parts = line.split()
            if not parts:
                continue
            orig_id = int(parts[0])
            unified_name = self.map_annotation(orig_id, source_dataset)
            if unified_name is None:
                continue  # skip non-vehicle classes
            unified_id = self.get_unified_id(unified_name)
            if unified_id is None:
                continue
            new_lines.append(f"{unified_id} {' '.join(parts[1:])}")
            converted += 1

        file_path.write_text("\n".join(new_lines))
        return converted

    def batch_convert(self, labels_dir: Path, source_dataset: str) -> Dict[str, int]:
        """
        Convert all .txt files in directory to unified class IDs.
        Returns {converted: N, skipped: M, files_processed: K}.
        """
        total_converted = 0
        total_skipped = 0
        files_processed = 0

        for label_file in labels_dir.rglob("*.txt"):
            converted = self.convert_yolo_label_file(label_file, source_dataset)
            total_converted += converted
            files_processed += 1

        return {
            "converted": total_converted,
            "files_processed": files_processed,
        }
