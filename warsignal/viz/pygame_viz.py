"""Interactive and headless Pygame renderer for mission VizSpec objects.

Layout (1280x800, see warsignal/viz/style.py for the shared standard):

    +--------------------------------------------------+---------------+
    | [ VERDICT ]  Title (bold)                        |  WarSignal    |
    |              subtitle (italic)                   |  hypothesis   |
    +--------------------------------------------------+  scores       |
    |  PANEL HEADER (bold)  note (italic)              |  stats (mono) |
    |  ┌────────────── chart ──────────────┐           |  legend       |
    |  └───────────────────────────────────┘           |               |
    |  ... up to 3 panels ...                          |               |
    +--------------------------------------------------+---------------+
    | controls hint                                                    |
    +------------------------------------------------------------------+
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from warsignal.analysis.stats import transform
from warsignal.config import WAR_START
from warsignal.indicators import REGISTRY, get_series
from warsignal.indicators.events import load_timeline
from warsignal.viz.style import GAP, LINE_GAP, PAD, PALETTE, VERDICT_TIERS, load_fonts, verdict_tier

WIDTH, HEIGHT = 1280, 800
PLOT_WIDTH, SIDEBAR_WIDTH = 940, WIDTH - 940
BANNER_HEIGHT = 92
FOOTER_HEIGHT = 34
PLOT_LEFT = 96
PLOT_RIGHT = PLOT_WIDTH - 28
PANEL_HEADER = 30
PANEL_FOOTER = 46
CEASEFIRE = (pd.Timestamp("2026-04-08"), pd.Timestamp("2026-07-08"))


def _read_result(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def _mission_id(path, result):
    return result.get("mission_id") or Path(path).stem


def _series_transforms(result):
    plan = result.get("plan") or {}
    return {
        plan.get("indicator_a"): plan.get("transform_a", "level"),
        plan.get("indicator_b"): plan.get("transform_b", "level"),
    }


def _load_panel_series(result, spec):
    transforms = _series_transforms(result)
    loaded = {}
    for panel in spec.get("panels", []):
        for name in panel.get("series", []):
            if name in loaded or name not in REGISTRY:
                continue
            try:
                series = get_series(name)
                series = transform(series, transforms.get(name, "level")).dropna()
                series.index = pd.to_datetime(series.index)
                loaded[name] = series.sort_index()
            except Exception:
                loaded[name] = pd.Series(dtype="float64", name=name)
    return loaded


def _date_range(series, result=None):
    """Window shown on time axes: the mission's aligned coverage, padded, else the overlap of the series."""
    stats = (result or {}).get("stats") or {}
    cov_start, cov_end = stats.get("coverage_start"), stats.get("coverage_end")
    if cov_start and cov_end:
        start, end = pd.Timestamp(cov_start), pd.Timestamp(cov_end)
        pad = max((end - start) * 0.25, pd.Timedelta(days=30))
        ends = [s.index.max() for s in series.values() if len(s)]
        latest = max(ends) if ends else end
        return start - pad, min(end + pad, max(latest, end))
    dates = [s.index.min() for s in series.values() if len(s)]
    ends = [s.index.max() for s in series.values() if len(s)]
    if not dates:
        return pd.Timestamp("2025-03-01"), pd.Timestamp("2026-09-19")
    start, end = max(dates), min(ends)
    if start >= end:
        start, end = min(dates), max(ends)
    return start, end


def _x(value, start, end, rect):
    span = max((end - start).total_seconds(), 1)
    return int(rect.left + (value - start).total_seconds() / span * rect.width)


def _y(value, low, high, rect):
    span = high - low or 1.0
    return int(rect.bottom - (value - low) / span * rect.height)


def _normalise(series):
    if series.empty:
        return series
    std = series.std(ddof=0)
    return (series - series.mean()) / std if std else series - series.mean()


def _fmt(value, digits=3):
    if value is None:
        return "—"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(value):
        return "—"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.{digits}f}"


def _short(name, limit=34):
    name = str(name)
    return name if len(name) <= limit else name[: limit - 1] + "…"


