"""Create the small, versioned serving bundle used by public deployments."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
SERVING_DIR = ROOT / "data" / "serving"
OUTPUT_DIR = ROOT / "deployment" / "releases"
BUNDLE_PATH = OUTPUT_DIR / "serving-cache-v1.zip"
REQUIRED_FILES = ("portfolio.sqlite", "customer_detail.sqlite", "model_metrics.json")
FIXED_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_file(archive: ZipFile, source: Path, archive_name: str) -> None:
    info = ZipInfo(archive_name, FIXED_TIMESTAMP)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    with source.open("rb") as input_handle, archive.open(info, "w") as output_handle:
        shutil.copyfileobj(input_handle, output_handle, length=1024 * 1024)


def main() -> None:
    missing = [name for name in REQUIRED_FILES if not (SERVING_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Serving cache is incomplete: {', '.join(missing)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": 1,
        "files": {
            name: {
                "bytes": (SERVING_DIR / name).stat().st_size,
                "sha256": sha256(SERVING_DIR / name),
            }
            for name in REQUIRED_FILES
        },
    }

    with ZipFile(BUNDLE_PATH, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name in REQUIRED_FILES:
            add_file(archive, SERVING_DIR / name, name)
        manifest_info = ZipInfo("manifest.json", FIXED_TIMESTAMP)
        manifest_info.compress_type = ZIP_DEFLATED
        manifest_info.external_attr = 0o100644 << 16
        archive.writestr(manifest_info, json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    bundle_hash = sha256(BUNDLE_PATH)
    checksum_path = BUNDLE_PATH.with_suffix(BUNDLE_PATH.suffix + ".sha256")
    checksum_path.write_text(f"{bundle_hash}  {BUNDLE_PATH.name}\n", encoding="ascii")
    print(f"Created {BUNDLE_PATH} ({BUNDLE_PATH.stat().st_size / 1024 / 1024:.1f} MiB)")
    print(f"SHA-256: {bundle_hash}")


if __name__ == "__main__":
    main()
