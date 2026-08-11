import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from deployment import prepare_serving_cache


FILES = {
    "portfolio.sqlite": b"portfolio fixture",
    "customer_detail.sqlite": b"detail fixture",
    "model_metrics.json": b'{"fixture": true}',
}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def create_bundle(path: Path, extra_file: bool = False) -> str:
    manifest = {
        "schemaVersion": 1,
        "files": {
            name: {"bytes": len(content), "sha256": sha256_bytes(content)}
            for name, content in FILES.items()
        },
    }
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, content in FILES.items():
            archive.writestr(name, content)
        archive.writestr("manifest.json", json.dumps(manifest))
        if extra_file:
            archive.writestr("unexpected.txt", "must be rejected")
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ServingBundleTests(unittest.TestCase):
    def test_downloads_and_verifies_valid_file_url_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle.zip"
            bundle_hash = create_bundle(bundle)
            target = root / "serving"
            environment = {
                "SERVING_BUNDLE_URL": bundle.as_uri(),
                "SERVING_BUNDLE_SHA256": bundle_hash,
            }
            with patch.object(prepare_serving_cache, "TARGET_DIR", target), patch.dict(
                os.environ, environment, clear=False
            ):
                prepare_serving_cache.prepare_serving_cache()
            self.assertEqual(set(path.name for path in target.iterdir()), set(FILES))
            for name, content in FILES.items():
                self.assertEqual((target / name).read_bytes(), content)

    def test_rejects_archive_with_unexpected_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle.zip"
            bundle_hash = create_bundle(bundle, extra_file=True)
            environment = {
                "SERVING_BUNDLE_URL": bundle.as_uri(),
                "SERVING_BUNDLE_SHA256": bundle_hash,
            }
            with patch.object(prepare_serving_cache, "TARGET_DIR", root / "serving"), patch.dict(
                os.environ, environment, clear=False
            ):
                with self.assertRaisesRegex(ValueError, "Unexpected serving bundle contents"):
                    prepare_serving_cache.prepare_serving_cache()

    def test_rejects_bundle_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle.zip"
            create_bundle(bundle)
            environment = {
                "SERVING_BUNDLE_URL": bundle.as_uri(),
                "SERVING_BUNDLE_SHA256": "0" * 64,
            }
            with patch.object(prepare_serving_cache, "TARGET_DIR", root / "serving"), patch.dict(
                os.environ, environment, clear=False
            ):
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    prepare_serving_cache.prepare_serving_cache()


if __name__ == "__main__":
    unittest.main()
