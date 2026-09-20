"""Castle interior: great hall + menus (current missions, queue, completed).

Contract with the rest of Kingdom:

* ``CastleScene(app, menu=None)`` — ``menu`` may be ``"current"``,
  ``"queue"`` or ``"completed"`` to open directly on that menu (used by
  ``--scene`` and screenshot tests); ``None`` shows the main menu.
* Esc/Backspace at the main menu calls ``app.pop()`` (App fades back to the field).
* Data comes from ``app.data.snapshot()`` (see ``kingdom/data.py``).
* Sprites come from ``app.assets.get(name)``; text from ``kingdom.text``.
"""
from __future__ import annotations

import math
import time
from typing import Callable, Optional

import pygame

from .app import LOGICAL_H, LOGICAL_W, Scene
from .data import CompletedMission, QueueItem
from .text import draw_text, text_size
from .ui import (
    AMBER,
    GOLD,
    GOLD_LIGHT,
    GREEN,
    INK,
    OUTLINE,
    PARCHMENT_DARK,
    RED,
    SHADOW,
    TEXT,
    TEXT_DIM,
    TEXT_FAINT,
    WOOD_DARK,
    Button,
    ProgressBar,
    ScrollList,
    TextPanel,
    ThumbnailCache,
    clip_lines,
    copy_to_clipboard,
    draw_clipboard_icon,
    draw_cursor_hand,
    draw_panel,
    draw_sprite_or_box,
    draw_thumbnail,
    fmt_elapsed,
    fmt_num,
    lerp_color,
    scaled_region,
    signal_color,
)

MAIN, CURRENT, QUEUE, COMPLETED, DETAIL = "main", "current", "queue", "completed", "detail"
NOTE, ZOOM = "note", "zoom"
MENUS = (CURRENT, QUEUE, COMPLETED)
PANEL = pygame.Rect(50, 35, 380, 200)
MAIN_PANEL_W = 340
CHART = pygame.Rect(PANEL.x + 12, PANEL.y + 30, 232, 130)
ZOOM_VIEW = pygame.Rect(4, 4, LOGICAL_W - 8, LOGICAL_H - 22)
COPY_BUTTON = pygame.Rect(PANEL.right - 12 - 84, PANEL.y + 10, 84, 12)
NOTE_BUTTON = pygame.Rect(PANEL.right - 12 - 84, PANEL.bottom - 24, 84, 12)
COPIED_SECONDS = 1.5
SLIDE_SECONDS = 0.2
MISSION_SECONDS = 300.0  # missions take ~3-5 minutes
LH = 9  # line height of the 8px font
# (label, key) for the completed list; None values always sort last
SORT_KEYS: tuple[tuple[str, Callable[[CompletedMission], Optional[float]]], ...] = (
    ("|r|", lambda m: abs(m.r) if m.r is not None else None),
    ("lag", lambda m: m.best_lag),
    ("perm p", lambda m: m.perm_p),
    ("validity", lambda m: m.validity),
    ("interest", lambda m: m.interestingness),
    ("unexpected", lambda m: m.unexpectedness),
    ("n", lambda m: m.n_obs),
    ("newest", lambda m: m.created_at),
)


def sort_completed(rows: list[CompletedMission], sort_index: int, descending: bool) -> list[CompletedMission]:
    key = SORT_KEYS[sort_index % len(SORT_KEYS)][1]
    known = [m for m in rows if key(m) is not None]
    unknown = [m for m in rows if key(m) is None]
    return sorted(known, key=key, reverse=descending) + unknown


