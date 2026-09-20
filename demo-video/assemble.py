"""Assemble the final local MP4 from finished, correctly timed scene clips.

No source collection, API writes, stock footage, generated findings, or implicit
looping. Each edit.json asset must be a completed clip of sufficient duration.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"


def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ]))


def inspect_plan(plan):
    missing = []
    cursor = 0
    for scene in plan["scenes"]:
        if scene["start"] != cursor or scene["end"] <= cursor:
            raise ValueError(f"Timeline gap or overlap at {scene['id']}")
        cursor = scene["end"]
        asset = scene.get("asset")
        if not asset or not (ROOT / asset).is_file():
            missing.append(scene["id"])
            continue
        details = probe(ROOT / asset)
        if not any(s["codec_type"] == "video" for s in details["streams"]):
            raise ValueError(f"{scene['id']}: render this source into a scene clip first")
        required = scene["end"] - scene["start"] + scene.get("in_seconds", 0)
        if float(details["format"]["duration"]) < required - 1 / plan["fps"]:
            raise ValueError(f"{scene['id']}: clip too short; extend its edit explicitly")
    if cursor != plan["duration_seconds"] or cursor != 120:
        raise ValueError("The final timeline must be exactly 120 seconds")
    return missing


def assemble(plan, narration=None, music=None):
    missing = inspect_plan(plan)
    if missing:
        raise SystemExit("Awaiting finished scene clips: " + ", ".join(missing))
    OUT.mkdir(exist_ok=True)
    intermediates = OUT / "scenes"
    intermediates.mkdir(exist_ok=True)
    width, height, fps = plan["width"], plan["height"], plan["fps"]
    clips = []
    for i, scene in enumerate(plan["scenes"]):
        clip = intermediates / f"{i:02d}.mp4"
        duration = scene["end"] - scene["start"]
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(scene.get("in_seconds", 0)), "-i", str(ROOT / scene["asset"]),
            "-t", str(duration), "-an", "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x0a0a0a,setsar=1,fps={fps}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            str(clip),
        ], check=True)
        clips.append(clip)
    concat = intermediates / "concat.txt"
    concat.write_text("".join(f"file '{clip.name}'\n" for clip in clips))
    picture = OUT / "kingdom-picture.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "1",
        "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(picture),
    ], check=True)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(picture)]
    tracks = []
    for path in (narration, music):
        if path:
            command.extend(["-i", str(path)])
            tracks.append(path)
    target = OUT / "kingdom-demo.mp4"
    if tracks:
        filters = []
        for i, path in enumerate(tracks, 1):
            gain = 1 if narration and path == narration else 0.18
            filters.append(f"[{i}:a]aresample=48000,volume={gain},apad[a{i}]")
        labels = "".join(f"[a{i}]" for i in range(1, len(tracks) + 1))
        filters.append(f"{labels}amix=inputs={len(tracks)}:normalize=0,"
                       "alimiter=limit=0.89:level=0,atrim=duration=120[audio]")
        command.extend(["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[audio]",
                        "-c:a", "aac", "-b:a", "192k"])
    else:
        command.extend(["-an"])
    command.extend(["-c:v", "copy", "-t", "120", "-movflags", "+faststart", str(target)])
    subprocess.run(command, check=True)
    metadata = probe(target)
    video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    assert video["width"] == width and video["height"] == height
    assert int(video["nb_frames"]) == 120 * fps
    assert abs(float(metadata["format"]["duration"]) - 120) < 0.08
    (OUT / "final-verification.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Verified {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--narration", type=Path)
    parser.add_argument("--music", type=Path)
    args = parser.parse_args()
    plan = json.loads((ROOT / "edit.json").read_text())
    if not args.render:
        print(json.dumps({"duration_seconds": 120, "missing_clips": inspect_plan(plan)}))
        return
    assemble(plan, args.narration, args.music)


if __name__ == "__main__":
    main()