def _wrap(font, text, width_px):
    """Wrap text by measured pixel width rather than a character estimate."""
    words = str(text).split()
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if font.size(trial)[0] <= width_px or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _draw_wrapped(surface, font, text, color, rect, line_gap=LINE_GAP, max_lines=None, ellipsis=False):
    y = rect.top
    lines = _wrap(font, text, rect.width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        if ellipsis:
            while lines[-1] and font.size(lines[-1] + "…")[0] > rect.width:
                lines[-1] = lines[-1][:-1]
            lines[-1] = lines[-1].rstrip() + "…"
    for line in lines:
        if y + font.get_height() > rect.bottom + 1:
            break
        surface.blit(font.render(line, True, color), (rect.left, y))
        y += font.get_height() + line_gap
    return y


def _text_box(surface, pygame, font, text, color, pos, bg=(24, 28, 38), pad=6, border=None):
    label = font.render(text, True, color)
    box = pygame.Rect(pos[0], pos[1], label.get_width() + pad * 2, label.get_height() + pad * 2)
    pygame.draw.rect(surface, bg, box, border_radius=6)
    if border:
        pygame.draw.rect(surface, border, box, 1, border_radius=6)
    surface.blit(label, (box.left + pad, box.top + pad))
    return box


def _draw_frame(surface, pygame, rect):
    pygame.draw.rect(surface, PALETTE["panel"], rect.inflate(2, 2), border_radius=4)


def _draw_grid(surface, pygame, rect, rows=4, cols=6):
    for i in range(rows + 1):
        y = rect.top + i * rect.height // rows
        pygame.draw.line(surface, PALETTE["grid"], (rect.left, y), (rect.right, y), 1)
    for i in range(cols + 1):
        x = rect.left + i * rect.width // cols
        pygame.draw.line(surface, PALETTE["grid"], (x, rect.top), (x, rect.bottom), 1)
    pygame.draw.line(surface, PALETTE["axis"], (rect.left, rect.top), (rect.left, rect.bottom), 1)
    pygame.draw.line(surface, PALETTE["axis"], (rect.left, rect.bottom), (rect.right, rect.bottom), 1)


def _draw_empty(surface, pygame, fonts, rect, result):
    _draw_grid(surface, pygame, rect)
    text = str(result.get("error") or "no local data for this panel")
    lines = _wrap(fonts["hi"], text, rect.width - 2 * PAD)[:2]
    y = rect.centery - len(lines) * fonts["hi"].get_height() // 2
    for line in lines:
        label = fonts["hi"].render(line, True, PALETTE["faint"])
        surface.blit(label, (rect.centerx - label.get_width() // 2, y))
        y += fonts["hi"].get_height() + LINE_GAP


def _draw_y_ticks(surface, pygame, font, rect, low, high, digits=3, count=5):
    for tick in np.linspace(high, low, count):
        y = _y(float(tick), low, high, rect)
        pygame.draw.line(surface, PALETTE["axis"], (rect.left - 5, y), (rect.left, y), 1)
        label = font.render(_fmt(tick, digits), True, PALETTE["muted"])
        surface.blit(label, (rect.left - label.get_width() - 10, y - label.get_height() // 2))


def _draw_x_dates(surface, pygame, font, rect, start, end):
    month = start.to_period("M").to_timestamp()
    months = []
    while month <= end:
        months.append(month)
        month = month + pd.offsets.MonthBegin()
    step = 1
    if len(months) > 1:
        gap = _x(months[1], start, end, rect) - _x(months[0], start, end, rect)
        while gap * step < font.size("2026-09")[0] + 18:
            step += 1
    for i, month in enumerate(months):
        x = _x(month, start, end, rect)
        pygame.draw.line(surface, PALETTE["axis"], (x, rect.bottom), (x, rect.bottom + 5), 1)
        if i % step:
            continue
        label = font.render(month.strftime("%b %y"), True, PALETTE["muted"])
        lx = x - label.get_width() // 2
        if lx < rect.left - 2 or lx + label.get_width() > rect.right + 2:
            continue
        surface.blit(label, (lx, rect.bottom + 8))


def _draw_panel_header(surface, fonts, rect, title, note=None):
    y = rect.top - PANEL_HEADER
    head = fonts["h"].render(title.upper(), True, PALETTE["text"])
    surface.blit(head, (rect.left, y + 2))
    if note and note.strip().lower() != title.strip().lower():
        x = rect.left + head.get_width() + PAD
        avail = rect.width - head.get_width() - PAD
        lines = _wrap(fonts["hi"], note, avail)
        text = lines[0]
        if len(lines) > 1:
            while text and fonts["hi"].size(text + "…")[0] > avail:
                text = text[:-1]
            text += "…"
        surface.blit(fonts["hi"].render(text, True, PALETTE["muted"]), (x, y + 4))


def _draw_timeseries(surface, pygame, fonts, rect, panel, series, start, end, result, show_events):
    small = fonts["monosmall"]
    _draw_frame(surface, pygame, rect)
    normalize = bool(panel.get("normalize"))
    windowed = {name: (value.loc[(value.index >= start) & (value.index <= end)] if len(value) else value)
                for name, value in series.items()}
    values = {name: (_normalise(value) if normalize else value) for name, value in windowed.items()}
    nonempty = [value for value in values.values() if len(value)]
    if not nonempty:
        _draw_empty(surface, pygame, fonts, rect, result)
        return
    finite = pd.concat(nonempty, axis=0).dropna()
    if finite.empty:
        _draw_empty(surface, pygame, fonts, rect, result)
        return
    # Robust limits: ignore the most extreme 0.5% on each side so one spike cannot flatten the chart.
    low, high = float(finite.quantile(0.005)), float(finite.quantile(0.995))
    if low == high:
        low, high = float(finite.min()), float(finite.max())
    if low == high:
        low, high = low - 1, high + 1
    pad = (high - low) * 0.08
    low, high = low - pad, high + pad
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    war_start = max(start, pd.Timestamp(WAR_START))
    if war_start <= end:
        x0 = _x(war_start, start, end, rect) - rect.left
        pygame.draw.rect(overlay, (*PALETTE["war"], 26), (x0, 0, rect.width - x0, rect.height))
    if CEASEFIRE[1] >= start and CEASEFIRE[0] <= end:
        x0 = _x(max(start, CEASEFIRE[0]), start, end, rect) - rect.left
        x1 = _x(min(end, CEASEFIRE[1]), start, end, rect) - rect.left
        pygame.draw.rect(overlay, (*PALETTE["ceasefire"], 16), (x0, 0, max(1, x1 - x0), rect.height))
    surface.blit(overlay, rect.topleft)
    _draw_grid(surface, pygame, rect)
    _draw_y_ticks(surface, pygame, small, rect, low, high, digits=2 if normalize else 3)
    # Legend chips top-left inside the plot, stacked with padding.
    ly = rect.top + GAP
    for index, (name, value) in enumerate(values.items()):
        color = PALETTE["series"][index % len(PALETTE["series"])]
        points = [(_x(pd.Timestamp(day), start, end, rect), min(rect.bottom, max(rect.top, _y(float(item), low, high, rect))))
                  for day, item in value.items() if np.isfinite(item)]
        if len(points) > 1:
            pygame.draw.aalines(surface, color, False, points)
        label = _short(name, 44) + ("" if len(points) > 1 else "  · no data")
        chip = _text_box(surface, pygame, fonts["mono"], label, color, (rect.left + GAP, ly),
                         bg=(*PALETTE["panel"],), pad=4)
        pygame.draw.rect(surface, color, (chip.left, chip.top, 3, chip.height), border_radius=2)
        ly = chip.bottom + 4
    if war_start <= end:
        wx = _x(war_start, start, end, rect)
        tag = fonts["hi"].render("WAR", True, PALETTE["war"])
        surface.blit(tag, (min(wx + 6, rect.right - tag.get_width() - 4), rect.bottom - tag.get_height() - 6))
    if (result.get("plan") or {}).get("mode") == "single":
        means = result.get("stats", {}).get("pre_post") or {}
        raw_values = next(iter(windowed.values()))
        mean = float(raw_values.mean())
        std = float(raw_values.std(ddof=0))
        for key, color, label in (("pre", PALETTE["series"][2], "pre mean"),
                                  ("post", PALETTE["series"][3], "post mean")):
            value = (means.get(key) or {}).get("mean")
            if value is None:
                continue
            value = (float(value) - mean) / std if normalize and std else float(value)
            y = _y(value, low, high, rect)
            for x0 in range(rect.left, rect.right, 12):
                pygame.draw.line(surface, color, (x0, y), (min(x0 + 7, rect.right), y), 1)
            tag = fonts["hi"].render(label, True, color)
            surface.blit(tag, (rect.right - tag.get_width() - GAP, y - tag.get_height() - 3))
    _draw_x_dates(surface, pygame, small, rect, start, end)
    if show_events:
        category = (result.get("plan") or {}).get("event_category")
        categories = {category} if category else set()
        categories.update(panel.get("events", []))
        if not categories:
            categories = {"war"}
        category_colors = {"war": PALETTE["war"], "hormuz": PALETTE["series"][2],
                           "diplomacy": PALETTE["ceasefire"], "market": PALETTE["accent"]}
        timeline = load_timeline()
        event_overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        rows = [row for _, row in timeline.iterrows()
                if row.get("category") in categories and start <= pd.Timestamp(row["date"]) <= end]
        dense = len(rows) > 14
        for row in rows:
            x = _x(pd.Timestamp(row["date"]), start, end, rect) - rect.left
            color = category_colors.get(row.get("category"), PALETTE["series"][2])
            pygame.draw.line(event_overlay, (*color, 45 if dense else 90), (x, 0), (x, rect.height), 1)
            pygame.draw.circle(event_overlay, (*color, 200), (x, 4), 3)
        surface.blit(event_overlay, rect.topleft)


def _draw_scatter(surface, pygame, fonts, rect, panel, series, result):
    small = fonts["monosmall"]
    _draw_frame(surface, pygame, rect)
    names = panel.get("series", [])[:2]
    if len(names) < 2 or not all(len(series.get(name, [])) for name in names):
        _draw_empty(surface, pygame, fonts, rect, result)
        return
    frame = pd.concat([series[names[0]].rename("a"), series[names[1]].rename("b")], axis=1).dropna()
    if frame.empty:
        _draw_empty(surface, pygame, fonts, rect, result)
        return
    _draw_grid(surface, pygame, rect)
    x, y = frame["a"], frame["b"]
    xmin, xmax, ymin, ymax = float(x.min()), float(x.max()), float(y.min()), float(y.max())
    if xmin == xmax:
        xmin, xmax = xmin - 1, xmax + 1
    if ymin == ymax:
        ymin, ymax = ymin - 1, ymax + 1
    xpad, ypad = (xmax - xmin) * 0.05, (ymax - ymin) * 0.06
    xmin, xmax, ymin, ymax = xmin - xpad, xmax + xpad, ymin - ypad, ymax + ypad
    _draw_y_ticks(surface, pygame, small, rect, ymin, ymax)
    for i in range(6):
        px = rect.left + i * rect.width // 5
        label = small.render(_fmt(xmin + (xmax - xmin) * i / 5), True, PALETTE["muted"])
        surface.blit(label, (min(rect.right - label.get_width(), max(rect.left, px - label.get_width() // 2)),
                             rect.bottom + 8))
    for a, b in zip(x, y):
        pygame.draw.circle(surface, PALETTE["series"][0],
                           (int(rect.left + (a - xmin) / (xmax - xmin) * rect.width),
                            int(rect.bottom - (b - ymin) / (ymax - ymin) * rect.height)), 3)
    if len(frame) >= 2:
        slope, intercept = np.polyfit(x, y, 1)
        line = [(rect.left, _y(slope * xmin + intercept, ymin, ymax, rect)),
                (rect.right, _y(slope * xmax + intercept, ymin, ymax, rect))]
        pygame.draw.aalines(surface, PALETTE["series"][1], False, line)
    r = float(np.corrcoef(x, y)[0, 1]) if len(frame) > 1 else float("nan")
    stat_text = f"r = {r:.3f}   n = {len(frame)}"
    box_width = fonts["monobold"].size(stat_text)[0] + 10
    _text_box(surface, pygame, fonts["monobold"], stat_text, PALETTE["text"],
              (rect.right - box_width - GAP, rect.top + GAP), pad=5, border=PALETTE["grid"])
    x_label = fonts["hi"].render(_short(names[0], 48), True, PALETTE["muted"])
    surface.blit(x_label, (rect.centerx - x_label.get_width() // 2, rect.bottom + 22))
    y_label = pygame.transform.rotate(fonts["hi"].render(_short(names[1], 40), True, PALETTE["muted"]), 90)
    surface.blit(y_label, (max(2, rect.left - 90), rect.centery - y_label.get_height() // 2))


def _draw_lagcorr(surface, pygame, fonts, rect, panel, result):
    small = fonts["monosmall"]
    _draw_frame(surface, pygame, rect)
    _draw_grid(surface, pygame, rect, rows=4)
    lagged = result.get("stats", {}).get("lagged") or {}
    lags, values = lagged.get("lags", []), lagged.get("r", [])
    if not lags:
        surface.blit(fonts["hi"].render("no lagged statistics", True, PALETTE["muted"]),
                     (rect.left + PAD, rect.centery - 6))
        return
    valid = [float(value) for value in values if value is not None and np.isfinite(value)]
    if not valid:
        return
    # Axis is scaled to the data (rounded up to a tidy step) so bars fill the panel.
    peak = max(abs(value) for value in valid)
    step = 0.05
    for candidate in (0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1.0):
        if peak <= candidate * 0.98:
            step = candidate
            break
    limit = max(step, float(np.ceil(peak / step) * step)) if peak > 0 else step
    limit *= 1.3  # headroom so the tallest bar and its label stay inside the frame
    zero = rect.centery
    _draw_y_ticks(surface, pygame, small, rect, -limit, limit, digits=2, count=5)
    pygame.draw.line(surface, PALETTE["axis"], (rect.left, zero), (rect.right, zero), 1)
    slot = rect.width / len(lags)
    width = max(4, int(slot) - 6)
    best = lagged.get("best_lag")
    label_every = 1
    while slot * label_every < small.size("+0.00")[0] + 14:
        label_every += 1
    lag_label_every = 1
    while slot * lag_label_every < small.size("-14")[0] + 8:
        lag_label_every += 1
    for index, (lag, value) in enumerate(zip(lags, values)):
        if value is None or not np.isfinite(value):
            continue
        x = int(rect.left + index * slot + (slot - width) / 2)
        height = int(abs(value) / limit * (rect.height / 2))
        top = zero - height if value >= 0 else zero
        is_best = lag == best
        color = PALETTE["series"][1] if is_best else PALETTE["series"][0]
        pygame.draw.rect(surface, color, (x, top, width, max(height, 1)), border_radius=2)
        if is_best or index % label_every == 0:
            font = fonts["monobold"] if is_best else small
            value_label = font.render(f"{float(value):+.2f}", True, color if is_best else PALETTE["muted"])
            ly = top - value_label.get_height() - 3 if value >= 0 else zero + height + 3
            ly = max(rect.top + 2, min(rect.bottom - value_label.get_height() - 2, ly))
            surface.blit(value_label, (x + width // 2 - value_label.get_width() // 2, ly))
        if index % lag_label_every == 0 or is_best:
            label = (fonts["monobold"] if is_best else small).render(str(lag), True,
                                                                     color if is_best else PALETTE["muted"])
            surface.blit(label, (x + width // 2 - label.get_width() // 2, rect.bottom + 8))
    if best is not None:
        best_r = lagged.get("best_r")
        _text_box(surface, pygame, fonts["monobold"], f"best lag {best:+d}   r = {_fmt(best_r)}",
                  PALETTE["series"][1], (rect.left + GAP, rect.top + GAP), pad=5, border=PALETTE["grid"])
    lag_unit = result.get("stats", {}).get("lag_unit") or "days"
    caption = fonts["hi"].render(f"lag in {lag_unit} · positive lag = A leads B", True, PALETTE["faint"])
    surface.blit(caption, (rect.left, rect.bottom + 22))


def _draw_eventstudy(surface, pygame, fonts, rect, panel, result):
    small = fonts["monosmall"]
    _draw_frame(surface, pygame, rect)
    _draw_grid(surface, pygame, rect)
    event = result.get("stats", {}).get("event_study") or {}
    pre, post = event.get("mean_pre"), event.get("mean_post")
    if pre is None or post is None:
        surface.blit(fonts["hi"].render("no event-study statistics", True, PALETTE["muted"]),
                     (rect.left + PAD, rect.centery - 6))
        return
    pre, post = float(pre), float(post)
    peak = max(abs(pre), abs(post)) or 1.0
    limit = peak * 1.45
    zero = rect.centery
    _draw_y_ticks(surface, pygame, small, rect, -limit, limit)
    pygame.draw.line(surface, PALETTE["axis"], (rect.left, zero), (rect.right, zero), 1)
    width = rect.width // 5
    for x, value, color, label in ((rect.centerx - width - PAD, pre, PALETTE["series"][0], "PRE"),
                                   (rect.centerx + PAD, post, PALETTE["series"][1], "POST")):
        height = int(abs(value) / limit * (rect.height / 2))
        top = zero - height if value >= 0 else zero
        pygame.draw.rect(surface, color, (x, top, width, max(height, 1)), border_radius=3)
        tag = fonts["h"].render(label, True, color)
        surface.blit(tag, (x + width // 2 - tag.get_width() // 2, rect.bottom + 8))
        val = fonts["monobold"].render(_fmt(value), True, color)
        vy = top - val.get_height() - 4 if value >= 0 else zero + height + 4
        surface.blit(val, (x + width // 2 - val.get_width() // 2, max(rect.top + 2, vy)))


def _draw_banner(surface, pygame, fonts, result, title):
    tier, label, color = verdict_tier(result)
    pygame.draw.rect(surface, PALETTE["panel"], (0, 0, PLOT_WIDTH, BANNER_HEIGHT))
    pygame.draw.line(surface, PALETTE["grid"], (0, BANNER_HEIGHT), (PLOT_WIDTH, BANNER_HEIGHT), 1)
    verdict = fonts["verdict"].render(label, True, PALETTE["bg"])
    box = pygame.Rect(PAD, PAD, verdict.get_width() + 28, verdict.get_height() + 16)
    glow = pygame.Surface((box.width + 12, box.height + 12), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*color, 60), glow.get_rect(), border_radius=12)
    surface.blit(glow, (box.left - 6, box.top - 6))
    pygame.draw.rect(surface, color, box, border_radius=8)
    surface.blit(verdict, (box.left + 14, box.top + 8))
    sx = box.left
    for index, (name, tier_color) in enumerate(VERDICT_TIERS):
        active = index == tier
        chip = fonts["monobold" if active else "monosmall"].render(
            name.split()[0], True, tier_color if active else PALETTE["faint"])
        surface.blit(chip, (sx, box.bottom + 8 - (1 if active else 0)))
        sx += chip.get_width() + 12
    text_left = max(box.right, sx) + PAD + GAP
    text_width = PLOT_WIDTH - text_left - PAD
    y = _draw_wrapped(surface, fonts["title"], title, PALETTE["text"],
                      pygame.Rect(text_left, PAD - 2, text_width, fonts["title"].get_height() * 2 + LINE_GAP),
                      max_lines=2, ellipsis=True)
    plan = result.get("plan") or {}
    stats = result.get("stats") or {}
    sub = []
    if plan.get("indicator_a") and plan.get("indicator_b"):
        sub.append(f"{plan['indicator_a']} × {plan['indicator_b']}")
    elif plan.get("indicator_a"):
        sub.append(plan["indicator_a"])
    cov = (stats.get("coverage_start"), stats.get("coverage_end"))
    if all(cov):
        sub.append(f"{cov[0]} → {cov[1]}")
    if sub:
        line = fonts["subtitle"].render("   ·   ".join(sub), True, PALETTE["muted"])
        if y + line.get_height() <= BANNER_HEIGHT - 6:
            surface.blit(line, (text_left, y + 2))


def _score_bar(surface, pygame, fonts, x, y, width, label, value, color):
    value = 0.0 if value is None else float(value)
    name = fonts["h"].render(label.upper(), True, PALETTE["text"])
    num = fonts["monobold"].render(f"{value:.2f}", True, color)
    surface.blit(name, (x, y))
    surface.blit(num, (x + width - num.get_width(), y - 1))
    bar_y = y + name.get_height() + 6
    pygame.draw.rect(surface, PALETTE["grid"], (x, bar_y, width, 8), border_radius=4)
    pygame.draw.rect(surface, color, (x, bar_y, int(width * max(0.0, min(10.0, value)) / 10.0), 8), border_radius=4)
    return bar_y + 8 + PAD


def _draw_sidebar(surface, pygame, fonts, result, series):
    x = PLOT_WIDTH + PAD + 4
    width = SIDEBAR_WIDTH - PAD * 2 - 8
    pygame.draw.rect(surface, PALETTE["panel"], (PLOT_WIDTH, 0, SIDEBAR_WIDTH, HEIGHT))
    pygame.draw.line(surface, PALETTE["grid"], (PLOT_WIDTH, 0), (PLOT_WIDTH, HEIGHT), 1)
    y = PAD
    brand = fonts["brand"].render("WarSignal", True, PALETTE["accent"])
    surface.blit(brand, (x, y))
    mission = fonts["monosmall"].render(str(result.get("mission_id", "")), True, PALETTE["faint"])
    surface.blit(mission, (x, y + brand.get_height() + 2))
    y += brand.get_height() + mission.get_height() + PAD
    head = fonts["hi"].render("HYPOTHESIS", True, PALETTE["faint"])
    surface.blit(head, (x, y))
    y += head.get_height() + 4
    y = _draw_wrapped(surface, fonts["subtitle"], result.get("hypothesis", ""), PALETTE["text"],
                      pygame.Rect(x, y, width, fonts["subtitle"].get_height() * 7 + LINE_GAP * 6),
                      max_lines=7, ellipsis=True)
    y += PAD
    pygame.draw.line(surface, PALETTE["grid"], (x, y), (x + width, y), 1)
    y += PAD
    scores = result.get("scores") or {}
    for key, color in (("validity", PALETTE["accent"]), ("interestingness", PALETTE["series"][2]),
                       ("unexpectedness", PALETTE["series"][4])):
        y = _score_bar(surface, pygame, fonts, x, y, width, key, scores.get(key, result.get(key)), color)
    pygame.draw.line(surface, PALETTE["grid"], (x, y), (x + width, y), 1)
    y += PAD
    stats = result.get("stats") or {}
    corr = (stats.get("correlation") or {}).get("pearson_r", result.get("r"))
    lagged = stats.get("lagged") or {}
    rows = [
        ("pearson r", _fmt(corr)),
        ("best lag", "—" if lagged.get("best_lag") is None else f"{lagged['best_lag']:+d}"),
        ("best r", _fmt(lagged.get("best_r"))),
        ("perm p", _fmt(stats.get("perm_p", result.get("perm_p")))),
        ("n obs", _fmt(result.get("n_obs", stats.get("n_obs")), 0)),
        ("supported", _fmt(scores.get("supported_prob", result.get("supported_prob")), 2)),
    ]
    for key, value in rows:
        k = fonts["mono"].render(key, True, PALETTE["muted"])
        v = fonts["monobold"].render(value, True, PALETTE["text"])
        surface.blit(k, (x, y))
        surface.blit(v, (x + width - v.get_width(), y - 1))
        y += max(k.get_height(), v.get_height()) + 6
    y += GAP
    pygame.draw.line(surface, PALETTE["grid"], (x, y), (x + width, y), 1)
    y += PAD
    head = fonts["hi"].render("SERIES", True, PALETTE["faint"])
    surface.blit(head, (x, y))
    y += head.get_height() + 6
    for index, name in enumerate(series):
        color = PALETTE["series"][index % len(PALETTE["series"])]
        pygame.draw.rect(surface, color, (x, y + 3, 10, 10), border_radius=2)
        key = fonts["monosmall"].render(f"{index + 1}", True, color)
        surface.blit(key, (x + 16, y + 1))
        y = _draw_wrapped(surface, fonts["small"], name, PALETTE["text"],
                          pygame.Rect(x + 30, y, width - 30, fonts["small"].get_height() * 2 + 2),
                          max_lines=2, ellipsis=True)
        y += 4
        if y > HEIGHT - FOOTER_HEIGHT - PAD:
            break


def _panel_rects(pygame, count):
    top = BANNER_HEIGHT + PAD + PANEL_HEADER
    bottom = HEIGHT - FOOTER_HEIGHT
    count = max(1, count)
    per = (bottom - top) // count
    rects = []
    for index in range(count):
        y = top + index * per
        rects.append(pygame.Rect(PLOT_LEFT, y, PLOT_RIGHT - PLOT_LEFT, per - PANEL_HEADER - PANEL_FOOTER))
    return rects


def render(spec, mission_result_json_path, screenshot_path=None, interactive=True):
    """Render a validated VizSpec, optionally opening an interactive Pygame window."""
    result = _read_result(mission_result_json_path)
    if not interactive:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    title = spec.get("title") or result.get("mission_id", "WarSignal")
    pygame.display.set_caption(title)
    fonts = load_fonts(pygame)
    series = _load_panel_series(result, spec)
    start, end = _date_range(series, result)
    show_events = True
    normalize_override = None
    hidden = set()
    hover = None
    dragging = False
    drag_x = 0
    drag_start, drag_end = start, end
    running = True
    screenshot = Path(screenshot_path) if screenshot_path else None
    if screenshot is None and not interactive:
        screenshot = Path("missions/reports") / f"{_mission_id(mission_result_json_path, result)}.png"
    clock = pygame.time.Clock()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_n:
                    normalize_override = not bool(normalize_override)
                elif event.key == pygame.K_e:
                    show_events = not show_events
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    index = event.key - pygame.K_1
                    names = list(series)
                    if index < len(names):
                        if names[index] in hidden:
                            hidden.remove(names[index])
                        else:
                            hidden.add(names[index])
                elif event.key == pygame.K_s:
                    target = screenshot or Path("missions/reports") / f"{_mission_id(mission_result_json_path, result)}.png"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(screen, target)
            elif event.type == pygame.MOUSEWHEEL:
                span = end - start
                factor = 0.8 if event.y > 0 else 1.25
                center = start + span / 2
                start, end = center - span * factor / 2, center + span * factor / 2
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging, drag_x, drag_start, drag_end = True, event.pos[0], start, end
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == pygame.MOUSEMOTION:
                hover = event.pos
                if dragging:
                    span = drag_end - drag_start
                    shift = -((event.pos[0] - drag_x) / max(PLOT_RIGHT - PLOT_LEFT, 1)) * span
                    start, end = drag_start + shift, drag_end + shift
        screen.fill(PALETTE["bg"])
        _draw_banner(screen, pygame, fonts, result, title)
        panels = spec.get("panels") or []
        rects = _panel_rects(pygame, len(panels))
        for panel, rect in zip(panels, rects):
            kind = panel.get("kind")
            note = panel.get("note", "")
            if kind == "timeseries":
                current = dict(panel)
                current["series"] = [name for name in panel.get("series", []) if name not in hidden]
                current["events"] = spec.get("events", [])
                if normalize_override is not None:
                    current["normalize"] = normalize_override
                panel_series = {name: series[name] for name in current["series"] if name in series}
                _draw_panel_header(screen, fonts, rect, "Time series" + (" · z-scored" if current.get("normalize") else ""), note)
                _draw_timeseries(screen, pygame, fonts, rect, current, panel_series, start, end, result, show_events)
            elif kind == "scatter":
                _draw_panel_header(screen, fonts, rect, "Scatter", note)
                _draw_scatter(screen, pygame, fonts, rect, panel, series, result)
            elif kind == "lagcorr":
                _draw_panel_header(screen, fonts, rect, "Lag correlation", note)
                _draw_lagcorr(screen, pygame, fonts, rect, panel, result)
            elif kind == "eventstudy":
                _draw_panel_header(screen, fonts, rect, "Event study", note)
                _draw_eventstudy(screen, pygame, fonts, rect, panel, result)
        _draw_sidebar(screen, pygame, fonts, result, list(series))
        if hover and 0 <= hover[0] < PLOT_WIDTH and BANNER_HEIGHT <= hover[1] < HEIGHT - FOOTER_HEIGHT:
            pygame.draw.line(screen, PALETTE["faint"], (hover[0], BANNER_HEIGHT), (hover[0], HEIGHT - FOOTER_HEIGHT), 1)
            day = start + (end - start) * (hover[0] - PLOT_LEFT) / max(PLOT_RIGHT - PLOT_LEFT, 1)
            lines = [day.date().isoformat()]
            for name, value in series.items():
                if len(value):
                    point = value.loc[value.index.get_indexer([day], method="nearest")[0]]
                    lines.append(f"{_short(name, 40)}: {float(point):.3f}")
            width = max(fonts["mono"].size(line)[0] for line in lines) + 16
            height = len(lines) * fonts["mono"].get_linesize() + 12
            left = min(hover[0] + 10, PLOT_WIDTH - width - 4)
            top = min(hover[1] + 10, HEIGHT - FOOTER_HEIGHT - height)
            pygame.draw.rect(screen, (24, 28, 38), (left, top, width, height), border_radius=6)
            pygame.draw.rect(screen, PALETTE["grid"], (left, top, width, height), 1, border_radius=6)
            for index, line in enumerate(lines):
                screen.blit(fonts["mono"].render(line, True, PALETTE["text"]),
                            (left + 8, top + 6 + index * fonts["mono"].get_linesize()))
        pygame.draw.line(screen, PALETTE["grid"], (0, HEIGHT - FOOTER_HEIGHT), (PLOT_WIDTH, HEIGHT - FOOTER_HEIGHT), 1)
        status = fonts["small"].render(
            "hover values  ·  wheel zoom  ·  drag pan  ·  N normalize  ·  E events  ·  1-9 toggle series  ·  S screenshot  ·  Q quit",
            True, PALETTE["faint"])
        screen.blit(status, (PLOT_LEFT, HEIGHT - FOOTER_HEIGHT + (FOOTER_HEIGHT - status.get_height()) // 2))
        pygame.display.flip()
        if not interactive:
            target = screenshot or Path("missions/reports") / f"{_mission_id(mission_result_json_path, result)}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(screen, target)
            running = False
        else:
            clock.tick(30)
    pygame.quit()
    return str(screenshot) if screenshot else None
