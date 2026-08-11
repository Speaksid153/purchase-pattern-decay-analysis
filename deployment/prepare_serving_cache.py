"""Download and verify the deployment serving cache before the API starts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = ROOT / "data" / "serving"
REQUIRED_FILES = frozenset(("portfolio.sqlite", "customer_detail.sqlite", "model_metrics.json"))
ALLOWED_ARCHIVE_FILES = REQUIRED_FILES | {"manifest.json"}
MAX_BUNDLE_BYTES = 512 * 1024 * 1024
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cache_exists() -> bool:
    return all((TARGET_DIR / name).is_file() for name in REQUIRED_FILES)


def _download(url: str, destination: Path) -> None:
    parsed = urllib.parse.urlparse(url)
    is_local = parsed.scheme == "file"
    is_loopback = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    if parsed.scheme != "https" and not is_local and not is_loopback:
        raise ValueError("SERVING_BUNDLE_URL must use HTTPS (file:// and loopback HTTP are allowed for tests)")

    request = urllib.request.Request(url, headers={"User-Agent": "purchase-pattern-analysis/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        declared_size = response.headers.get("Content-Length")
        if declared_size and int(declared_size) > MAX_BUNDLE_BYTES:
            raise ValueError("Serving bundle exceeds the 512 MiB safety limit")
        copied = 0
        while chunk := response.read(1024 * 1024):
            copied += len(chunk)
            if copied > MAX_BUNDLE_BYTES:
                raise ValueError("Serving bundle exceeds the 512 MiB safety limit")
            output.write(chunk)


def _extract_verified(bundle: Path, destination: Path) -> None:
    try:
        with ZipFile(bundle) as archive:
            names = set(archive.namelist())
            if names != ALLOWED_ARCHIVE_FILES:
                raise ValueError(f"Unexpected serving bundle contents: {sorted(names)}")
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("schemaVersion") != 1 or set(manifest.get("files", {})) != REQUIRED_FILES:
                raise ValueError("Serving bundle manifest has an unsupported schema")

            destination.mkdir(parents=True, exist_ok=True)
            for name in REQUIRED_FILES:
                metadata = manifest["files"][name]
                expected_hash = str(metadata.get("sha256", "")).lower()
                expected_bytes = metadata.get("bytes")
                if not SHA256_PATTERN.fullmatch(expected_hash) or not isinstance(expected_bytes, int):
                    raise ValueError(f"Invalid manifest metadata for {name}")
                target = destination / name
                with archive.open(name) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                if target.stat().st_size != expected_bytes or _sha256(target) != expected_hash:
                    raise ValueError(f"Serving bundle file failed verification: {name}")
    except BadZipFile as error:
        raise ValueError("Serving bundle is not a valid ZIP archive") from error


def _install_verified(source_directory: Path) -> None:
    """Atomically install verified files without crossing filesystem boundaries."""
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_FILES:
        staging_file = tempfile.NamedTemporaryFile(
            dir=TARGET_DIR,
            prefix=f".{name}.",
            suffix=".tmp",
            delete=False,
        )
        staging_path = Path(staging_file.name)
        try:
            with staging_file, (source_directory / name).open("rb") as source:
                shutil.copyfileobj(source, staging_file, length=1024 * 1024)
                staging_file.flush()
                os.fsync(staging_file.fileno())
            os.replace(staging_path, TARGET_DIR / name)
        finally:
            staging_path.unlink(missing_ok=True)


def prepare_serving_cache() -> None:
    if _cache_exists():
        print("Using serving cache already present in the image or mounted filesystem", flush=True)
        return

    url = os.getenv("SERVING_BUNDLE_URL", "").strip()
    expected_hash = os.getenv("SERVING_BUNDLE_SHA256", "").strip().lower()
    if not url:
        raise RuntimeError("Serving cache is absent and SERVING_BUNDLE_URL is not configured")
    if not SHA256_PATTERN.fullmatch(expected_hash):
        raise RuntimeError("SERVING_BUNDLE_SHA256 must be the bundle's 64-character SHA-256")

    with tempfile.TemporaryDirectory(prefix="serving-cache-") as temp_directory:
        temp_root = Path(temp_directory)
        bundle = temp_root / "serving-cache.zip"
        extracted = temp_root / "verified"
        print("Downloading versioned serving cache", flush=True)
        _download(url, bundle)
        actual_hash = _sha256(bundle)
        if actual_hash != expected_hash:
            raise ValueError(f"Serving bundle SHA-256 mismatch: expected {expected_hash}, received {actual_hash}")
        _extract_verified(bundle, extracted)

        _install_verified(extracted)
    print("Serving cache downloaded and verified", flush=True)
