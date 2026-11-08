import importlib.util
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SPEC = importlib.util.spec_from_file_location("preview", Path(__file__).resolve().parents[1] / "serve.py")
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)


class PreviewServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = preview.ThreadingHTTPServer(("127.0.0.1", 0), preview.Preview)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.origin = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=2)

    def test_only_explicit_shared_assets(self):
        for path in ["/.env", "/shared/.env", "/shared/js/api.js", "/backend/app/main.py", "/api/users", "/assets/", "/shared/../.env", "/%2e%2e/.env"]:
            with self.subTest(path=path), self.assertRaises(HTTPError) as caught:
                urlopen(self.origin + path)
            self.assertEqual(caught.exception.code, 404)
            caught.exception.close()

    def test_shared_assets_are_original_bytes(self):
        asset = "js/home-motion/ritual-video.mjs"
        with urlopen(self.origin + "/shared/" + asset) as response:
            self.assertEqual(response.read(), (preview.ASSETS / asset).read_bytes())
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(response.headers["Content-Type"], "text/javascript")

    def test_video_range_for_scrubbing(self):
        asset = preview.ASSETS / "media/home/ritual-scrub.webm"
        for spec, start, end in [("bytes=120-239", 120, 239), ("bytes=-64", asset.stat().st_size - 64, asset.stat().st_size - 1)]:
            with self.subTest(range=spec), urlopen(Request(self.origin + "/shared/media/home/ritual-scrub.webm", headers={"Range": spec})) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.read(), asset.read_bytes()[start:end + 1])
                self.assertEqual(response.headers["Content-Range"], f"bytes {start}-{end}/{asset.stat().st_size}")

    def test_invalid_range_is_rejected(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.origin + "/shared/media/home/ritual-scrub.webm", headers={"Range": "bytes=99999999-"}))
        self.assertEqual(caught.exception.code, 416)
        caught.exception.close()

    def test_no_post(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.origin + "/", data=b"", method="POST"))
        self.assertEqual(caught.exception.code, 501)
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
