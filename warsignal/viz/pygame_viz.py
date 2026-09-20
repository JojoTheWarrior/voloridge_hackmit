"""Interactive and headless Pygame renderer for mission VizSpec objects."""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd

from warsignal.analysis.stats import transform
from warsignal.config import WAR_START
from warsignal.indicators import REGISTRY, get_series
from warsignal.indicators.events import load_timeline

WIDTH, HEIGHT = 1280, 800
PLOT_WIDTH, SIDEBAR_WIDTH = 1000, 280
PALETTE = {
    "bg": (15, 17, 23),
    "grid": (42, 47, 58),
    "text": (226, 232, 240),
    "muted": (148, 163, 184),
    "pre": (55, 65, 81),
    "war": (93, 45, 57),
    "series": [(76, 201, 240), (247, 37, 133), (255, 209, 102), (6, 214, 160)],
}


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
                loaded[name] = transform(series, transforms.get(name, "level")).dropna()
            except Exception:
                loaded[name] = pd.Series(dtype="float64", name=name)
    return loaded


def _date_range(series):
    dates = [s.index.min() for s in series.values() if len(s)]
    ends = [s.index.max() for s in series.values() if len(s)]
    if not dates:
        return pd.Timestamp("2025-03-01"), pd.Timestamp("2026-09-19")
    return min(dates), max(ends)


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


