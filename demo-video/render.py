"""Deterministic local motion graphics. No network or Kingdom API calls.

Preview: real UI captures plus editorial type/camera/cursor choreography.
Final: accepts approved media clips through edit.json and refuses missing scenes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = ROOT / "output"
W, H, FPS = 1920, 1080, 30
DURATION = 30
INK = (246, 246, 243)
MUTED = (140, 142, 145)
PANEL = (176, 156, 1568, 882)
CUTS = [0, 4.2, 9, 16.6, 23.4, 26.2, 30]
QUESTION = "What can public data tell us about the world?"


def clamp(x):
    return max(0.0, min(1.0, x))


def ease(x):
    x = clamp(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def mix(a, b, t):
    return a + (b - a) * t


def between(a, b, t):
    return tuple(mix(x, y, t) for x, y in zip(a, b, strict=True))


def prepare_fonts():
    for name in ("geist", "geist-mono"):
        source = ASSETS / "fonts" / f"{name}.woff2"
        for weight in (400, 500, 600):
            target = ASSETS / "fonts" / f"{name}-{weight}.ttf"
            if not target.exists():
                font = TTFont(source)
                font.flavor = None
                instantiateVariableFont(font, {"wght": weight}, inplace=True)
                font.save(target)


@lru_cache(maxsize=200)
def font(size, weight=500, mono=False):
    name = "geist-mono" if mono else "geist"
    return ImageFont.truetype(str(ASSETS / "fonts" / f"{name}-{weight}.ttf"), size)


@lru_cache(maxsize=600)
def lettering(text, size, weight=500, color=INK, mono=False):
    f = font(size, weight, mono)
    box = f.getbbox(text or " ")
    layer = Image.new("RGBA", (max(1, math.ceil(f.getlength(text)) + 8), size * 2))
    ImageDraw.Draw(layer).text((0, -box[1]), text, font=f, fill=(*color, 255))
    return layer.crop((0, 0, layer.width, max(1, box[3] - box[1] + 3)))


def put_text(canvas, text, x, y, size, weight=500, color=INK, opacity=1, mono=False):
    layer = lettering(text, size, weight, color, mono)
    if opacity < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda a: int(a * clamp(opacity))))
    canvas.paste(layer, (round(x), round(y)), layer)
    return layer.width


@lru_cache(maxsize=1)
def backdrop():
    yy, xx = np.mgrid[0:H, 0:W]
    glow = np.exp(-(((xx - 1060) / 1100) ** 2 + ((yy - 470) / 680) ** 2))
    pixels = np.repeat((8 + 9 * glow).astype(np.uint8)[..., None], 3, axis=2)
    canvas = Image.fromarray(pixels)
    draw = ImageDraw.Draw(canvas)
    for x in range(48, W, 64):
        for y in range(48, H, 64):
            draw.point((x, y), fill=(33, 33, 33))
    return canvas


def castle(canvas, x, y, size, color=INK):
    # Same silhouette as the app's web/public/castle.svg.
    s = size / 16
    points = [(1, 2), (4, 2), (4, 4), (6, 4), (6, 2), (10, 2), (10, 4),
              (12, 4), (12, 2), (15, 2), (15, 15), (10, 15), (10, 11),
              (9.7, 10), (9, 9.3), (8, 9), (7, 9.3), (6.3, 10), (6, 11),
              (6, 15), (1, 15)]
    ImageDraw.Draw(canvas).polygon([(x + px * s, y + py * s) for px, py in points], fill=color)


def chrome(canvas, t, chapter):
    castle(canvas, 72, 51, 30)
    put_text(canvas, "kingdom", 118, 51, 28, weight=500)
    label = f"MOTION STUDY  /  {chapter}"
    width = lettering(label, 17, 400, MUTED, True).width
    put_text(canvas, label, W - 72 - width, 58, 17, 400, MUTED, mono=True)
    ImageDraw.Draw(canvas).line((72, 101, W - 72, 101), fill=(44, 44, 44), width=1)
    ImageDraw.Draw(canvas).line((72, H - 28, 72 + (W - 144) * t / DURATION, H - 28),
                               fill=(112, 112, 112), width=2)


@lru_cache(maxsize=12)
def source(name):
    return Image.open(ASSETS / name).convert("RGB")


@lru_cache(maxsize=1)
def panel_mask():
    mask = Image.new("L", PANEL[2:])
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, PANEL[2] - 1, PANEL[3] - 1), radius=18, fill=255)
    return mask


def screen(canvas, name, rect, alpha=1):
    x, y, width, height = rect
    px, py, pw, ph = PANEL
    image = source(name).transform((pw, ph), Image.Transform.AFFINE,
                                   (width / pw, 0, x, 0, height / ph, y),
                                   resample=Image.Resampling.BICUBIC)
    mask = panel_mask()
    if alpha < 1:
        mask = mask.point(lambda a: int(a * alpha))
    canvas.paste(image, (px, py), mask)
    ImageDraw.Draw(canvas).rounded_rectangle((px, py, px + pw, py + ph), radius=18,
                                             outline=(68, 68, 68), width=1)


def project(point, rect):
    x, y, width, height = rect
    px, py, pw, ph = PANEL
    return px + (point[0] - x) * pw / width, py + (point[1] - y) * ph / height


def cursor(canvas, point, click_age=None, alpha=1):
    x, y = point
    layer = Image.new("RGBA", canvas.size)
    draw = ImageDraw.Draw(layer)
    if click_age is not None and 0 <= click_age <= 0.6:
        phase = click_age / 0.6
        r = 12 + 42 * ease(phase)
        draw.ellipse((x - r, y - r, x + r, y + r),
                     outline=(30, 30, 30, int(180 * (1 - phase))), width=3)
        r2 = 7 + 22 * ease(phase)
        draw.ellipse((x - r2, y - r2, x + r2, y + r2),
                     fill=(240, 240, 240, int(130 * (1 - phase))))
    points = [(0, 0), (0, 35), (9, 27), (16, 42), (23, 39), (16, 24), (29, 24)]
    draw.polygon([(x + dx + 2, y + dy + 4) for dx, dy in points], fill=(0, 0, 0, 55))
    polygon = [(x + dx, y + dy) for dx, dy in points]
    draw.polygon(polygon, fill=(255, 255, 255, int(255 * alpha)))
    draw.line(polygon + [polygon[0]], fill=(10, 10, 10, int(255 * alpha)), width=2, joint="curve")
    canvas.paste(layer, (0, 0), layer)


def reveal_line(canvas, text, x, y, size, t, delay, color=INK):
    p = ease((t - delay) / 0.7)
    put_text(canvas, text, x, y + 62 * (1 - p), size, color=color, opacity=p)


def scene(index, t):
    canvas = backdrop().copy()
    if index == 0:
        chrome(canvas, t, "01")
        drift = ease(t / 4.2)
        put_text(canvas, "EVERY INVESTIGATION STARTS SOMEWHERE", 148, 282, 21,
                 400, MUTED, mono=True, opacity=ease(t / 0.65))
        reveal_line(canvas, "A question worth", 140 - 12 * drift, 376, 133, t, 0.2)
        reveal_line(canvas, "looking into.", 140 - 12 * drift, 530, 133, t, 0.55)
        line = ease((t - 1.35) / 0.75)
        ImageDraw.Draw(canvas).line((148, 701, 148 + 775 * line, 701), fill=(225, 225, 220), width=3)
        put_text(canvas, "Start with curiosity.", 148, 790, 30, 400, MUTED,
                 opacity=ease((t - 1.6) / 0.65))
    elif index == 1:
        chrome(canvas, t, "02")
        local = t - CUTS[1]
        put_text(canvas, "ASK IN PLAIN LANGUAGE", 148, 266, 21, 400, MUTED, mono=True)
        f = font(152, 500)
        n_float = clamp((local - 0.3) / 3.55) * len(QUESTION)
        n = int(n_float)
        visible = QUESTION[:n]
        previous = f.getlength(visible)
        next_length = f.getlength(QUESTION[: min(n + 1, len(QUESTION))])
        advance = mix(previous, next_length, n_float - n)
        camera = max(0, advance - 1440)
        put_text(canvas, visible, 148 - camera, 443, 152)
        if local < 4.1 or int(t * 3) % 2:
            xx = 156 + advance - camera
            ImageDraw.Draw(canvas).rectangle((xx, 430, xx + 3, 604), fill=INK)
        put_text(canvas, "One question. A place to begin.", 148, 765, 30, 400, MUTED)
        # Side masks leave deliberate, clean cinematic edges as the camera tracks.
        canvas.paste(backdrop().crop((0, 360, 100, 660)), (0, 360))
        canvas.paste(backdrop().crop((1830, 360, 1920, 660)), (1830, 360))
    elif index == 2:
        chrome(canvas, t, "03")
        rect = between((365, 70, 800, 450), (0, 0, 1280, 720), ease((t - 12.6) / 2.5))
        screen(canvas, "home-question.png", rect)
        if t > 14.4:
            position = between((810, 385), (85, 692), ease((t - 14.4) / 1.8))
            cursor(canvas, project(position, rect), t - 16.24)
    elif index == 3:
        chrome(canvas, t, "04")
        rect = between((0, 0, 1280, 720), (300, 62, 960, 540), ease((t - 20.1) / 2.3))
        screen(canvas, "datasets-list.png" if t >= 19.86 else "datasets-cards.png", rect)
        position = between((85, 692), (1014.7, 112), ease((t - 17.0) / 2.55))
        cursor(canvas, project(position, rect), t - 19.7,
               alpha=1 - ease((t - 21.8) / 0.7))
    elif index == 4:
        chrome(canvas, t, "05")
        local = t - CUTS[4]
        words = ["Investigate.", "Verify.", "Explore."]
        index2 = min(2, int(local / 0.83))
        phase = local - index2 * 0.83
        y = 455 + 70 * (1 - ease(phase / 0.35))
        word = words[index2]
        ww = lettering(word, 158).width
        put_text(canvas, word, (W - ww) / 2, y, 158, opacity=ease(phase / 0.2))
        put_text(canvas, "FROM QUESTION TO UNDERSTANDING", 630, 712, 19, 400, MUTED, mono=True)
    else:
        chrome(canvas, t, "06")
        local = t - CUTS[5]
        p = ease(local / 0.85)
        castle(canvas, 405, 402 + 30 * (1 - p), 146)
        put_text(canvas, "kingdom", 588, 400 + 30 * (1 - p), 168, opacity=p)
        width = lettering("Ask. Investigate. Discover.", 38, 400, MUTED).width
        put_text(canvas, "Ask. Investigate. Discover.", (W - width) / 2, 654, 38,
                 400, MUTED, opacity=ease((local - 0.45) / 0.75))
        text = "STYLE PREVIEW  /  RESEARCH SCENES TO FOLLOW"
        width = lettering(text, 18, 400, MUTED, True).width
        put_text(canvas, text, (W - width) / 2, 850, 18, 400, MUTED, mono=True,
                 opacity=ease((local - 1.1) / 0.5))
    return canvas


def preview_frame(t):
    index = next((i for i in range(len(CUTS) - 1) if CUTS[i] <= t < CUTS[i + 1]), 5)
    canvas = scene(index, t)
    if index and t - CUTS[index] < 0.2:
        before = scene(index - 1, CUTS[index] - 0.001)
        canvas = Image.blend(before, canvas, ease((t - CUTS[index]) / 0.2))
    if t < 0.4:
        canvas = Image.blend(Image.new("RGB", (W, H)), canvas, ease(t / 0.4))
    if t > 29.45:
        canvas = Image.blend(canvas, Image.new("RGB", (W, H)), ease((t - 29.45) / 0.55))
    return canvas


def soundtrack():
    """Original synthesized bed and interface accents; no downloaded music."""
    sr = 48000
    t = np.arange(sr * DURATION, dtype=np.float64) / sr
    left = np.zeros_like(t)
    right = np.zeros_like(t)
    fade = np.minimum(np.clip(t / 2, 0, 1), np.clip((DURATION - t) / 1.2, 0, 1))
    for frequency, level in [(55, 0.027), (110, 0.017), (164.8138, 0.009), (220, 0.004)]:
        env = (0.74 + 0.26 * np.sin(2 * np.pi * 0.13 * t)) * fade
        left += level * env * np.sin(2 * np.pi * frequency * t)
        right += level * env * np.sin(2 * np.pi * (frequency + 0.12) * t)
    for beat in np.arange(0.65, 29, 0.625):
        offset = int(beat * sr)
        tt = np.arange(int(0.22 * sr)) / sr
        pulse = 0.035 * np.exp(-tt * 23) * np.sin(2 * np.pi * (70 * tt - 40 * tt * tt))
        left[offset:offset + len(tt)] += pulse
        right[offset:offset + len(tt)] += pulse
    rng = np.random.default_rng(7331)
    for start, strength in [(16.24, 0.17), (19.7, 0.17)] + [
        (4.5 + i * 3.55 / len(QUESTION), 0.038) for i in range(len(QUESTION))
    ]:
        offset = int(start * sr)
        tt = np.arange(int(0.045 * sr)) / sr
        tick = strength * np.exp(-tt * 145) * (
            0.65 * np.sin(2 * np.pi * 1850 * tt) + 0.35 * rng.normal(0, 0.7, len(tt))
        )
        left[offset:offset + len(tt)] += tick
        right[offset:offset + len(tt)] += tick
    stereo = np.stack([left, right], axis=1) * fade[:, None]
    audio = np.clip(stereo * 32767, -32767, 32767).astype("<i2")
    path = OUT / "preview-soundtrack.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(audio.tobytes())
    return path


def preflight(final=False):
    edit = json.loads((ROOT / "edit.json").read_text())
    assert edit["duration_seconds"] == 120
    end = 0
    missing = []
    for item in edit["scenes"]:
        assert item["start"] == end and item["end"] > item["start"]
        end = item["end"]
        if item["required"] and not item["asset"]:
            missing.append(item["id"])
        if item["asset"] and not (ROOT / item["asset"]).is_file():
            missing.append(item["id"])
    assert end == edit["duration_seconds"]
    for path in ("home-question.png", "datasets-cards.png", "datasets-list.png",
                 "fonts/geist.woff2", "fonts/geist-mono.woff2"):
        if not (ASSETS / path).is_file():
            raise SystemExit(f"Missing preview asset: {path}")
    print(json.dumps({"preview_ready": True, "final_missing_scenes": missing,
                      "duration_seconds": end, "network_calls": 0}))
    if final and missing:
        raise SystemExit("Final render blocked: completed mission footage is required.")
    return edit


def contact_sheet():
    times = [1.6, 3.4, 5.9, 8.2, 10.6, 14.5, 16.3, 18.3, 20.2, 22.2, 25.3, 28.3]
    sheet = Image.new("RGB", (1440, 928), (20, 20, 20))
    for n, t in enumerate(times):
        image = preview_frame(t).resize((480, 270), Image.Resampling.LANCZOS)
        x, y = (n % 3) * 480, (n // 3) * 232
        image = image.resize((400, 225), Image.Resampling.LANCZOS)
        sheet.paste(image, (x + 40, y))
        ImageDraw.Draw(sheet).text((x + 45, y + 5), f"{t:04.1f}s", fill=INK, font=font(15, 400))
    sheet.save(OUT / "contact-sheet.jpg", quality=94)
    preview_frame(10.6).save(OUT / "poster.jpg", quality=95)


def render_preview():
    audio = soundtrack()
    target = OUT / "kingdom-style-preview.mp4"
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", str(audio), "-c:v", "libx264", "-preset", "fast", "-crf", "18",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags",
               "+faststart", "-shortest", str(target)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
        try:
            for frame in range(DURATION * FPS):
                process.stdin.write(preview_frame(frame / FPS).tobytes())
                if frame % (FPS * 5) == 0:
                    print(f"Rendered {frame // FPS}/{DURATION}s", flush=True)
        finally:
            process.stdin.close()
        if process.wait():
            raise SystemExit("FFmpeg failed")
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(target)
    ]))
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    assert video["width"] == W and video["height"] == H
    assert int(video["nb_frames"]) == DURATION * FPS
    assert abs(float(probe["format"]["duration"]) - DURATION) < 0.08
    probe["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    (OUT / "verification.json").write_text(json.dumps(probe, indent=2) + "\n")
    print(f"Verified: {target.name}; {W}x{H}; {FPS} fps; {DURATION}s; audio included")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--stills", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--final-check", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    preflight(final=args.final_check)
    if args.preflight or args.final_check:
        return
    prepare_fonts()
    contact_sheet()
    if args.preview or not args.stills:
        render_preview()


if __name__ == "__main__":
    main()
