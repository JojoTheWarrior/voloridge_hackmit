"""WarSignal generated chart. Self-contained: loads plan.json + data CSVs from its own folder."""

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pygame

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
WIDTH, HEIGHT = 1280, 800
PALETTE = {
    "bg": (13, 15, 20),
    "panel": (18, 21, 28),
    "grid": (38, 43, 54),
    "axis": (70, 78, 94),
    "text": (236, 240, 246),
    "muted": (140, 152, 172),
    "faint": (92, 102, 120),
    "accent": (76, 201, 240),
    "series": [(76, 201, 240), (247, 37, 133), (255, 209, 102), (6, 214, 160), (181, 126, 255)],
}
# Shared WarSignal typography (Inter + JetBrains Mono) bundled in the repo; DejaVu fallback keeps the
# script runnable when the folder is moved elsewhere.
FONT_DIRS = [BASE / "fonts", BASE.parent.parent / "warsignal" / "viz" / "fonts"]
FONT_FILES = {
    "title": ("Inter-Bold.ttf", 24), "label": ("Inter-SemiBold.ttf", 14), "italic": ("Inter-Italic.ttf", 13),
    "mono": ("JetBrainsMono-Regular.ttf", 12), "monobold": ("JetBrainsMono-Bold.ttf", 13),
    "small": ("Inter-Regular.ttf", 12),
}
FALLBACK = {"title": ("dejavusans", 22, True, False), "label": ("dejavusans", 13, True, False),
            "italic": ("dejavusans", 12, False, True), "mono": ("dejavusansmono", 12, False, False),
            "monobold": ("dejavusansmono", 13, True, False), "small": ("dejavusans", 11, False, False)}


def load_fonts():
    fonts = {}
    for role, (filename, size) in FONT_FILES.items():
        path = next((d / filename for d in FONT_DIRS if (d / filename).exists()), None)
        if path is not None:
            fonts[role] = pygame.font.Font(str(path), size)
        else:
            name, fsize, bold, italic = FALLBACK[role]
            fonts[role] = pygame.font.SysFont(name, fsize, bold=bold, italic=italic)
    return fonts


WAR_START = pd.Timestamp("2026-02-28")
CEASEFIRE = (pd.Timestamp("2026-04-08"), pd.Timestamp("2026-07-08"))

HEADLESS = os.environ.get("CHART_HEADLESS")


def load_plan():
    return json.loads((BASE / "plan.json").read_text(encoding="utf-8"))


def load_series_file(name):
    path = BASE / name
    if not path.exists():
        path = BASE / "data" / name
    frame = pd.read_csv(path)
    dates = pd.to_datetime(frame["date"])
    values = pd.to_numeric(frame["value"], errors="coerce").to_numpy(dtype="float64")
    return dates, values


def load_events():
    path = BASE / "iran_timeline.csv"
    if not path.exists():
        return []
    frame = pd.read_csv(path)
    events = []
    for _, row in frame.iterrows():
        try:
            day = pd.Timestamp(row["date"])
        except Exception:
            continue
        events.append((day, str(row.get("category", "")), str(row.get("event", ""))))
    return events


def build_series(plan):
    series = []
    for item in plan.get("series", []):
        dates, values = load_series_file(item["file"])
        series.append({"label": item.get("label", item["file"]), "dates": dates, "values": values})
    return series


def build_spread(plan):
    a_dates, a_vals = load_series_file(plan["series"][0]["file"])
    b_dates, b_vals = load_series_file(plan["series"][1]["file"])
    frame = pd.DataFrame({"a": a_vals}, index=a_dates).join(
        pd.DataFrame({"b": b_vals}, index=b_dates), how="inner")
    diff = (frame["a"] - frame["b"]).dropna()
    label = plan["series"][0].get("label", "a") + " - " + plan["series"][1].get("label", "b")
    return [{"label": label, "dates": diff.index, "values": diff.to_numpy()}]


