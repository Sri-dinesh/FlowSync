#!/usr/bin/env python3
"""
Intelligent Merge Script for FlowSync Real-World CCTV Integration
Converts multiple datasets with dynamic class mappings (Roboflow YAMLs, IDD XMLs)
into a single unified YOLOv8 dataset.
"""
import argparse
import os
import shutil
import sys
import yaml
import xml.etree.ElementTree as ET
from pathlib import Path

# Unified 7-class schema
UNIFIED_CLASSES = ["bicycle", "motorcycle", "car", "auto_rickshaw", "van", "bus", "truck"]
UNIFIED_MAP = {name: i for i, name in enumerate(UNIFIED_CLASSES)}

# Broad string mapping to unified class
STRING_MAPPING = {
    "auto": "auto_rickshaw", "autorickshaw": "auto_rickshaw", "rickshaw": "auto_rickshaw",
    "bike": "motorcycle", "motorcycle": "motorcycle", "motorbike": "motorcycle", "two-wheeler": "motorcycle",
    "car": "car", "suv": "car", "jeep": "car", "sedan": "car",
    "bus": "bus", "mini-bus": "bus",
    "truck": "truck", "lorry": "truck",
    "tempo": "van", "van": "van", "minivan": "van",
    "bicycle": "bicycle", "cycle": "bicycle",
    "vehicle": "car"  # Fallback for generic 'vehicle' labels
}

def map_string_to_unified_id(name: str) -> int:
    name_lower = name.lower()
    
    # Check exact match in broad mapping
    for key, unified_name in STRING_MAPPING.items():
        if key in name_lower:
            return UNIFIED_MAP[unified_name]
            
    # Check FGVD specific prefixes
    if name_lower.startswith('autorickshaw'): return UNIFIED_MAP['auto_rickshaw']
    if name_lower.startswith('scooter') or name_lower.startswith('motorcycle'): return UNIFIED_MAP['motorcycle']
    if name_lower.startswith('car'): return UNIFIED_MAP['car']
    if name_lower.startswith('bus') or name_lower.startswith('mini-bus'): return UNIFIED_MAP['bus']
    if name_lower.startswith('truck'): return UNIFIED_MAP['truck']
    
    return -1 # Unknown class (e.g. pedestrian, traffic light)

def merge_roboflow_dataset(dataset_dir: Path, output_dir: Path) -> int:
    # Find the data.yaml which indicates the root of the YOLO dataset
    yaml_paths = list(dataset_dir.rglob("data.yaml"))
    if not yaml_paths:
        return 0
    
    yaml_path = yaml_paths[0]
    base_dir = yaml_path.parent
        
    with open(yaml_path, 'r', encoding='utf-8', errors='ignore') as f:
        data = yaml.safe_load(f)
        
    names = data.get('names', [])
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names.keys())]
        
    # Create local_id -> unified_id map
    local_map = {}
    for i, name in enumerate(names):
        uid = map_string_to_unified_id(str(name))
        if uid != -1:
            local_map[i] = uid
            
    count = 0
    for split in ["train", "valid", "test", "val"]:
        images_dir = base_dir / split / "images"
        labels_dir = base_dir / split / "labels"
        if not images_dir.exists():
            continue
            
        out_split = "val" if split == "valid" else split
        
        for img_path in images_dir.glob("*.*"):
            if img_path.suffix.lower() not in ('.jpg', '.jpeg', '.png'): continue
            
            lbl_path = labels_dir / img_path.with_suffix(".txt").name
            if not lbl_path.exists(): continue
            
            # Read label and convert
            lines = lbl_path.read_text(encoding='utf-8').strip().splitlines()
            new_lines = []
            for line in lines:
                parts = line.split()
                if not parts: continue
                local_id = int(parts[0])
                if local_id in local_map:
                    new_lines.append(f"{local_map[local_id]} {' '.join(parts[1:])}")
                    
            if not new_lines: continue # Skip image if no valid vehicles found
            
            # Save converted label and copy image
            dest_img = output_dir / "images" / out_split / f"robo_{dataset_dir.name}_{img_path.name}"
            dest_lbl = output_dir / "labels" / out_split / dest_img.with_suffix(".txt").name
            
            shutil.copy2(img_path, dest_img)
            dest_lbl.write_text("\n".join(new_lines))
            count += 1
            
    return count