class CastleScene(Scene):
    def __init__(self, app, menu: Optional[str] = None):
        super().__init__(app)
        self.menu = MAIN
        self.t = 0.0
        self.slide = 0.0  # seconds remaining in the current transition
        self.slide_dir = 1
        self.selected = 0  # main-menu button / list row
        self.hover: Optional[int] = None
        self.thumbs = ThumbnailCache()
        self.detail: Optional[CompletedMission] = None
        inner = PANEL.inflate(-24, -24)
        self.list_view = pygame.Rect(inner.x, inner.y + 18, inner.w - 8, inner.h - 18)
        self.scroll = ScrollList(self.list_view, step=LH)
        self.note_panel = TextPanel(pygame.Rect(PANEL.x + 12, PANEL.y + 30, PANEL.w - 24, PANEL.h - 42))
        self.copied_until = -1.0
        self.zoom = 1.0
        self.zoom_center = (0.5, 0.5)
        self._drag: Optional[tuple[int, int]] = None
        self.sort_index = 0
        self.sort_desc = True
        self._zoom_cache: Optional[tuple[tuple, pygame.Surface]] = None
        self._row_tops: list[tuple[int, int]] = []  # (top, height) per row in content coords
        bw, bh = 200, 26
        bx = LOGICAL_W // 2 - bw // 2
        self.buttons = [
            Button("Current missions", pygame.Rect(bx, PANEL.y + 52, bw, bh), "icon_hammer", CURRENT),
            Button("Mission queue", pygame.Rect(bx, PANEL.y + 88, bw, bh), "icon_scroll", QUEUE),
            Button("Completed missions", pygame.Rect(bx, PANEL.y + 124, bw, bh), "icon_trophy", COMPLETED),
        ]
        if menu in MENUS:
            self.menu = menu
        self._light = pygame.Surface((LOGICAL_W, LOGICAL_H))

    # -- navigation --------------------------------------------------------
    def open_menu(self, menu: str, direction: int = 1):
        self.menu = menu
        self.slide = SLIDE_SECONDS
        self.slide_dir = direction
        self.selected = 0
        self.hover = None
        self.scroll.scroll_to(0)

    def back(self):
        if self.menu == MAIN:
            self.app.pop()
        elif self.menu == DETAIL:
            self.detail = None
            self.open_menu(COMPLETED, -1)
            self.selected = self._detail_index
            self.scroll.scroll_to(self._detail_scroll)
        elif self.menu in (NOTE, ZOOM):
            self._drag = None
            self.open_menu(DETAIL, -1)
        else:
            self.open_menu(MAIN, -1)

    def open_detail(self, mission: CompletedMission):
        self._detail_index = self.selected
        self._detail_scroll = self.scroll.offset
        self.detail = mission
        self.note_panel.set_text(mission.note_text() or "(no note written for this mission)",
                                 title=mission.hypothesis, subtitle=mission.mission_id)
        self.zoom, self.zoom_center, self._zoom_cache = 1.0, (0.5, 0.5), None
        self.open_menu(DETAIL, 1)

    def completed_rows(self) -> list[CompletedMission]:
        return sort_completed(self.app.data.snapshot().completed, self.sort_index, self.sort_desc)

    def cycle_sort(self):
        self.sort_index = (self.sort_index + 1) % len(SORT_KEYS)
        self.selected = 0
        self.scroll.scroll_to(0)

    def toggle_sort_direction(self):
        self.sort_desc = not self.sort_desc
        self.selected = 0
        self.scroll.scroll_to(0)

    def copy_command(self) -> str:
        """Copy a shell command that opens this mission's note in VS Code."""
        m = self.detail
        if m is None:
            return ""
        target = m.note_path if m.note_path is not None else m.path
        try:
            rel = target.resolve().relative_to(self.app.root.resolve())
        except ValueError:
            rel = target
        command = f'code "{rel.as_posix()}"'
        self.copied_until = self.t + COPIED_SECONDS if copy_to_clipboard(command) else -1.0
        return command

    # -- events ------------------------------------------------------------
    def handle_event(self, event):
        if self.slide > 0:
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.back()
            return
        handler = {
            MAIN: self._event_main,
            CURRENT: self._event_list,
            QUEUE: self._event_list,
            COMPLETED: self._event_completed,
            DETAIL: self._event_detail,
            NOTE: self._event_note,
            ZOOM: self._event_zoom,
        }[self.menu]
        handler(event)

    def _event_main(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.buttons)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.open_menu(self.buttons[self.selected].action)
        elif event.type == pygame.MOUSEMOTION:
            for i, button in enumerate(self.buttons):
                if button.rect.collidepoint(event.lpos):
                    self.selected = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.rect.collidepoint(event.lpos):
                    self.open_menu(button.action)

    def _event_list(self, event):
        self.scroll.handle_event(event)

    def _event_completed(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
            self.cycle_sort()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_d:
            self.toggle_sort_direction()
            return
        rows = self.completed_rows()
        if not rows:
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN):
            self.selected = max(0, min(len(rows) - 1, self.selected + (1 if event.key == pygame.K_DOWN else -1)))
            if self.selected < len(self._row_tops):
                top, h = self._row_tops[self.selected]
                self.scroll.ensure_visible(top, top + h)
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.open_detail(rows[min(self.selected, len(rows) - 1)])
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover = self._row_at(event.lpos)
            if self.hover is not None:
                self.selected = self.hover
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            idx = self._row_at(event.lpos)
            if idx is not None and idx < len(rows):
                self.selected = idx
                self.open_detail(rows[idx])
            return
        self.scroll.handle_event(event)

    def _event_detail(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_z):
                self.open_menu(ZOOM)
            elif event.key == pygame.K_n:
                self.open_menu(NOTE)
            elif event.key == pygame.K_c:
                self.copy_command()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if COPY_BUTTON.collidepoint(event.lpos):
                self.copy_command()
            elif CHART.collidepoint(event.lpos):
                self.open_menu(ZOOM)
            elif NOTE_BUTTON.collidepoint(event.lpos):
                self.open_menu(NOTE)

    def _event_note(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_n):
            self.back()
            return
        self.note_panel.handle_event(event)

    def _event_zoom(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_z):
                self.back()
            elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS, pygame.K_UP):
                self._zoom_by(1.25)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_DOWN):
                self._zoom_by(0.8)
            elif event.key == pygame.K_0:
                self.zoom, self.zoom_center = 1.0, (0.5, 0.5)
        elif event.type == pygame.MOUSEWHEEL:
            self._zoom_by(1.25 if event.y > 0 else 0.8)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._drag = event.lpos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag = None
        elif event.type == pygame.MOUSEMOTION and self._drag is not None:
            img = self.thumbs.source(self.detail.viz_path) if self.detail else None
            if img is not None:
                fit = min(ZOOM_VIEW.w / img.get_width(), ZOOM_VIEW.h / img.get_height()) * self.zoom
                dx = (event.lpos[0] - self._drag[0]) / (img.get_width() * fit)
                dy = (event.lpos[1] - self._drag[1]) / (img.get_height() * fit)
                cx, cy = self.zoom_center
                self.zoom_center = (min(1.0, max(0.0, cx - dx)), min(1.0, max(0.0, cy - dy)))
            self._drag = event.lpos

    def _zoom_by(self, factor: float, toward: Optional[tuple[int, int]] = None):
        new_zoom = min(8.0, max(1.0, self.zoom * factor))
        if toward is not None and new_zoom > self.zoom:
            # move the centre a little toward the pointer so zooming feels anchored
            fx = (toward[0] - ZOOM_VIEW.x) / ZOOM_VIEW.w
            fy = (toward[1] - ZOOM_VIEW.y) / ZOOM_VIEW.h
            cx, cy = self.zoom_center
            k = 0.35
            self.zoom_center = (cx + (fx - cx) * k, cy + (fy - cy) * k)
        self.zoom = new_zoom
        if self.zoom == 1.0:
            self.zoom_center = (0.5, 0.5)

    def _row_at(self, pos) -> Optional[int]:
        if not self.list_view.collidepoint(pos):
            return None
        y = pos[1] - self.list_view.y + self.scroll.offset
        for i, (top, h) in enumerate(self._row_tops):
            if top <= y < top + h:
                return i
        return None

    # -- update ------------------------------------------------------------
    def update(self, dt, t):
        self.t += dt
        if self.slide > 0:
            self.slide = max(0.0, self.slide - dt)
        self.app.data.snapshot()

    def _slide_offset(self) -> tuple[int, float]:
        """(dx, alpha) for the sliding panel: eases in from the side."""
        if self.slide <= 0:
            return 0, 1.0
        k = self.slide / SLIDE_SECONDS  # 1 -> 0
        ease = k * k
        return int(round(ease * 24 * self.slide_dir)), 1.0 - ease

    # -- draw --------------------------------------------------------------
    def draw(self, surface, t):
        t = self.t
        self._draw_background(surface, t)
        dx, alpha = self._slide_offset()
        if alpha < 1.0:
            layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            self._draw_menu(layer, t, dx)
            layer.set_alpha(int(255 * alpha))
            surface.blit(layer, (0, 0))
        else:
            self._draw_menu(surface, t, 0)

    def _draw_menu(self, surface, t, dx):
        if self.menu == MAIN:
            self._draw_main(surface, t, dx)
        elif self.menu == CURRENT:
            self._draw_current(surface, t, dx)
        elif self.menu == QUEUE:
            self._draw_queue(surface, t, dx)
        elif self.menu == COMPLETED:
            self._draw_completed(surface, t, dx)
        elif self.menu == DETAIL:
            self._draw_detail(surface, t, dx)
        elif self.menu == NOTE:
            self._draw_note(surface, t, dx)
        else:
            self._draw_zoom(surface, t, dx)

    def _draw_background(self, surface, t):
        assets = self.app.assets
        if assets.has("hall_bg"):
            surface.blit(assets.get("hall_bg", (LOGICAL_W, LOGICAL_H)).frame(t), (0, 0))
        else:
            self._draw_fallback_hall(surface)
        torch = assets.get("torch", (8, 16), (242, 168, 111))
        for i, x in enumerate((36, LOGICAL_W - 44)):
            surface.blit(torch.frame(t, i * 0.37), (x, 14))
            # glow under the torch
            glow = 0.5 + 0.5 * math.sin(t * 0.8 + i * 1.7)
            r = 10 + int(glow * 3)
            pygame.draw.circle(surface, (int(38 + 12 * glow), int(20 + 8 * glow), 0), (x + 4, 24), r, 0)
        # warm flicker overlay (additive, very gentle)
        k = 0.5 + 0.5 * math.sin(t * 0.8)
        self._light.fill((int(14 * k), int(8 * k), int(2 * k)))
        surface.blit(self._light, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _draw_fallback_hall(self, surface):
        surface.fill((43, 49, 64))
        # stone courses
        for y in range(0, LOGICAL_H, 12):
            pygame.draw.line(surface, (36, 41, 54), (0, y), (LOGICAL_W, y))
            off = 12 if (y // 12) % 2 else 0
            for x in range(off, LOGICAL_W, 24):
                pygame.draw.line(surface, (36, 41, 54), (x, y), (x, y + 12))
        # floor
        pygame.draw.rect(surface, (74, 82, 102), (0, 190, LOGICAL_W, LOGICAL_H - 190))
        for y in range(190, LOGICAL_H, 10):
            pygame.draw.line(surface, (58, 65, 84), (0, y), (LOGICAL_W, y))
        # carpet
        pygame.draw.rect(surface, (122, 47, 47), (LOGICAL_W // 2 - 40, 0, 80, LOGICAL_H))
        pygame.draw.rect(surface, (178, 63, 63), (LOGICAL_W // 2 - 34, 0, 68, LOGICAL_H))
        pygame.draw.rect(surface, GOLD, (LOGICAL_W // 2 - 40, 0, 2, LOGICAL_H))
        pygame.draw.rect(surface, GOLD, (LOGICAL_W // 2 + 38, 0, 2, LOGICAL_H))
        # windows
        for x in (14, 70, LOGICAL_W - 86, LOGICAL_W - 30):
            pygame.draw.rect(surface, OUTLINE, (x - 1, 39, 18, 62))
            pygame.draw.rect(surface, (29, 63, 94), (x, 40, 16, 60))
            pygame.draw.rect(surface, (63, 143, 179), (x + 2, 42, 12, 30))
            pygame.draw.line(surface, OUTLINE, (x + 8, 40), (x + 8, 99))
        # throne
        pygame.draw.rect(surface, OUTLINE, (LOGICAL_W // 2 - 11, 4, 22, 30))
        pygame.draw.rect(surface, GOLD, (LOGICAL_W // 2 - 10, 5, 20, 28))
        pygame.draw.rect(surface, (122, 47, 47), (LOGICAL_W // 2 - 7, 9, 14, 20))
        # banners
        for x in (110, LOGICAL_W - 126):
            pygame.draw.rect(surface, OUTLINE, (x - 1, 4, 18, 40))
            pygame.draw.rect(surface, (122, 47, 47), (x, 5, 16, 38))
            pygame.draw.rect(surface, GOLD, (x + 5, 14, 6, 6))

    # -- main --------------------------------------------------------------
    def _draw_title(self, surface, title, dx, subtitle: Optional[str] = None):
        y = PANEL.y + 10
        draw_text(surface, title, (LOGICAL_W // 2 + dx, y), GOLD_LIGHT, kind="title", shadow=OUTLINE, align="center")
        th = text_size(title, "title")[1]
        if subtitle:
            draw_text(surface, subtitle, (LOGICAL_W // 2 + dx, y + th + 3), TEXT_DIM, align="center")
        # ornament line
        w = text_size(title, "title")[0] + 24
        ly = y + th + (14 if subtitle else 3)
        pygame.draw.line(surface, GOLD, (LOGICAL_W // 2 - w // 2 + dx, ly), (LOGICAL_W // 2 + w // 2 + dx, ly))
        pygame.draw.rect(surface, GOLD_LIGHT, (LOGICAL_W // 2 - 1 + dx, ly - 1, 3, 3))

    def _draw_main(self, surface, t, dx):
        assets = self.app.assets
        snap = self.app.data.snapshot()
        counts = f"{len(snap.active)} active   {len(snap.queue)} queued   {len(snap.completed)} done"
        if snap.counts["live"] > 0:
            counts += f"   {snap.counts['live']} live"
        pw = max(MAIN_PANEL_W, text_size(counts, "small")[0] + 32)
        panel = pygame.Rect(LOGICAL_W // 2 - pw // 2, PANEL.y + 10, pw, 172).move(dx, 0)
        draw_panel(surface, assets, panel)
        draw_sprite_or_box(surface, assets, "crest", panel.centerx - 16, panel.y - 14, (32, 32), t, (122, 47, 47))
        draw_text(surface, "GREAT HALL", (panel.centerx, panel.y + 20), GOLD_LIGHT, kind="title", shadow=OUTLINE, align="center")
        pygame.draw.line(surface, GOLD, (panel.x + 40, panel.y + 38), (panel.right - 41, panel.y + 38))
        for i, button in enumerate(self.buttons):
            button.draw(surface, assets, i == self.selected, t, dx, 0)
        sel = self.buttons[self.selected].rect.move(dx, 0)
        draw_cursor_hand(surface, assets, sel.x - 4, sel.centery, t)
        draw_text(surface, counts, (panel.centerx, panel.bottom - 24), TEXT_DIM, kind="small", align="center")
        draw_text(surface, "Esc: leave the castle", (panel.centerx, panel.bottom - 13), TEXT_FAINT, kind="small", align="center")

    # -- shared list frame ---------------------------------------------------
    def _begin_list(self, surface, dx) -> pygame.Rect:
        view = self.list_view.move(dx, 0)
        prev = surface.get_clip()
        surface.set_clip(view)
        return prev

    def _draw_empty(self, surface, message, dx):
        view = self.list_view.move(dx, 0)
        draw_text(surface, message, (view.centerx, view.centery - 4), TEXT_DIM, align="center")

    def _footer(self, surface, text, dx):
        draw_text(surface, text, (LOGICAL_W // 2 + dx, PANEL.bottom + 6), TEXT_DIM, kind="small", shadow=OUTLINE,
                  align="center")

    # -- current -------------------------------------------------------------
    def _draw_current(self, surface, t, dx):
        assets = self.app.assets
        draw_panel(surface, assets, PANEL.move(dx, 0))
        snap = self.app.data.snapshot()
        self._draw_title(surface, "CURRENT MISSIONS", dx)
        self._footer(surface, "Wheel/arrows: scroll   Esc: back", dx)
        if not snap.active:
            self.scroll.set_content_height(0)
            self._draw_empty(surface, "The workshops are quiet - no active missions.", dx)
            return
        view = self.list_view.move(dx, 0)
        card_w = view.w - 6
        text_w = card_w - 16
        now = time.time()
        cards = []
        y = 0
        for m in snap.active:
            lines = clip_lines(m.display_title, text_w, 2)
            msg = clip_lines(m.message, text_w, 1, "small")[0] if m.message else ""
            h = 8 + len(lines) * LH + 2 + LH + 6 + 12 + (LH + 4 if msg else 0) + 6
            cards.append((m, lines, msg, y, h))
            y += h + 4
        self.scroll.set_content_height(max(0, y - 4))
        prev = surface.get_clip()
        surface.set_clip(view)
        for m, lines, msg, top, h in cards:
            cy = view.y + top - self.scroll.offset
            if cy > view.bottom or cy + h < view.y:
                continue
            card = pygame.Rect(view.x, cy, card_w, h)
            draw_panel(surface, assets, card, "panel_light")
            ty = cy + 8
            for line in lines:
                draw_text(surface, line, (card.x + 8, ty), INK)
                ty += LH
            ty += 2
            stage = "QUEUED" if m.state == "queued" else (m.stage.upper() if m.stage else "IN PROGRESS")
            draw_text(surface, stage, (card.x + 8, ty), GOLD, kind="small")
            if m.agent_tag:
                draw_text(surface, m.agent_tag, (card.right - 8, ty), TEXT_FAINT, kind="small", align="right")
            ty += LH + 4
            elapsed = m.elapsed(now)
            progress = m.progress if m.progress is not None else min(0.95, elapsed / MISSION_SECONDS)
            signal = m.signal()
            draw_sprite_or_box(surface, assets, "icon_hammer", card.x + 8, ty - 2, (16, 16), t)
            bar = pygame.Rect(card.x + 28, ty, card.w - 28 - 6 - 48, 12)
            ProgressBar.draw(surface, assets, bar, progress, signal_color(signal), t, shimmer=True, pulse=signal is None)
            draw_text(surface, fmt_elapsed(elapsed), (card.right - 6, ty + 2), INK, align="right")
            ty += 12 + 4
            if msg:
                draw_text(surface, msg, (card.x + 8, ty), PARCHMENT_DARK, kind="small")
        surface.set_clip(prev)
        self.scroll.draw_scrollbar(surface, assets, view.right + 2, t)

    # -- queue ---------------------------------------------------------------
    def _draw_queue(self, surface, t, dx):
        assets = self.app.assets
        draw_panel(surface, assets, PANEL.move(dx, 0))
        snap = self.app.data.snapshot()
        n = len(snap.queue)
        self._draw_title(surface, "MISSION QUEUE", dx, f"{n} hypothes{'is' if n == 1 else 'es'} waiting")
        self._footer(surface, "Wheel/arrows/PgUp/PgDn: scroll   Esc: back", dx)
        if not snap.queue:
            self.scroll.set_content_height(0)
            self._draw_empty(surface, "The scroll is blank - nothing queued.", dx)
            return
        view = self.list_view.move(dx, 0)
        view = pygame.Rect(view.x, view.y + 10, view.w, view.h - 10)
        num_w = text_size(f"{n}.", "small")[0] + 6
        row_h = 2 * LH + 5
        self.scroll.viewport = view.move(-dx, 0)
        self.scroll.set_content_height(n * row_h - 3)
        prev = surface.get_clip()
        surface.set_clip(view)
        first = max(0, self.scroll.offset // row_h)
        for i in range(first, min(n, first + view.h // row_h + 2)):
            y = view.y + i * row_h - self.scroll.offset
            if i % 2 == 0:
                pygame.draw.rect(surface, WOOD_DARK, (view.x, y - 2, view.w, row_h - 1))
            draw_text(surface, f"{i + 1}.", (view.x + num_w - 6, y), GOLD, kind="small", align="right")
            item = snap.queue_items[i] if i < len(snap.queue_items) else QueueItem(snap.queue[i])
            x = view.x + num_w
            if item.round:
                draw_text(surface, item.round, (x, y), GOLD, kind="small")
                x += text_size(item.round, "small")[0] + 4
            if item.parent_mission_id:
                draw_text(surface, item.parent_mission_id, (x, y), TEXT_FAINT, kind="small")
                x += text_size(item.parent_mission_id, "small")[0] + 4
            for j, line in enumerate(clip_lines(item.text, view.right - 8 - x, 2)):
                draw_text(surface, line, (x, y + j * LH), TEXT if j == 0 else TEXT_DIM)
        surface.set_clip(prev)
        self.scroll.draw_scrollbar(surface, assets, view.right + 2, t)

    # -- completed -----------------------------------------------------------
    def _draw_completed(self, surface, t, dx):
        assets = self.app.assets
        draw_panel(surface, assets, PANEL.move(dx, 0))
        snap = self.app.data.snapshot()
        rows = self.completed_rows()
        arrow = "v" if self.sort_desc else "^"
        label = SORT_KEYS[self.sort_index][0]
        self._draw_title(surface, "COMPLETED MISSIONS", dx,
                         f"{len(rows)} missions   {len(snap.succeeded)} ok   sort: {label} {arrow}")
        self._footer(surface, "Enter: details   T: sort by   D: asc/desc   Esc: back", dx)
        header_bottom = PANEL.y + 10 + text_size("COMPLETED MISSIONS", "title")[1] + 17
        self.scroll.viewport = pygame.Rect(self.list_view.x, max(self.list_view.y + 10, header_bottom),
                                           self.list_view.w, self.list_view.y + self.list_view.h
                                           - max(self.list_view.y + 10, header_bottom))
        view = self.scroll.viewport.move(dx, 0)
        if not rows:
            self.scroll.set_content_height(0)
            self._row_tops = []
            self._draw_empty(surface, "No missions have returned yet.", dx)
            return
        self.selected = max(0, min(self.selected, len(rows) - 1))
        thumb_w, thumb_h = 48, 27
        row_h = 3 * LH + LH + 8  # folder + 2 hyp lines + stats + padding
        self._row_tops = [(i * (row_h + 3), row_h) for i in range(len(rows))]
        self.scroll.set_content_height(len(rows) * (row_h + 3) - 3)
        prev = surface.get_clip()
        surface.set_clip(view)
        for i, m in enumerate(rows):
            top, _ = self._row_tops[i]
            y = view.y + top - self.scroll.offset
            if y > view.bottom or y + row_h < view.y:
                continue
            row = pygame.Rect(view.x, y, view.w, row_h)
            tint = RED if m.failed else GREEN if m.status == "ok" else AMBER
            if i == self.selected:
                pygame.draw.rect(surface, OUTLINE, row)
                pygame.draw.rect(surface, lerp_color(WOOD_DARK, GOLD, 0.18), row.inflate(-2, -2))
            else:
                pygame.draw.rect(surface, lerp_color(WOOD_DARK, tint, 0.12), row)
            pygame.draw.rect(surface, tint, (row.x, row.y, 2, row.h))
            tx = row.x + 6
            has_thumb = m.viz_path is not None
            text_right = row.right - thumb_w - 10 if has_thumb else row.right - 6
            row_text_w = max(24, text_right - tx)
            viu = f"V/I/U={fmt_num(m.validity, 1)}/{fmt_num(m.interestingness, 1)}/{fmt_num(m.unexpectedness, 1)}"
            if m.actionability is not None:
                viu += f"/A={fmt_num(m.actionability, 1)}"
            viu_w = text_size(viu, "small")[0]
            draw_text(surface, viu, (tx + row_text_w, y + 3), TEXT_FAINT, kind="small", align="right")
            draw_text(surface, clip_lines(m.folder, row_text_w - viu_w - 8, 1, "small")[0], (tx, y + 3), TEXT_FAINT,
                      kind="small")
            lines = clip_lines(m.hypothesis or "(no hypothesis)", row_text_w, 2)
            for j, line in enumerate(lines):
                draw_text(surface, line, (tx, y + 3 + LH * (j + 1)), TEXT)
            lag = str(m.best_lag) if m.best_lag is not None else "-"
            stats = (f"n={m.n_obs if m.n_obs is not None else '-'}  r={fmt_num(m.r, 3)}  p={fmt_num(m.perm_p, 3)}  "
                     f"lag={lag}")
            if m.failed:
                stats = "FAILED  " + stats
            elif m.status != "ok":
                stats = f"{m.status.upper()}  " + stats
            draw_text(surface, clip_lines(stats, row_text_w, 1, "small")[0], (tx, y + 3 + LH * 3),
                      lerp_color(tint, GOLD_LIGHT, 0.45), kind="small")
            if has_thumb:
                draw_thumbnail(surface, self.thumbs.get(m.viz_path, (thumb_w, thumb_h)), row.right - thumb_w - 4,
                               y + (row_h - thumb_h) // 2, (thumb_w, thumb_h))
        surface.set_clip(prev)
        self.scroll.draw_scrollbar(surface, assets, view.right + 2, t)
        if self.selected < len(self._row_tops):
            top, _ = self._row_tops[self.selected]
            hy = view.y + top - self.scroll.offset + row_h // 2
            if view.y <= hy <= view.bottom:
                draw_cursor_hand(surface, assets, view.x - 3, hy, t)

    # -- detail --------------------------------------------------------------
    def _small_button(self, surface, rect: pygame.Rect, label: str, icon_done: Optional[bool] = None, hot=False):
        pygame.draw.rect(surface, OUTLINE, rect)
        pygame.draw.rect(surface, lerp_color(WOOD_DARK, GOLD, 0.35 if hot else 0.15), rect.inflate(-2, -2))
        x = rect.x + 4
        if icon_done is not None:
            draw_clipboard_icon(surface, x, rect.y + 1, icon_done)
            x += 12
        draw_text(surface, label, (x, rect.y + 2), GOLD_LIGHT if not hot else GREEN, kind="small")

    def _draw_detail(self, surface, t, dx):
        assets = self.app.assets
        m = self.detail
        panel = PANEL.move(dx, 0)
        draw_panel(surface, assets, panel)
        self._footer(surface, "Enter: zoom chart   N: note   C: copy   Esc: back", dx)
        if m is None:
            return
        tint = RED if m.failed else GREEN
        x0, y0 = panel.x + 12, panel.y + 10
        draw_text(surface, m.status.upper(), (x0, y0), tint, kind="title", shadow=OUTLINE)
        sw = text_size(m.status.upper(), "title")[0]
        ident = m.mission_id or m.folder
        draw_text(surface, clip_lines(ident, COPY_BUTTON.x - 8 - (x0 + sw + 8), 1, "small")[0],
                  (x0 + sw + 8, y0 + 4), TEXT_FAINT, kind="small")
        copied = t < self.copied_until
        self._small_button(surface, COPY_BUTTON.move(dx, 0), "copied!" if copied else "copy cmd", copied, copied)
        pygame.draw.line(surface, GOLD, (x0, y0 + 16), (panel.right - 12, y0 + 16))

        # the chart is the centrepiece: smooth (unquantized) and click-to-zoom
        chart = CHART.move(dx, 0)
        pygame.draw.rect(surface, OUTLINE, chart.inflate(4, 4))
        img = self.thumbs.source(m.viz_path)
        if img is not None:
            surface.blit(scaled_region(img, chart.size, 1.0, (0.5, 0.5)), chart.topleft)
        else:
            pygame.draw.rect(surface, SHADOW, chart)
            draw_text(surface, "no chart", chart.center, TEXT_FAINT, kind="small", align="center")

        # compact stats column on the right
        sx = chart.right + 12
        sw_col = panel.right - 12 - sx
        stats = [
            ("n", str(m.n_obs) if m.n_obs is not None else "-"),
            ("r", fmt_num(m.r, 3)),
            ("perm p", fmt_num(m.perm_p, 3)),
            ("validity", fmt_num(m.validity, 1)),
            ("interest", fmt_num(m.interestingness, 1)),
            ("unexpect", fmt_num(m.unexpectedness, 1)),
        ]
        if m.actionability is not None:
            stats.append(("action", fmt_num(m.actionability, 1)))
        y = chart.y
        for k, v in stats:
            draw_text(surface, k, (sx, y), TEXT_DIM, kind="small")
            draw_text(surface, v, (sx + sw_col, y), GOLD_LIGHT, kind="small", align="right")
            y += LH + 2
        sig = m.signal()
        pygame.draw.rect(surface, OUTLINE, (sx, y + 2, sw_col, 6))
        pygame.draw.rect(surface, signal_color(sig), (sx + 1, y + 3, max(0, int((sw_col - 2) * (sig or 0))), 4))
        draw_text(surface, "signal", (sx, y + 11), TEXT_FAINT, kind="small")
        if isinstance(m.trade_idea, dict):
            ti = m.trade_idea
            inst, direction = ti.get("instrument"), ti.get("direction")
            hit, avg = ti.get("hit_rate"), ti.get("avg_return")
            trade = (f"{inst if isinstance(inst, str) and inst else '-'} "
                     f"{direction if isinstance(direction, str) and direction else '-'}  "
                     f"hit {f'{hit:.0%}' if isinstance(hit, (int, float)) else '-'}  "
                     f"avg {f'{avg:+.2%}' if isinstance(avg, (int, float)) else '-'}")
            for j, line in enumerate(clip_lines(trade, sw_col, 2, "small")):
                draw_text(surface, line, (sx, y + 20 + j * (LH - 2)), GOLD, kind="small")
        self._small_button(surface, NOTE_BUTTON.move(dx, 0), "read note")

        # hypothesis under the chart, two lines max
        hy = chart.bottom + 6
        for line in clip_lines(m.hypothesis or "(no hypothesis)", chart.w, 2):
            draw_text(surface, line, (chart.x, hy), TEXT)
            hy += LH

    def _draw_note(self, surface, t, dx):
        assets = self.app.assets
        panel = PANEL.move(dx, 0)
        draw_panel(surface, assets, panel)
        self._footer(surface, "Wheel/arrows: scroll   Esc: back", dx)
        m = self.detail
        if m is None:
            return
        draw_text(surface, "MISSION NOTE", (panel.x + 12, panel.y + 10), GOLD_LIGHT, kind="title", shadow=OUTLINE)
        self.note_panel.draw(surface, assets, INK, dx, 0)

    def _draw_zoom(self, surface, t, dx):
        m = self.detail
        pygame.draw.rect(surface, OUTLINE, ZOOM_VIEW.inflate(4, 4))
        img = self.thumbs.source(m.viz_path) if m is not None else None
        if img is None:
            pygame.draw.rect(surface, SHADOW, ZOOM_VIEW)
            draw_text(surface, "no chart for this mission", ZOOM_VIEW.center, TEXT_FAINT, align="center")
        else:
            key = (round(self.zoom, 3), round(self.zoom_center[0], 3), round(self.zoom_center[1], 3), id(img))
            if self._zoom_cache is None or self._zoom_cache[0] != key:
                self._zoom_cache = (key, scaled_region(img, ZOOM_VIEW.size, self.zoom, self.zoom_center))
            surface.blit(self._zoom_cache[1], ZOOM_VIEW.topleft)
        draw_text(surface, f"x{self.zoom:.2f}   Wheel/+/-: zoom   Drag: pan   0: reset   Esc: back",
                  (LOGICAL_W // 2, LOGICAL_H - 12), TEXT_DIM, kind="small", shadow=OUTLINE, align="center")
