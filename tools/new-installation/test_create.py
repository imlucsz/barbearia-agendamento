import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("create.py")
SPEC = importlib.util.spec_from_file_location("installation_creator", MODULE_PATH)
creator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creator)


class InstallationScaffoldTests(unittest.TestCase):
    def make_core(self, root: Path) -> Path:
        (root / "backend" / "app").mkdir(parents=True)
        (root / "backend" / "app" / "main.py").write_text("core", encoding="utf-8")
        (root / "frontend" / "assets" / "js").mkdir(parents=True)
        (root / "frontend" / "assets" / "js" / "installation-config.mjs").write_text("old config", encoding="utf-8")
        (root / "frontend" / "assets" / "css").mkdir(parents=True)
        (root / "frontend" / "assets" / "css" / "installation.css").write_text("tokens", encoding="utf-8")
        (root / "frontend" / "assets" / "branding").mkdir(parents=True)
        (root / "frontend" / "assets" / "branding" / "old-logo.webp").write_bytes(b"old-installation-logo")
        (root / "backend" / ".env.example").write_text("SECRET_KEY=accidental-source-secret\n", encoding="utf-8")
        (root / "backend" / ".env").write_text("SECRET_KEY=private-source-secret\n", encoding="utf-8")
        (root / "backend" / "barbearia.db").write_bytes(b"old-installation-database")
        (root / "exports").mkdir()
        (root / "exports" / "clients.csv").write_text("private", encoding="utf-8")
        return root

    def test_scaffold_creates_new_env_and_config_without_source_data(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = self.make_core(temp_path / "core")
            target = temp_path / "new-shop"
            creator.create_installation(str(target), "Barbearia do Bairro", "https://api.bairro.example", source)

            env = (target / "backend" / ".env").read_text(encoding="utf-8")
            config = (target / "frontend" / "assets" / "js" / "installation-config.mjs").read_text(encoding="utf-8")
            self.assertIn("SECRET_KEY=\n", env)
            self.assertIn('INSTALLATION_NAME="Barbearia do Bairro"', env)
            self.assertNotIn("source-secret", env)
            self.assertIn('"Barbearia do Bairro"', config)
            self.assertIn('"https://api.bairro.example"', config)
            self.assertFalse((target / "backend" / "barbearia.db").exists())
            self.assertNotIn("accidental-source-secret", (target / "backend" / ".env.example").read_text(encoding="utf-8"))
            self.assertFalse((target / "frontend" / "assets" / "branding" / "old-logo.webp").exists())
            self.assertFalse((target / "exports").exists())
            self.assertTrue((target / "INSTALLATION_CHECKLIST.md").is_file())

    def test_existing_target_or_non_https_api_is_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = self.make_core(temp_path / "core")
            target = temp_path / "existing"
            target.mkdir()
            with self.assertRaisesRegex(ValueError, "must not exist"):
                creator.create_installation(str(target), "Shop", "https://api.example", source)
            with self.assertRaisesRegex(ValueError, "HTTPS origin"):
                creator.create_installation(str(temp_path / "another"), "Shop", "http://api.example", source)
            self.assertFalse((temp_path / "another").exists())


if __name__ == "__main__":
    unittest.main()
