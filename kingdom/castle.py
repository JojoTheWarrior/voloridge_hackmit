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
from typing import Optional

import pygame

from .app import LOGICAL_H, LOGICAL_W, Scene
from .data import CompletedMission
from .text import draw_text, text_size
from .ui import (
    GOLD,
    GOLD_LIGHT,
    GREEN,
    INK,
    OUTLINE,
    RED,
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
    draw_cursor_hand,
    draw_panel,
    draw_sprite_or_box,
    draw_thumbnail,
    fmt_elapsed,
    fmt_num,
    lerp_color,
    signal_color,
)

MAIN, CURRENT, QUEUE, COMPLETED, DETAIL = "main", "current", "queue", "completed", "detail"
MENUS = (CURRENT, QUEUE, COMPLETED)
PANEL = pygame.Rect(50, 35, 380, 200)
SLIDE_SECONDS = 0.2
MISSION_SECONDS = 300.0  # missions take ~3-5 minutes
LH = 9  # line height of the 8px font


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
        self.note_panel = TextPanel(pygame.Rect(PANEL.x + 176, PANEL.y + 14, 192, 172))
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
        else:
            self.open_menu(MAIN, -1)

    def open_detail(self, mission: CompletedMission):
        self._detail_index = self.selected
        self._detail_scroll = self.scroll.offset
        self.detail = mission
        self.note_panel.set_text(mission.note_text() or "(no note written for this mission)")
        self.open_menu(DETAIL, 1)

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
        rows = self.app.data.snapshot().completed
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
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.back()
            return
        self.note_panel.handle_event(event)

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
        else:
            self._draw_detail(surface, t, dx)

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
        panel = pygame.Rect(LOGICAL_W // 2 - 130, PANEL.y + 10, 260, 172).move(dx, 0)
        draw_panel(surface, assets, panel)
        draw_sprite_or_box(surface, assets, "crest", panel.centerx - 16, panel.y - 14, (32, 32), t, (122, 47, 47))
        draw_text(surface, "GREAT HALL", (panel.centerx, panel.y + 20), GOLD_LIGHT, kind="title", shadow=OUTLINE, align="center")
        pygame.draw.line(surface, GOLD, (panel.x + 40, panel.y + 38), (panel.right - 41, panel.y + 38))
        for i, button in enumerate(self.buttons):
            button.draw(surface, assets, i == self.selected, t, dx, 0)
        sel = self.buttons[self.selected].rect.move(dx, 0)
        draw_cursor_hand(surface, assets, sel.x - 4, sel.centery, t)
        snap = self.app.data.snapshot()
        counts = f"{len(snap.active)} active   {len(snap.queue)} queued   {len(snap.completed)} done"
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
            lines = clip_lines(m.hypothesis, text_w, 3)
            h = 8 + len(lines) * LH + 6 + 12 + 8
            cards.append((m, lines, y, h))
            y += h + 4
        self.scroll.set_content_height(max(0, y - 4))
        prev = surface.get_clip()
        surface.set_clip(view)
        for m, lines, top, h in cards:
            cy = view.y + top - self.scroll.offset
            if cy > view.bottom or cy + h < view.y:
                continue
            card = pygame.Rect(view.x, cy, card_w, h)
            draw_panel(surface, assets, card, "panel_light")
            ty = cy + 8
            for line in lines:
                draw_text(surface, line, (card.x + 8, ty), INK)
                ty += LH
            ty += 4
            elapsed = m.elapsed(now)
            progress = min(0.95, elapsed / MISSION_SECONDS)
            signal = m.signal()
            bar = pygame.Rect(card.x + 8, ty, card_w - 16 - 44, 12)
            ProgressBar.draw(surface, assets, bar, progress, signal_color(signal), t, shimmer=True, pulse=signal is None)
            draw_sprite_or_box(surface, assets, "icon_hammer", card.right - 44, ty - 2, (16, 16), t)
            draw_text(surface, fmt_elapsed(elapsed), (card.right - 8, ty + 2), INK, align="right")
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
        text_w = view.w - num_w - 8
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
            for j, line in enumerate(clip_lines(snap.queue[i], text_w, 2)):
                draw_text(surface, line, (view.x + num_w, y + j * LH), TEXT if j == 0 else TEXT_DIM)
        surface.set_clip(prev)
        self.scroll.draw_scrollbar(surface, assets, view.right + 2, t)

    # -- completed -----------------------------------------------------------
    def _draw_completed(self, surface, t, dx):
        assets = self.app.assets
        draw_panel(surface, assets, PANEL.move(dx, 0))
        snap = self.app.data.snapshot()
        rows = snap.completed
        self._draw_title(surface, "COMPLETED MISSIONS", dx, f"{len(rows)} missions   {len(snap.succeeded)} ok")
        self._footer(surface, "Enter/click: details   Esc: back", dx)
        self.scroll.viewport = pygame.Rect(self.list_view.x, self.list_view.y + 10, self.list_view.w, self.list_view.h - 10)
        view = self.scroll.viewport.move(dx, 0)
        if not rows:
            self.scroll.set_content_height(0)
            self._row_tops = []
            self._draw_empty(surface, "No missions have returned yet.", dx)
            return
        self.selected = max(0, min(self.selected, len(rows) - 1))
        thumb_w, thumb_h = 48, 27
        text_w = view.w - thumb_w - 20
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
            tint = RED if m.failed else GREEN
            if i == self.selected:
                pygame.draw.rect(surface, OUTLINE, row)
                pygame.draw.rect(surface, lerp_color(WOOD_DARK, GOLD, 0.18), row.inflate(-2, -2))
            else:
                pygame.draw.rect(surface, lerp_color(WOOD_DARK, tint, 0.12), row)
            pygame.draw.rect(surface, tint, (row.x, row.y, 2, row.h))
            tx = row.x + 6
            draw_text(surface, m.folder, (tx, y + 3), TEXT_FAINT, kind="small")
            lines = clip_lines(m.hypothesis or "(no hypothesis)", text_w, 2)
            for j, line in enumerate(lines):
                draw_text(surface, line, (tx, y + 3 + LH * (j + 1)), TEXT)
            stats = (f"{m.status}  n={m.n_obs if m.n_obs is not None else '-'}  r={fmt_num(m.r, 3)}  "
                     f"p={fmt_num(m.perm_p, 3)}  V/I/U={fmt_num(m.validity, 1)}/"
                     f"{fmt_num(m.interestingness, 1)}/{fmt_num(m.unexpectedness, 1)}")
            draw_text(surface, stats, (tx, y + 3 + LH * 3), lerp_color(tint, GOLD_LIGHT, 0.45), kind="small")
            if m.viz_path is not None:
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
    def _draw_detail(self, surface, t, dx):
        assets = self.app.assets
        m = self.detail
        panel = PANEL.move(dx, 0)
        draw_panel(surface, assets, panel)
        self._footer(surface, "Wheel/arrows: scroll note   Esc: back", dx)
        if m is None:
            return
        left = pygame.Rect(panel.x + 12, panel.y + 12, 156, panel.h - 24)
        tint = RED if m.failed else GREEN
        draw_text(surface, m.status.upper(), (left.x, left.y), tint, kind="title", shadow=OUTLINE)
        draw_text(surface, m.mission_id or m.folder[:12], (left.right, left.y + 4), TEXT_FAINT, kind="small", align="right")
        y = left.y + 18
        pygame.draw.line(surface, GOLD, (left.x, y), (left.right, y))
        y += 4
        stats = [
            ("n", str(m.n_obs) if m.n_obs is not None else "-"),
            ("r", fmt_num(m.r, 3)),
            ("perm p", fmt_num(m.perm_p, 3)),
            ("validity", fmt_num(m.validity, 1)),
            ("interest", fmt_num(m.interestingness, 1)),
            ("unexpected", fmt_num(m.unexpectedness, 1)),
        ]
        col = left.w // 2
        for i, (k, v) in enumerate(stats):
            cx = left.x + (i % 2) * col
            cy = y + (i // 2) * LH
            draw_text(surface, k, (cx, cy), TEXT_DIM, kind="small")
            draw_text(surface, v, (cx + col - 6, cy), GOLD_LIGHT, kind="small", align="right")
        y += 3 * LH + 4
        thumb_w, thumb_h = 160, 90
        ty = left.bottom - thumb_h - 2
        hyp_lines = clip_lines(m.hypothesis or "(no hypothesis)", left.w, max(1, (ty - 4 - y) // LH))
        for line in hyp_lines:
            draw_text(surface, line, (left.x, y), TEXT)
            y += LH
        draw_thumbnail(surface, self.thumbs.get(m.viz_path, (thumb_w, thumb_h)), left.x - 2, ty, (thumb_w, thumb_h))
        self.note_panel.draw(surface, assets, INK, dx, 0)