def merge_idd_fgvd(idd_dir: Path, output_dir: Path) -> int:
    """Convert IDD FGVD XMLs to YOLO and merge."""
    count = 0
    
    xml_files = list(idd_dir.rglob("*.xml"))
    if not xml_files:
        return 0
        
    import random
    random.seed(42)
    random.shuffle(xml_files)
    
    split_idx = int(len(xml_files) * 0.85)
    
    for i, xml_path in enumerate(xml_files):
        out_split = "train" if i < split_idx else "val"
        
        # In IDD_FGVD, images are in 'images' folder alongside 'annos'
        # e.g. IDD_FGVD/train/annos/0001.xml -> IDD_FGVD/train/images/0001.jpg
        img_dir = xml_path.parent.parent / "images"
        img_name = xml_path.with_suffix(".jpg").name
        img_path = img_dir / img_name
        
        if not img_path.exists(): continue
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            size = root.find("size")
            width = int(size.find("width").text)
            height = int(size.find("height").text)
            
            new_lines = []
            for obj in root.findall("object"):
                name = obj.find("name").text
                uid = map_string_to_unified_id(name)
                if uid == -1: continue
                
                bndbox = obj.find("bndbox")
                xmin = float(bndbox.find("xmin").text)
                ymin = float(bndbox.find("ymin").text)
                xmax = float(bndbox.find("xmax").text)
                ymax = float(bndbox.find("ymax").text)
                
                # Convert to YOLO format (x_center, y_center, width, height) normalized
                x_c = ((xmin + xmax) / 2) / width
                y_c = ((ymin + ymax) / 2) / height
                w = (xmax - xmin) / width
                h = (ymax - ymin) / height
                
                # Bound between 0 and 1
                x_c = max(0.0, min(1.0, x_c))
                y_c = max(0.0, min(1.0, y_c))
                w = max(0.0, min(1.0, w))
                h = max(0.0, min(1.0, h))
                
                new_lines.append(f"{uid} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}")
                
            if not new_lines: continue
            
            dest_img = output_dir / "images" / out_split / f"idd_fgvd_{img_path.name}"
            dest_lbl = output_dir / "labels" / out_split / dest_img.with_suffix(".txt").name
            
            shutil.copy2(img_path, dest_img)
            dest_lbl.write_text("\n".join(new_lines))
            count += 1
            
        except Exception as e:
            continue
            
    return count

def generate_dataset_yaml(output_dir: Path):
    yaml_content = f"""path: {output_dir.resolve()}
train: images/train
val: images/val
test: images/test
nc: {len(UNIFIED_CLASSES)}
names: {UNIFIED_CLASSES}
"""
    (output_dir / "dataset.yaml").write_text(yaml_content)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=str, default="data/raw")
    parser.add_argument("--output", type=str, default="data/processed")
    args = parser.parse_args()

    raw_dir = Path(args.raw)
    out_dir = Path(args.output)
    
    # Reset processed dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
        
    for split in ["train", "val", "test"]:
        (out_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_dir / "labels" / split).mkdir(parents=True, exist_ok=True)
        
    total = 0
    
    # 1. Merge Roboflow
    print("[Merge] Processing Roboflow datasets...")
    robo_dir = raw_dir / "roboflow"
    if robo_dir.exists():
        for d in robo_dir.iterdir():
            if d.is_dir():
                n = merge_roboflow_dataset(d, out_dir)
                print(f"  - {d.name}: {n} images")
                total += n
                
    # 2. Merge UA-DETRAC
    print("[Merge] Processing UA-DETRAC datasets...")
    ua_dir = raw_dir / "ua_detrac"
    if ua_dir.exists():
        for d in ua_dir.iterdir():
            if d.is_dir():
                n = merge_roboflow_dataset(d, out_dir)
                print(f"  - {d.name}: {n} images")
                total += n
                
    # 3. Merge IDD FGVD (XML to YOLO)
    print("[Merge] Processing IDD FGVD (XML to YOLO)...")
    idd_dir = raw_dir / "idd" / "IDD_FGVD"
    if idd_dir.exists():
        n = merge_idd_fgvd(idd_dir, out_dir)
        print(f"  - IDD_FGVD: {n} images")
        total += n
        
    generate_dataset_yaml(out_dir)
    print(f"\n[Merge] DONE! Total images prepared for training: {total}")
    print(f"[Merge] Output dataset.yaml at: {out_dir / 'dataset.yaml'}")

if __name__ == "__main__":
    main()