def build_scatter(plan):
    x_dates, x_vals = load_series_file(plan.get("x_series") or plan["series"][0]["file"])
    y_dates, y_vals = load_series_file(plan.get("y_series") or plan["series"][1]["file"])
    frame = pd.DataFrame({"x": x_vals}, index=x_dates).join(
        pd.DataFrame({"y": y_vals}, index=y_dates), how="inner").dropna()
    return frame


def xmap(day, start, end, rect):
    span = max((end - start).days, 1)
    return int(rect.left + (day - start).days / span * rect.width)


def ymap(value, low, high, rect):
    span = high - low or 1.0
    return int(rect.bottom - (value - low) / span * rect.height)


def fmt_value(value):
    return f"{value:.4g}" if abs(value) < 1 else f"{value:.2f}"


def draw_frame(screen, rect):
    pygame.draw.rect(screen, PALETTE["panel"], rect.inflate(2, 2), border_radius=4)


def draw_grid(screen, font, rect, low, high, start, end, xnum=None):
    for i in range(5):
        y = rect.top + i * rect.height // 4
        pygame.draw.line(screen, PALETTE["grid"], (rect.left, y), (rect.right, y), 1)
        value = high - (high - low) * i / 4
        label = font.render(fmt_value(value), True, PALETTE["muted"])
        screen.blit(label, (max(0, rect.left - label.get_width() - 12), y - label.get_height() // 2))
    pygame.draw.line(screen, PALETTE["axis"], (rect.left, rect.top), (rect.left, rect.bottom), 1)
    pygame.draw.line(screen, PALETTE["axis"], (rect.left, rect.bottom), (rect.right, rect.bottom), 1)
    if xnum is not None:
        xmin, xmax = xnum
        for i in range(6):
            x = rect.left + i * rect.width // 5
            pygame.draw.line(screen, PALETTE["grid"], (x, rect.top), (x, rect.bottom), 1)
            label = font.render(fmt_value(xmin + (xmax - xmin) * i / 5), True, PALETTE["muted"])
            screen.blit(label, (min(rect.right - label.get_width(), max(rect.left, x - label.get_width() // 2)),
                                rect.bottom + 10))
        return
    months = []
    month = start.to_period("M").to_timestamp()
    while month <= end:
        months.append(month)
        month = month + pd.offsets.MonthBegin()
    step = 1
    if len(months) > 1:
        gap = xmap(months[1], start, end, rect) - xmap(months[0], start, end, rect)
        while gap * step < font.size("Sep 26")[0] + 20:
            step += 1
    for i, month in enumerate(months):
        x = xmap(month, start, end, rect)
        pygame.draw.line(screen, PALETTE["axis"], (x, rect.bottom), (x, rect.bottom + 5), 1)
        if i % step:
            continue
        label = font.render(month.strftime("%b %y"), True, PALETTE["muted"])
        lx = x - label.get_width() // 2
        if lx < rect.left - 2 or lx + label.get_width() > rect.right + 2:
            continue
        screen.blit(label, (lx, rect.bottom + 10))


def draw_bands(screen, rect, start, end):
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    if WAR_START <= end:
        x0 = xmap(max(start, WAR_START), start, end, rect) - rect.left
        pygame.draw.rect(overlay, (247, 37, 133, 28), (x0, 0, rect.width - x0, rect.height))
    if CEASEFIRE[1] >= start and CEASEFIRE[0] <= end:
        x0 = xmap(max(start, CEASEFIRE[0]), start, end, rect) - rect.left
        x1 = xmap(min(end, CEASEFIRE[1]), start, end, rect) - rect.left
        pygame.draw.rect(overlay, (6, 214, 160, 18), (x0, 0, max(1, x1 - x0), rect.height))
    screen.blit(overlay, rect.topleft)


def draw_events(screen, font, rect, start, end, events, hover_x=None):
    colors = {"war": (247, 37, 133), "diplomacy": (6, 214, 160)}
    shown = None
    for day, category, text in events:
        if not (start <= day <= end):
            continue
        x = xmap(day, start, end, rect)
        if category in colors:
            color = colors[category]
            pygame.draw.line(screen, color, (x, rect.top), (x, rect.top + 10), 2)
            pygame.draw.circle(screen, color, (x, rect.top + 2), 2)
        if hover_x is not None and abs(hover_x - x) <= 6:
            shown = (x, text)
    if shown:
        label = font.render(shown[1], True, PALETTE["text"])
        lx = min(max(rect.left, shown[0] - label.get_width() // 2), rect.right - label.get_width())
        pygame.draw.rect(screen, (24, 28, 38), (lx - 8, rect.top + 14, label.get_width() + 16,
                                               label.get_height() + 10), border_radius=6)
        screen.blit(label, (lx, rect.top + 19))


def draw_lines(screen, font, rect, series, start, end, upto=None, glow=False, legend_font=None):
    legend_font = legend_font or font
    all_vals = np.concatenate([s["values"][np.isfinite(s["values"])] for s in series]) if series else np.array([])
    if all_vals.size == 0:
        return 0.0, 1.0
    low, high = float(all_vals.min()), float(all_vals.max())
    if low == high:
        low, high = low - 1, high + 1
    pad = (high - low) * 0.05
    low, high = low - pad, high + pad
    draw_frame(screen, rect)
    draw_bands(screen, rect, start, end)
    draw_grid(screen, font, rect, low, high, start, end)
    heads = []
    for index, s in enumerate(series):
        color = PALETTE["series"][index % len(PALETTE["series"])]
        dates, values = s["dates"], s["values"]
        points = []
        for d, v in zip(dates, values):
            if not np.isfinite(v) or d < start or d > end:
                continue
            if upto is not None and d > upto:
                break
            points.append((xmap(d, start, end, rect), ymap(float(v), low, high, rect)))
        if len(points) > 1:
            pygame.draw.aalines(screen, color, False, points)
        if points:
            heads.append((points[-1], color, float(s["values"][min(len(points) - 1, len(s["values"]) - 1)])))
            if glow:
                pygame.draw.circle(screen, (*color,), points[-1], 6)
                pygame.draw.circle(screen, (255, 255, 255), points[-1], 2)
        chip = legend_font.render(s["label"], True, color)
        cy = rect.top + 10 + index * (chip.get_height() + 12)
        pygame.draw.rect(screen, PALETTE["panel"], (rect.left + 10, cy - 4, chip.get_width() + 18, chip.get_height() + 8),
                         border_radius=6)
        pygame.draw.rect(screen, color, (rect.left + 10, cy - 4, 3, chip.get_height() + 8), border_radius=2)
        screen.blit(chip, (rect.left + 20, cy))
    return low, high, heads


def draw_status(screen, font):
    bar = pygame.Rect(0, HEIGHT - 34, WIDTH, 34)
    pygame.draw.rect(screen, PALETTE["panel"], bar)
    pygame.draw.line(screen, PALETTE["grid"], (0, bar.top), (WIDTH, bar.top), 1)
    keys = "Space play/pause  ·  Left/Right step  ·  Up/Down speed  ·  Home/End  ·  R restart  ·  S screenshot  ·  Q quit"
    label = font.render(keys, True, PALETTE["faint"])
    screen.blit(label, (16, bar.centery - label.get_height() // 2))


def main():
    plan = load_plan()
    chart_type = plan.get("chart_type", "line")
    events = load_events()
    if chart_type == "spread" and len(plan.get("series", [])) >= 2:
        series = build_spread(plan)
    elif chart_type == "scatter":
        series = []
    else:
        series = build_series(plan)
    if chart_type == "scatter":
        frame = build_scatter(plan)
        days = frame.index
    else:
        all_dates = pd.DatetimeIndex(sorted(set().union(*[s["dates"] for s in series]))) if series else pd.DatetimeIndex([])
        frame, days = None, all_dates
    if len(days) == 0:
        days = pd.DatetimeIndex([pd.Timestamp("2025-01-01")])
    start, end = days.min(), days.max()
    if start == end:
        end = start + pd.Timedelta(days=1)

    pygame.init()
    pygame.key.set_repeat(250, 30)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(plan.get("title", "WarSignal chart"))
    fonts = load_fonts()
    font, title_font, small = fonts["mono"], fonts["title"], fonts["small"]
    rect = pygame.Rect(104, 88, WIDTH - 168, HEIGHT - 196)

    cursor = int((len(days) - 1) * 0.7) if HEADLESS else (0 if chart_type == "reel" else len(days) - 1)
    playing = chart_type == "reel" and not HEADLESS
    speed = 8.0
    hover = None
    clock = pygame.time.Clock()
    accum = 0.0

    def render_frame():
        screen.fill(PALETTE["bg"])
        screen.blit(title_font.render(plan.get("title", "WarSignal chart"), True, PALETTE["text"]), (rect.left, 22))
        brand = fonts["italic"].render("WarSignal · " + chart_type, True, PALETTE["faint"])
        screen.blit(brand, (rect.left, 22 + title_font.get_height() + 4))
        hx = hover[0] if hover else None
        if chart_type == "scatter":
            xs, ys = frame["x"].to_numpy(), frame["y"].to_numpy()
            xmin, xmax = float(xs.min()), float(xs.max())
            ymin, ymax = float(ys.min()), float(ys.max())
            if xmin == xmax:
                xmin, xmax = xmin - 1, xmax + 1
            if ymin == ymax:
                ymin, ymax = ymin - 1, ymax + 1
            draw_frame(screen, rect)
            draw_grid(screen, font, rect, ymin, ymax, start, end, xnum=(xmin, xmax))
            for d, xv, yv in zip(frame.index, xs, ys):
                color = PALETTE["series"][1] if d >= WAR_START else PALETTE["muted"]
                px = int(rect.left + (xv - xmin) / (xmax - xmin) * rect.width)
                py = int(rect.bottom - (yv - ymin) / (ymax - ymin) * rect.height)
                pygame.draw.circle(screen, color, (px, py), 3)
            if len(frame) > 1:
                slope, intercept = np.polyfit(xs, ys, 1)
                line = [(rect.left, int(rect.bottom - (slope * xmin + intercept - ymin) / (ymax - ymin) * rect.height)),
                        (rect.right, int(rect.bottom - (slope * xmax + intercept - ymin) / (ymax - ymin) * rect.height))]
                pygame.draw.aalines(screen, PALETTE["series"][0], False, line)
                r = float(np.corrcoef(xs, ys)[0, 1])
                stat = fonts["monobold"].render(f"r = {r:.3f}   n = {len(frame)}", True, PALETTE["text"])
                box = pygame.Rect(rect.right - stat.get_width() - 26, rect.top + 10, stat.get_width() + 16, stat.get_height() + 10)
                pygame.draw.rect(screen, (24, 28, 38), box, border_radius=6)
                pygame.draw.rect(screen, PALETTE["grid"], box, 1, border_radius=6)
                screen.blit(stat, (box.left + 8, box.top + 5))
            labels = plan.get("series", [])
            if len(labels) >= 2:
                xl = fonts["italic"].render(labels[0].get("label", "x"), True, PALETTE["muted"])
                screen.blit(xl, (rect.centerx - xl.get_width() // 2, rect.bottom + 34))
                yl = pygame.transform.rotate(fonts["italic"].render(labels[1].get("label", "y"), True, PALETTE["muted"]), 90)
                screen.blit(yl, (rect.left - 96, rect.centery - yl.get_height() // 2))
            if hover and rect.collidepoint(hover):
                idx = int(np.argmin(np.abs(((xs - xmin) / (xmax - xmin) * rect.width + rect.left - hover[0]))))
                screen.blit(font.render(str(frame.index[idx].date()), True, PALETTE["text"]),
                            (hover[0] + 10, hover[1] + 10))
        else:
            upto = days[cursor] if chart_type == "reel" else None
            low, high, heads = draw_lines(screen, font, rect, series, start, end, upto=upto,
                                          glow=chart_type == "reel", legend_font=fonts["label"])
            if chart_type == "spread" and low < 0 < high:
                zero = ymap(0, low, high, rect)
                for x in range(rect.left, rect.right, 8):
                    pygame.draw.line(screen, PALETTE["muted"], (x, zero), (min(x + 4, rect.right), zero), 1)
            draw_events(screen, small, rect, start, end, events, hover_x=hx)
            if chart_type == "reel":
                day = days[cursor]
                parts = [day.date().isoformat()] + [f"{v:.2f}" for _, _, v in heads]
                readout = fonts["monobold"].render("   |   ".join(parts), True, PALETTE["text"])
                box = pygame.Rect(rect.right - readout.get_width() - 16, 24, readout.get_width() + 16, readout.get_height() + 10)
                pygame.draw.rect(screen, (24, 28, 38), box, border_radius=6)
                pygame.draw.rect(screen, PALETTE["grid"], box, 1, border_radius=6)
                screen.blit(readout, (box.left + 8, box.top + 5))
                pygame.draw.rect(screen, PALETTE["grid"], (rect.left, rect.bottom + 50, rect.width, 6), border_radius=3)
                pygame.draw.rect(screen, PALETTE["accent"],
                                 (rect.left, rect.bottom + 50, int(rect.width * cursor / max(len(days) - 1, 1)), 6),
                                 border_radius=3)
            if hover and rect.collidepoint(hover):
                day = start + pd.Timedelta(days=(hover[0] - rect.left) / max(rect.width, 1) * (end - start).days)
                lines = [day.date().isoformat()]
                for s in series:
                    pos = s["dates"].searchsorted(day)
                    if 0 <= pos < len(s["values"]):
                        lines.append(f"{s['label']}: {s['values'][pos]:.3f}")
                w = max(font.size(t)[0] for t in lines) + 20
                h = len(lines) * (font.get_linesize() + 2) + 12
                lx, ly = min(hover[0] + 12, WIDTH - w - 10), min(hover[1] + 12, HEIGHT - h - 40)
                pygame.draw.rect(screen, (24, 28, 38), (lx, ly, w, h), border_radius=6)
                pygame.draw.rect(screen, PALETTE["grid"], (lx, ly, w, h), 1, border_radius=6)
                for i, t in enumerate(lines):
                    screen.blit(font.render(t, True, PALETTE["text"]), (lx + 10, ly + 6 + i * (font.get_linesize() + 2)))
                pygame.draw.line(screen, PALETTE["muted"], (hover[0], rect.top), (hover[0], rect.bottom), 1)
        draw_status(screen, font)
        pygame.display.flip()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_SPACE and chart_type == "reel":
                    playing = not playing
                elif event.key == pygame.K_LEFT:
                    cursor = max(0, cursor - 1)
                elif event.key == pygame.K_RIGHT:
                    cursor = min(len(days) - 1, cursor + 1)
                elif event.key == pygame.K_UP:
                    speed *= 1.5
                elif event.key == pygame.K_DOWN:
                    speed /= 1.5
                elif event.key == pygame.K_HOME:
                    cursor = 0
                elif event.key == pygame.K_END:
                    cursor = len(days) - 1
                elif event.key == pygame.K_r:
                    cursor = 0
                elif event.key == pygame.K_s:
                    pygame.image.save(screen, BASE / f"screenshot_{days[cursor].date()}.png")
            elif event.type == pygame.MOUSEMOTION:
                hover = event.pos
        if playing and chart_type == "reel":
            accum += dt * speed
            step = int(accum)
            if step:
                accum -= step
                cursor = min(len(days) - 1, cursor + step)
                if cursor >= len(days) - 1:
                    playing = False
        render_frame()
        if HEADLESS:
            pygame.image.save(screen, HEADLESS)
            pygame.quit()
            sys.exit(0)
    pygame.quit()


if __name__ == "__main__":
    main()
