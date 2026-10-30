import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import backup


class BackupFilesystemTests(unittest.TestCase):
    def test_retention_removes_only_old_direct_children_with_exact_backup_pattern(self):
        now = datetime.now(timezone.utc)
        old_stamp = (now - timedelta(days=31)).strftime("%Y%m%dT%H%M%SZ")
        new_stamp = (now - timedelta(days=2)).strftime("%Y%m%dT%H%M%SZ")
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            old_stem = f"barbearia-postgres-{old_stamp}-a1b2c3d4"
            new_stem = f"barbearia-postgres-{new_stamp}-a1b2c3d4"
            old_files = [directory / f"{old_stem}.dump.age", directory / f"{old_stem}.sha256", directory / f"{old_stem}.manifest.json"]
            for path in old_files:
                path.write_text("fixture", encoding="utf-8")
            recent = directory / f"{new_stem}.dump.age"
            recent.write_text("fixture", encoding="utf-8")
            malformed = directory / f"{old_stem}.dump.age.extra"
            malformed.write_text("keep", encoding="utf-8")
            orphan = directory / f"barbearia-postgres-{old_stamp}-deadbeef.manifest.json"
            orphan.write_text("old sidecar only", encoding="utf-8")
            nested = directory / "nested"
            nested.mkdir()
            (nested / f"{old_stem}.dump.age").write_text("keep", encoding="utf-8")

            with patch.dict(os.environ, {"BACKUP_RETENTION_DAYS": "30"}):
                backup.prune(directory)

            self.assertTrue(all(not path.exists() for path in old_files))
            self.assertFalse(orphan.exists())
            self.assertTrue(recent.exists())
            self.assertTrue(malformed.exists())
            self.assertTrue((nested / f"{old_stem}.dump.age").exists())

    def test_latest_backup_requires_matching_checksum_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            content = b"fictional encrypted dump bytes"
            backup_path = directory / "barbearia-postgres-20261001T120000Z-abcdef12.dump.age"
            backup_path.write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            backup.write_private(directory / "barbearia-postgres-20261001T120000Z-abcdef12.sha256", f"{digest}  {backup_path.name}\n")
            manifest = {
                "format": "postgresql-custom-age-v1",
                "backup_file": backup_path.name,
                "sha256": digest,
                "alembic_revision": "fictional_revision",
                "table_counts": {"public.alembic_version": 1},
            }
            backup.write_private(directory / "barbearia-postgres-20261001T120000Z-abcdef12.manifest.json", json.dumps(manifest))

            restored_path, _, restored_manifest = backup.latest_backup(directory)

            self.assertEqual(restored_path, backup_path)
            self.assertEqual(restored_manifest, manifest)

    def test_latest_corrupt_backup_fails_closed_instead_of_using_older_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            old = directory / "barbearia-postgres-20260901T120000Z-abcdef12.dump.age"
            old.write_bytes(b"old")
            latest = directory / "barbearia-postgres-20261001T120000Z-abcdef12.dump.age"
            latest.write_bytes(b"latest")

            with self.assertRaisesRegex(RuntimeError, "refusing to fall back"):
                backup.latest_backup(directory)


if __name__ == "__main__":
    unittest.main()
