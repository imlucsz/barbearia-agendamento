"""Loopback-only visual preview; serves prototypes and explicit existing assets.

No API, environment loading, database or directory listing. Run from any cwd:
    python prototypes/part2/serve.py
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

PROTOTYPES = Path(__file__).resolve().parent
PROJECT = PROTOTYPES.parents[1]
ASSETS = PROJECT / "frontend/assets"
THREE_CANDIDATES = [PROJECT / "frontend/e2e/motion-lab/node_modules/three/build"]
if PROJECT.parent.name == ".worktrees":
    THREE_CANDIDATES.append(PROJECT.parent.parent / "frontend/e2e/motion-lab/node_modules/three/build")
THREE = next((path for path in THREE_CANDIDATES if (path / "three.module.js").is_file()), None)
SHARED = {
    "css/installation.css", "css/home-ritual.css",
    "js/vendor/gsap/gsap.min.js", "js/vendor/gsap/ScrollTrigger.min.js",
    "js/home-motion/assets.mjs", "js/home-motion/runtime.mjs",
    "js/home-motion/ritual-video.mjs", "js/home-motion/video-seek.mjs",
    "js/estrelinha/cinematic.mjs", "js/estrelinha/itens-barbeiro.js",
    "js/estrelinha/pets/especies.js", "js/estrelinha/pets/malha.js",
    "js/estrelinha/pets/voxel.js", "js/estrelinha/pets/logo.js",
    "images/navalha-recortada.png", "media/home/ritual-poster.webp", "media/home/ritual-scrub.webm",
}


def resolve_asset(url):
    path = unquote(urlsplit(url).path)
    parts = path.strip("/").split("/")
    if any(part in {"..", "."} for part in parts) or "\\" in path:
        return None
    if path.startswith("/shared/vendor/three/"):
        name = path.removeprefix("/shared/vendor/three/")
        return THREE / name if THREE and name in {"three.module.js", "three.core.js"} else None
    if path.startswith("/shared/"):
        name = path.removeprefix("/shared/")
        return ASSETS / name if name in SHARED else None
    target = (PROTOTYPES / path.lstrip("/")).resolve()
    if not target.is_relative_to(PROTOTYPES):
        return None
    if path == "/":
        return PROTOTYPES / "index.html"
    return target if target.is_file() and target.suffix in {".html", ".css", ".js", ".mjs", ".png", ".webp", ".ttf", ".md", ".txt"} else None


class Preview(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".js": "text/javascript", ".webm": "video/webm"}

    def translate_path(self, path):
        return str(resolve_asset(path) or PROTOTYPES / "__not_found__")

    def list_directory(self, path):
        self.send_error(404)
        return None

    def send_head(self):
        target = resolve_asset(self.path)
        if not target or not target.is_file():
            self.send_error(404)
            return None
        # Seeking the existing WebM needs byte ranges, as on the real asset server.
        size = target.stat().st_size
        requested = self.headers.get("Range")
        start, end = 0, size - 1
        if requested:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested)
            if not match or not any(match.groups()):
                self.send_error(416)
                return None
            first, last = match.groups()
            start = int(first) if first else max(0, size - int(last))
            end = min(int(last), size - 1) if first and last else size - 1
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
        source = target.open("rb")
        source.seek(start)
        self._remaining = end - start + 1
        self.send_response(206 if requested else 200)
        self.send_header("Content-Type", self.guess_type(str(target)))
        self.send_header("Content-Length", str(self._remaining))
        self.send_header("Accept-Ranges", "bytes")
        if requested:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        return source

    def copyfile(self, source, outputfile):
        while self._remaining > 0:
            chunk = source.read(min(65536, self._remaining))
            if not chunk:
                break
            try:
                outputfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                break
            self._remaining -= len(chunk)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print("Prévia local: http://127.0.0.1:4194/ — Ctrl+C encerra", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 4194), Preview).serve_forever()
