import os
import sys
import json
import hashlib
from pathlib import Path
from collections import defaultdict
from PIL import Image

def audit_plantvillage_dataset(dataset_dir="plantvillage dataset/color", output_report="ml/artifacts/dataset_audit_report.json"):
    root = Path(dataset_dir).resolve()
    print(f"[Dataset Audit] Auditing: {root}")
    if not root.exists():
        raise FileNotFoundError(f"Dataset root does not exist: {root}")

    class_dirs = sorted([d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")])
    print(f"[Dataset Audit] Found {len(class_dirs)} class directories.")

    stats = {
        "dataset_path": str(root),
        "total_classes": len(class_dirs),
        "total_images": 0,
        "format_counts": {},
        "corrupted_files": [],
        "empty_classes": [],
        "classes": {},
        "duplicate_hash_count": 0,
    }

    seen_hashes = {}
    duplicates = []
    format_counts = defaultdict(int)

    for c_dir in class_dirs:
        class_name = c_dir.name
        img_files = [f for f in c_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
        
        if len(img_files) == 0:
            stats["empty_classes"].append(class_name)

        valid_count = 0
        formats = defaultdict(int)

        for img_path in img_files:
            ext = img_path.suffix.lower()
            formats[ext] += 1
            format_counts[ext] += 1

            # Validate readability
            try:
                with Image.open(img_path) as img:
                    img.verify()
                # Compute md5 of file to detect bitwise duplicates
                with open(img_path, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                if file_hash in seen_hashes:
                    duplicates.append((str(img_path), seen_hashes[file_hash]))
                else:
                    seen_hashes[file_hash] = str(img_path)

                valid_count += 1
            except Exception as e:
                stats["corrupted_files"].append({
                    "file": str(img_path),
                    "error": str(e)
                })

        stats["classes"][class_name] = {
            "total_images": len(img_files),
            "valid_images": valid_count,
            "formats": dict(formats)
        }
        stats["total_images"] += valid_count

    stats["duplicate_hash_count"] = len(duplicates)
    stats["format_counts"] = dict(format_counts)

    os.makedirs(os.path.dirname(output_report), exist_ok=True)
    with open(output_report, "w") as f:
        json.dump(stats, f, indent=2)

    print("\n" + "="*60)
    print("           PLANTVILLAGE DATASET AUDIT SUMMARY")
    print("="*60)
    print(f" Dataset Path:      {stats['dataset_path']}")
    print(f" Total Classes:     {stats['total_classes']}")
    print(f" Total Images:      {stats['total_images']}")
    print(f" Formats Found:     {stats['format_counts']}")
    print(f" Corrupted Images:  {len(stats['corrupted_files'])}")
    print(f" Empty Classes:     {len(stats['empty_classes'])}")
    print(f" Identical Hashes:  {stats['duplicate_hash_count']}")
    print("="*60)
    print(f"Audit report saved to: {output_report}")

    return stats

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "plantvillage dataset/color"
    audit_plantvillage_dataset(path)
