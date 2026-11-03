"""Create scroll assets without modifying the supplied MP4. FFmpeg/ffprobe required."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "Barber_cutting_client's_hair_115145ff.mp4"
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)


def probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = checksum(MASTER)
    source = probe(MASTER)
    video = next(s for s in source["streams"] if s["codec_type"] == "video")
    if (video["width"], video["height"], video["avg_frame_rate"]) != (1280, 720, "24/1"):
        raise ValueError("Unexpected source: inspect before selecting this encoding profile")
    target = ASSETS / "ritual-scrub.webm"
    command = ["ffmpeg", "-n", "-hide_banner", "-loglevel", "warning", "-i", str(MASTER),
               "-map", "0:v:0", "-an", "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
               "-g", "6", "-keyint_min", "6", "-lag-in-frames", "0", "-auto-alt-ref", "0",
               "-deadline", "good", "-cpu-used", "2", "-row-mt", "1", "-tile-columns", "1",
               "-threads", "4", "-pix_fmt", "yuv420p", str(target)]
    if not target.exists():
        subprocess.run(command, check=True)
    poster = ASSETS / "ritual-poster.webp"
    poster_command = ["ffmpeg", "-n", "-hide_banner", "-loglevel", "error", "-ss", "7.9", "-i", str(MASTER),
                      "-frames:v", "1", "-c:v", "libwebp", "-quality", "85", "-compression_level", "6", str(poster)]
    if not poster.exists():
        subprocess.run(poster_command, check=True)
    encoded = probe(target)
    output_video = next(s for s in encoded["streams"] if s["codec_type"] == "video")
    frame_probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
                                  "-show_entries", "frame=best_effort_timestamp_time,key_frame", "-of", "json", str(target)], capture_output=True, text=True, check=True)
    frames = json.loads(frame_probe.stdout)["frames"]
    keys = [float(f["best_effort_timestamp_time"]) for f in frames if f["key_frame"]]
    if (output_video["codec_name"], output_video["width"], output_video["height"], output_video["avg_frame_rate"], len(frames)) != ("vp9", 1280, 720, "24/1", 240):
        raise ValueError("Existing derived asset differs from the inspected profile; not overwriting it")
    if len(keys) != 40 or any(abs(t - i * .25) > .001 for i, t in enumerate(keys)):
        raise ValueError("Keyframes differ from the requested 250ms strategy")
    report = {"master": {"filename": MASTER.name, "bytes": MASTER.stat().st_size, "sha256": before,
                         "width": 1280, "height": 720, "fps": 24, "videoDuration": 10, "codec": "h264 High", "audio": "AAC stereo 48kHz", "keyframeTimes": [0]},
              "webm": {"filename": target.name, "bytes": target.stat().st_size, "sha256": checksum(target),
                       "width": 1280, "height": 720, "fps": 24, "duration": float(encoded["format"]["duration"]),
                       "codec": "vp9", "audio": False, "gopFrames": 6, "keyframeIntervalSeconds": .25,
                       "keyframeTimes": keys, "frameCount": len(frames), "crf": 30},
              "poster": {"filename": poster.name, "bytes": poster.stat().st_size, "sourceTime": 7.9},
              "chapters": [{"name": "PREPARO", "start": 0, "end": 2.5}, {"name": "TÉCNICA", "start": 2.5, "end": 7.75}, {"name": "ACABAMENTO", "start": 7.75, "end": 10}],
              "command": command, "posterCommand": poster_command, "masterUnchanged": checksum(MASTER) == before}
    assert report["masterUnchanged"]
    assert not any(s["codec_type"] == "audio" for s in encoded["streams"])
    (ASSETS / "ritual-media.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"webmBytes": target.stat().st_size, "keyframes": len(keys), "posterBytes": poster.stat().st_size, "masterUnchanged": True}, indent=2))


if __name__ == "__main__":
    main()