def _draw_wrapped(surface, font, text, color, rect, line_gap=3, max_lines=None, ellipsis=False):
    y = rect.top
    width = max(1, rect.width // max(font.size("M")[0], 1))
    lines = textwrap.wrap(str(text), width=width) or [""]
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        if ellipsis:
            lines[-1] = (lines[-1].rstrip()[: max(1, width - 1)] + "…")
    for line in lines:
        if y + font.get_height() > rect.bottom:
            break
        surface.blit(font.render(line, True, color), (rect.left, y))
        y += font.get_height() + line_gap
    return y


def _draw_grid(surface, pygame, rect, rows=4, cols=6):
    for i in range(rows + 1):
        y = rect.top + i * rect.height // rows
        pygame.draw.line(surface, PALETTE["grid"], (rect.left, y), (rect.right, y), 1)
    for i in range(cols + 1):
        x = rect.left + i * rect.width // cols
        pygame.draw.line(surface, PALETTE["grid"], (x, rect.top), (x, rect.bottom), 1)


def _draw_timeseries(surface, pygame, font, rect, panel, series, start, end, result, show_events):
    normalize = bool(panel.get("normalize"))
    values = {name: (_normalise(value) if normalize else value) for name, value in series.items()}
    nonempty = [value for value in values.values() if len(value)]
    if not nonempty:
        _draw_grid(surface, pygame, rect)
        return
    finite = pd.concat(nonempty, axis=0).dropna()
    if finite.empty:
        _draw_grid(surface, pygame, rect)
        return
    low, high = float(finite.min()), float(finite.max())
    if low == high:
        low, high = low - 1, high + 1
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    war_start = max(start, pd.Timestamp(WAR_START))
    if war_start <= end:
        x0 = _x(war_start, start, end, rect) - rect.left
        pygame.draw.rect(overlay, (247, 37, 133, 28), (x0, 0, rect.width - x0, rect.height))
        surface.blit(overlay, rect.topleft)
        surface.blit(font.render("WAR", True, (247, 37, 133)), (max(rect.left + 4, x0 + rect.left + 4), rect.top + 2))
    ceasefire_start, ceasefire_end = pd.Timestamp("2026-04-08"), pd.Timestamp("2026-07-08")
    if ceasefire_end >= start and ceasefire_start <= end:
        x0 = _x(max(start, ceasefire_start), start, end, rect) - rect.left
        x1 = _x(min(end, ceasefire_end), start, end, rect) - rect.left
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (6, 214, 160, 18), (x0, 0, max(1, x1 - x0), rect.height))
        surface.blit(overlay, rect.topleft)
    _draw_grid(surface, pygame, rect)
    for tick in np.linspace(high, low, 4):
        y = _y(float(tick), low, high, rect)
        pygame.draw.line(surface, PALETTE["muted"], (rect.left - 4, y), (rect.left, y), 1)
        label = font.render(f"{tick:.3f}" if normalize else f"{tick:.2f}", True, PALETTE["muted"])
        surface.blit(label, (max(0, rect.left - label.get_width() - 8), y - label.get_height() // 2))
    for index, (name, value) in enumerate(values.items()):
        points = [(_x(pd.Timestamp(day), start, end, rect), _y(float(item), low, high, rect))
                  for day, item in value.items() if start <= pd.Timestamp(day) <= end and np.isfinite(item)]
        if len(points) > 1:
            pygame.draw.aalines(surface, PALETTE["series"][index % len(PALETTE["series"])], False, points)
        label = font.render(name, True, PALETTE["series"][index % len(PALETTE["series"])])
        surface.blit(label, (rect.left + 8, rect.top + 6 + index * font.get_height()))
    month = start.to_period("M").to_timestamp()
    date_font = pygame.font.SysFont("dejavusans", 10)
    while month <= end:
        x = _x(month, start, end, rect)
        pygame.draw.line(surface, PALETTE["muted"], (x, rect.bottom), (x, rect.bottom + 4), 1)
        label = date_font.render(month.strftime("%Y-%m"), True, PALETTE["muted"])
        surface.blit(label, (max(rect.left, min(rect.right - label.get_width(), x - label.get_width() // 2)), rect.bottom + 5))
        month = month + pd.offsets.MonthBegin()
    if show_events:
        category = result.get("plan", {}).get("event_category")
        categories = {category} if category else set()
        categories.update(panel.get("events", []))
        category_colors = {"war": (247, 37, 133), "hormuz": (255, 209, 102),
                           "diplomacy": (6, 214, 160), "market": (76, 201, 240)}
        timeline = load_timeline()
        event_overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for _, row in timeline.iterrows():
            if categories and row.get("category") not in categories:
                continue
            day = pd.Timestamp(row["date"])
            if start <= day <= end:
                x = _x(day, start, end, rect) - rect.left
                color = category_colors.get(row.get("category"), PALETTE["series"][2])
                pygame.draw.line(event_overlay, (*color, 120), (x, 0), (x, rect.height), 1)
                pygame.draw.circle(event_overlay, (*color, 180), (x, 3), 3)
        surface.blit(event_overlay, rect.topleft)
    _draw_wrapped(surface, font, panel.get("note", "Timeseries"), PALETTE["text"],
                  pygame.Rect(rect.left, rect.top - font.get_height() * 2 - 6, rect.width, font.get_height() * 2 + 2),
                  max_lines=2, ellipsis=True)


def _draw_scatter(surface, pygame, font, rect, panel, series):
    _draw_grid(surface, pygame, rect)
    names = panel.get("series", [])[:2]
    if len(names) < 2 or not all(len(series.get(name, [])) for name in names):
        return
    frame = pd.concat([series[names[0]].rename("a"), series[names[1]].rename("b")], axis=1).dropna()
    if frame.empty:
        return
    x, y = frame["a"], frame["b"]
    xmin, xmax, ymin, ymax = float(x.min()), float(x.max()), float(y.min()), float(y.max())
    if xmin == xmax:
        xmin, xmax = xmin - 1, xmax + 1
    if ymin == ymax:
        ymin, ymax = ymin - 1, ymax + 1
    points = [(int(rect.left + (a - xmin) / (xmax - xmin) * rect.width),
               int(rect.bottom - (b - ymin) / (ymax - ymin) * rect.height)) for a, b in zip(x, y)]
    for point in points:
        pygame.draw.circle(surface, PALETTE["series"][0], point, 3)
    if len(frame) >= 2:
        slope, intercept = np.polyfit(x, y, 1)
        line = [(rect.left, _y(slope * xmin + intercept, ymin, ymax, rect)),
                (rect.right, _y(slope * xmax + intercept, ymin, ymax, rect))]
        pygame.draw.aalines(surface, PALETTE["series"][1], False, line)
    r = float(np.corrcoef(x, y)[0, 1]) if len(frame) > 1 else float("nan")
    surface.blit(font.render(f"r={r:.3f}, n={len(frame)}", True, PALETTE["text"]), (rect.right - 130, rect.top + 5))
    x_label = font.render(names[0], True, PALETTE["muted"])
    surface.blit(x_label, (rect.centerx - x_label.get_width() // 2, rect.bottom + 5))
    y_label = pygame.transform.rotate(font.render(names[1], True, PALETTE["muted"]), 90)
    surface.blit(y_label, (max(0, rect.left - y_label.get_width() - 8), rect.centery - y_label.get_height() // 2))
    surface.blit(font.render("Scatter", True, PALETTE["text"]), (rect.left, rect.top - font.get_height() - 4))


def _draw_lagcorr(surface, pygame, font, rect, panel, result):
    _draw_grid(surface, pygame, rect)
    lagged = result.get("stats", {}).get("lagged") or {}
    lags, values = lagged.get("lags", []), lagged.get("r", [])
    if not lags:
        return
    valid = [float(value) for value in values if value is not None and np.isfinite(value)]
    if not valid:
        return
    maximum = max(1.0, max(abs(value) for value in valid))
    zero = rect.bottom - rect.height // 2
    pygame.draw.line(surface, PALETTE["muted"], (rect.left, zero), (rect.right, zero), 1)
    width = max(4, rect.width // len(lags) - 6)
    best = lagged.get("best_lag")
    for index, (lag, value) in enumerate(zip(lags, values)):
        if value is None or not np.isfinite(value):
            continue
        x = rect.left + index * (rect.width // len(lags)) + 4
        height = int(abs(value) / maximum * rect.height // 2)
        top = zero - height if value >= 0 else zero
        color = PALETTE["series"][1] if lag == best else PALETTE["series"][0]
        pygame.draw.rect(surface, color, (x, top, width, max(height, 1)))
        value_label = font.render(f"{float(value):.3f}", True, color)
        surface.blit(value_label, (x + width // 2 - value_label.get_width() // 2,
                                   top - value_label.get_height() - 2 if value >= 0 else zero + 2))
        label = font.render(str(lag), True, PALETTE["muted"])
        surface.blit(label, (x, rect.bottom - label.get_height() - 2))
    surface.blit(font.render("Lag correlation", True, PALETTE["text"]), (rect.left, rect.top - font.get_height() - 4))
    surface.blit(font.render("positive lag = A leads B", True, PALETTE["muted"]), (rect.right - 180, rect.bottom + 5))


def _draw_eventstudy(surface, pygame, font, rect, panel, result):
    _draw_grid(surface, pygame, rect)
    event = result.get("stats", {}).get("event_study") or {}
    pre, post = event.get("mean_pre"), event.get("mean_post")
    if pre is None or post is None:
        return
    maximum = max(abs(float(pre)), abs(float(post)), 1.0)
    zero = rect.bottom - rect.height // 2
    width = rect.width // 4
    for x, value, color, label in ((rect.centerx - width, pre, PALETTE["series"][0], "pre"),
                                   (rect.centerx + 8, post, PALETTE["series"][1], "post")):
        height = int(abs(float(value)) / maximum * rect.height // 2)
        top = zero - height if value >= 0 else zero
        pygame.draw.rect(surface, color, (x, top, width, max(height, 1)))
        surface.blit(font.render(label, True, PALETTE["muted"]), (x, rect.bottom - font.get_height()))
    surface.blit(font.render(panel.get("note", "Event study"), True, PALETTE["text"]), (rect.left, rect.top - font.get_height() - 4))


def _draw_sidebar(surface, pygame, fonts, result, series):
    title_font, body_font = fonts
    x = PLOT_WIDTH + 16
    y = 16
    surface.blit(title_font.render("WarSignal", True, PALETTE["series"][0]), (x, y))
    y += title_font.get_height() + 8
    y = _draw_wrapped(surface, body_font, result.get("hypothesis", ""), PALETTE["text"],
                       pygame.Rect(x, y, SIDEBAR_WIDTH - 30, 198), max_lines=12, ellipsis=True)
    y += 8
    for key in ("validity", "interestingness", "unexpectedness"):
        value = float(result.get("scores", {}).get(key) or 0)
        surface.blit(body_font.render(f"{key}: {value:.3f}", True, PALETTE["text"]), (x, y))
        pygame.draw.rect(surface, PALETTE["grid"], (x, y + 20, 220, 8))
        pygame.draw.rect(surface, PALETTE["series"][0], (x, y + 20, int(22 * max(0, min(10, value))), 8))
        y += 42
    corr = (result.get("stats", {}).get("correlation") or {}).get("pearson_r")
    lag = (result.get("stats", {}).get("lagged") or {}).get("best_lag")
    def fmt(value):
        return "—" if value is None else f"{float(value):.3f}"
    stats = [f"r: {fmt(corr)}", f"best lag: {lag}", f"perm p: {fmt(result.get('stats', {}).get('perm_p'))}",
             f"n: {result.get('n_obs', result.get('stats', {}).get('n_obs', 0))}"]
    y += 4
    for line in stats:
        surface.blit(body_font.render(line, True, PALETTE["muted"]), (x, y))
        y += body_font.get_height() + 4
    y += 8
    for index, name in enumerate(series):
        color = PALETTE["series"][index % len(PALETTE["series"])]
        surface.blit(body_font.render(f"{index + 1}: {name}", True, color), (x, y))
        y += body_font.get_height() + 3


def render(spec, mission_result_json_path, screenshot_path=None, interactive=True):
    """Render a validated VizSpec, optionally opening an interactive Pygame window."""
    result = _read_result(mission_result_json_path)
    if not interactive:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(spec.get("title") or result.get("mission_id", "WarSignal"))
    title_font = pygame.font.SysFont("dejavusans", 18, bold=True)
    body_font = pygame.font.SysFont("dejavusans", 13)
    series = _load_panel_series(result, spec)
    start, end = _date_range(series)
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
                    shift = -((event.pos[0] - drag_x) / max(PLOT_WIDTH, 1)) * span
                    start, end = drag_start + shift, drag_end + shift
        screen.fill(PALETTE["bg"])
        _draw_wrapped(screen, title_font, spec.get("title") or result.get("mission_id", "WarSignal"),
                      PALETTE["text"], pygame.Rect(64, 8, PLOT_WIDTH - 72, 50), max_lines=2, ellipsis=True)
        panels = spec.get("panels") or []
        height = max(100, (HEIGHT - 138) // max(1, len(panels)))
        for index, panel in enumerate(panels):
            rect = pygame.Rect(64, index * height + 100, PLOT_WIDTH - 84, height - 36)
            kind = panel.get("kind")
            if kind == "timeseries":
                current = dict(panel)
                current["series"] = [name for name in panel.get("series", []) if name not in hidden]
                current["events"] = spec.get("events", [])
                if normalize_override is not None:
                    current["normalize"] = normalize_override
                panel_series = {name: series[name] for name in current["series"] if name in series}
                _draw_timeseries(screen, pygame, body_font, rect, current, panel_series, start, end, result, show_events)
            elif kind == "scatter":
                _draw_scatter(screen, pygame, body_font, rect, panel, series)
            elif kind == "lagcorr":
                _draw_lagcorr(screen, pygame, body_font, rect, panel, result)
            elif kind == "eventstudy":
                _draw_eventstudy(screen, pygame, body_font, rect, panel, result)
        pygame.draw.line(screen, PALETTE["grid"], (PLOT_WIDTH, 0), (PLOT_WIDTH, HEIGHT), 1)
        _draw_sidebar(screen, pygame, (title_font, body_font), result, list(series))
        if hover and 0 <= hover[0] < PLOT_WIDTH and 0 <= hover[1] < HEIGHT:
            pygame.draw.line(screen, PALETTE["muted"], (hover[0], 0), (hover[0], HEIGHT), 1)
            plot_left, plot_right = 64, PLOT_WIDTH - 20
            day = start + (end - start) * (hover[0] - plot_left) / max(plot_right - plot_left, 1)
            lines = [day.date().isoformat()]
            for name, value in series.items():
                if len(value):
                    point = value.loc[value.index.get_indexer([day], method="nearest")[0]]
                    lines.append(f"{name}: {float(point):.3f}")
            width = max(body_font.size(line)[0] for line in lines) + 12
            height = len(lines) * body_font.get_linesize() + 8
            left = min(hover[0] + 8, PLOT_WIDTH - width)
            top = min(hover[1] + 8, HEIGHT - height)
            pygame.draw.rect(screen, (24, 28, 38), (left, top, width, height))
            for index, line in enumerate(lines):
                screen.blit(body_font.render(line, True, PALETTE["text"]),
                            (left + 6, top + 4 + index * body_font.get_linesize()))
        status = body_font.render("hover for values · wheel zoom · drag pan · N normalize · E events · S screenshot · Q quit",
                                  True, PALETTE["muted"])
        screen.blit(status, (64, HEIGHT - status.get_height() - 5))
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
