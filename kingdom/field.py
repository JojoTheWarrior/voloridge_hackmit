"""Outdoor field scene: isometric grass field, castle, huts, workers, trees, water."""
from __future__ import annotations

import math
import random

import pygame

from .app import LOGICAL_H, LOGICAL_W, Scene
from .text import draw_text

TILE_W, TILE_H = 32, 16
MAP_R = 16
ORIGIN = (240.0, 150.0)  # world coords of tile (0, 0) top vertex
GROUND_OX = MAP_R * TILE_W + TILE_W // 2  # 528
GROUND_OY = MAP_R * TILE_H  # 256
GROUND_W = MAP_R * 2 * TILE_W + TILE_W  # 1056
GROUND_H = MAP_R * 2 * TILE_H + TILE_H  # 528

CASTLE_FALLBACK = (122, 131, 154)
FALLBACKS = {
    "grass": ((32, 16), (95, 154, 85)),
    "grass_flowers": ((32, 16), (95, 154, 85)),
    "path": ((32, 16), (178, 160, 118)),
    "field_crop": ((32, 16), (196, 170, 80)),
    "water": ((32, 16), (63, 143, 179)),
    "shore": ((32, 16), (206, 190, 140)),
    "castle": ((128, 128), CASTLE_FALLBACK),
    "castle_gate_open": ((128, 128), CASTLE_FALLBACK),
    "hut": ((32, 32), (154, 122, 78)),
    "workshop": ((48, 40), (140, 110, 70)),
    "worker": ((16, 16), (220, 180, 140)),
    "worker_b": ((16, 16), (200, 160, 150)),
    "tree": ((24, 32), (47, 93, 58)),
    "pine": ((24, 40), (38, 78, 55)),
    "bush": ((16, 12), (60, 110, 62)),
    "rock": ((16, 10), (130, 130, 140)),
    "flag": ((8, 16), (198, 64, 64)),
    "banner": ((16, 32), (188, 60, 60)),
    "monument": ((16, 24), (172, 172, 182)),
    "cloud": ((48, 20), (240, 244, 248)),
    "windmill": ((32, 48), (170, 140, 100)),
    "smoke": ((8, 8), (200, 200, 205)),
}

NEIGHBORS_NESW = ((0, -1), (1, 0), (0, 1), (-1, 0))


def iso(tx: float, ty: float) -> tuple[float, float]:
    return ORIGIN[0] + (tx - ty) * (TILE_W / 2), ORIGIN[1] + (tx + ty) * (TILE_H / 2)


def _ease(p: float) -> float:
    p = max(0.0, min(1.0, p))
    return p * p * (3.0 - 2.0 * p)


def land(tx: float, ty: float) -> bool:
    angle = math.atan2(ty, tx)
    r = math.hypot(tx * 1.0, ty * 1.15)
    return r < 10.5 + 0.9 * math.sin(3 * angle) + 0.5 * math.sin(7 * angle + 1)


class FieldScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.rng = random.Random(1234)
        self._build_map()
        self._build_slots()
        self.grounds = self._render_grounds()
        self.world_canvas = pygame.Surface((LOGICAL_W, LOGICAL_H)).convert()
        self.focus = [float(ORIGIN[0]), float(ORIGIN[1])]
        self.zoom = 1.0
        self.zoom_target = 1.0
        self.zoom_centre = [LOGICAL_W / 2, LOGICAL_H / 2]
        self.entering = False
        self.exiting = False
        self._zoom_t = 0.0
        self._visited_castle = False
        self.mouse_lpos = (0, 0)
        self.huts: list[dict] = []
        self._hut_count = -1
        self._flip_cache: dict = {}
        self._smoke_cache: dict = {}
        self._scale_cache: dict = {}
        self._cloud_shadows: dict = {}
        self.clouds = [
            {
                "x": self.rng.uniform(-100, LOGICAL_W + 60),
                "y": 18 + i * 16 + self.rng.uniform(-6, 6),
                "speed": self.rng.uniform(3.0, 5.0),
                "phase": self.rng.uniform(0, math.tau),
                "variant": i % 3,
            }
            for i in range(5)
        ]
        self.night = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.night.fill((20, 30, 70))
        self._hover_panel = pygame.Surface((96, 34), pygame.SRCALPHA)

    # -- map construction ---------------------------------------------------
    def _build_map(self):
        rng = random.Random(1234)
        self.tiles = {}
        for ty in range(-MAP_R, MAP_R + 1):
            for tx in range(-MAP_R, MAP_R + 1):
                is_land = land(tx, ty)
                variant = rng.randrange(3)
                flowers = rng.random() < 0.06
                self.tiles[(tx, ty)] = {"land": is_land, "variant": variant, "flowers": flowers}
        self.paths = set()
        for k in range(1, 7):
            self.paths.add((k, k))
        for j in range(1, 4):
            self.paths.add((6 + j, 6 - j))
            self.paths.add((6 - j, 6 + j))
        self.crops = set()
        for base in ((4, -4), (-4, 4)):
            for dx in (0, 1):
                for dy in (0, 1):
                    self.crops.add((base[0] + dx, base[1] + dy))

    def _build_slots(self):
        self.hut_slots = []
        for i in range(12):
            ang = math.radians(15 + i * 30)
            self.hut_slots.append((4.5 * math.cos(ang), 4.5 * math.sin(ang), ang))
        self.hut_slots.sort(key=lambda s: abs(math.atan2(math.sin(s[2] - math.pi / 4), math.cos(s[2] - math.pi / 4))))
        self.hut_slots = self.hut_slots[2:]
        self.monument_slots = [
            (7.5 * math.cos(math.radians(7.5 + i * 15)), 7.5 * math.sin(math.radians(7.5 + i * 15)))
            for i in range(24)
        ]
        rng = random.Random(777)
        occupied = set(self.paths) | set(self.crops)
        occupied |= {(tx, ty) for ty in range(-2, 3) for tx in range(-2, 3)}
        for sx, sy, _ in self.hut_slots:
            occupied.add((round(sx), round(sy)))
        for sx, sy in self.monument_slots:
            occupied.add((round(sx), round(sy)))
        occupied.add((-7, 3))
        self.scatter = []
        for (tx, ty), info in sorted(self.tiles.items()):
            if not info["land"] or (tx, ty) in occupied:
                continue
            if max(abs(tx), abs(ty)) > MAP_R - 1:
                continue
            near = any((tx + dx, ty + dy) in occupied for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            if near:
                continue
            roll = rng.random()
            tr = math.hypot(tx, ty * 1.15)
            if tr > 9 and roll < 0.35:
                self.scatter.append((tx, ty, "pine" if rng.random() < 0.3 else "tree", rng.random()))
            elif roll < 0.04:
                self.scatter.append((tx, ty, "rock" if rng.random() < 0.4 else "bush", rng.random()))

    def _sprite(self, name):
        size, color = FALLBACKS[name]
        return self.app.assets.get(name, size, color)

    def _render_grounds(self):
        grass = self._sprite("grass")
        flowers = self._sprite("grass_flowers")
        water = self._sprite("water")
        shore = self._sprite("shore")
        path = self._sprite("path")
        crop = self._sprite("field_crop")
        grounds = []
        for wf in range(4):
            surf = pygame.Surface((GROUND_W, GROUND_H), pygame.SRCALPHA)
            wframe = water.frames[wf % len(water.frames)]
            for (tx, ty), info in self.tiles.items():
                sx, sy = iso(tx, ty)
                px, py = int(sx - TILE_W / 2 + GROUND_OX), int(sy + GROUND_OY)
                if not info["land"]:
                    surf.blit(wframe, (px, py))
                    continue
                if (tx, ty) in self.paths:
                    surf.blit(path.frames[0], (px, py))
                    continue
                if (tx, ty) in self.crops:
                    surf.blit(crop.frames[(tx + ty) % len(crop.frames)], (px, py))
                    continue
                tile = flowers.frames[0] if info["flowers"] else grass.frames[info["variant"] % len(grass.frames)]
                surf.blit(tile, (px, py))
                for i, (dx, dy) in enumerate(NEIGHBORS_NESW):
                    if not self.tiles.get((tx + dx, ty + dy), {"land": False})["land"]:
                        surf.blit(shore.frames[i % len(shore.frames)], (px, py))
                        break
            grounds.append(surf)
        return grounds

    # -- camera -------------------------------------------------------------
    def _world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        return wx - self.focus[0] + LOGICAL_W / 2, wy - self.focus[1] + LOGICAL_H / 2

    def _castle_screen(self) -> tuple[float, float]:
        wx, wy = iso(0, 0)
        return self._world_to_screen(wx, wy + 8)

    def _castle_gate_screen(self) -> tuple[float, float]:
        cx, cy = self._castle_screen()
        return cx, cy - 20

    # -- events -------------------------------------------------------------
    def handle_event(self, event):
        if self.entering or self.exiting:
            return
        if event.type == pygame.MOUSEMOTION:
            self.mouse_lpos = event.lpos
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                cx, cy = self._castle_screen()
                if pygame.Rect(int(cx) - 64, int(cy) - 64, 128, 128).collidepoint(event.lpos):
                    self._start_enter()
            elif event.button in (4, 5):
                self._wheel(1 if event.button == 4 else -1, event.lpos)
        elif event.type == pygame.MOUSEWHEEL:
            self._wheel(event.y, self.app.logical_mouse(pygame.mouse.get_pos()))
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._start_enter()
            elif event.key == pygame.K_HOME:
                self.focus = [float(ORIGIN[0]), float(ORIGIN[1])]
                self.zoom_target = 1.0

    def _wheel(self, direction: int, lpos):
        if self.entering or self.exiting:
            return
        self.zoom_target = max(1.0, min(2.0, self.zoom_target + 0.2 * direction))
        if self.zoom_target > 1.0:
            self.zoom_centre[0] += (lpos[0] - self.zoom_centre[0]) * 0.5
            self.zoom_centre[1] += (lpos[1] - self.zoom_centre[1]) * 0.5

    def _start_enter(self):
        self.entering = True
        self._zoom_t = 0.0
        self._zoom_from = self.zoom

    def enter_castle(self):
        from .castle import CastleScene

        self._visited_castle = True
        self.app.push(CastleScene(self.app))

    def on_enter(self):
        if self._visited_castle:
            self.exiting = True
            self._zoom_t = 0.0
            self.zoom = 3.2

    # -- update -------------------------------------------------------------
    def update(self, dt: float, t: float):
        keys = pygame.key.get_pressed()
        pan = 120.0 * dt
        if keys[pygame.K_LEFT]:
            self.focus[0] -= pan
        if keys[pygame.K_RIGHT]:
            self.focus[0] += pan
        if keys[pygame.K_UP]:
            self.focus[1] -= pan
        if keys[pygame.K_DOWN]:
            self.focus[1] += pan
        self.focus[0] = max(ORIGIN[0] - 380, min(ORIGIN[0] + 380, self.focus[0]))
        self.focus[1] = max(ORIGIN[1] - 200, min(ORIGIN[1] + 220, self.focus[1]))

        if self.entering:
            self._zoom_t += dt
            p = _ease(self._zoom_t / 1.1)
            self.zoom = self._zoom_from + (3.2 - self._zoom_from) * p
            gx, gy = self._castle_gate_screen()
            self.zoom_centre[0] += (gx - self.zoom_centre[0]) * min(1.0, dt * 8)
            self.zoom_centre[1] += (gy - self.zoom_centre[1]) * min(1.0, dt * 8)
            if p >= 1.0:
                self.entering = False
                self.enter_castle()
        elif self.exiting:
            self._zoom_t += dt
            p = _ease(self._zoom_t / 0.9)
            self.zoom = 3.2 + (1.0 - 3.2) * p
            self.zoom_centre[0] += (LOGICAL_W / 2 - self.zoom_centre[0]) * min(1.0, dt * 8)
            self.zoom_centre[1] += (LOGICAL_H / 2 - self.zoom_centre[1]) * min(1.0, dt * 8)
            if p >= 1.0:
                self.exiting = False
                self.zoom = 1.0
                self.zoom_target = 1.0
                self.zoom_centre = [LOGICAL_W / 2, LOGICAL_H / 2]
        else:
            self.zoom += (self.zoom_target - self.zoom) * min(1.0, dt * 8)
            if abs(self.zoom - self.zoom_target) < 0.01:
                self.zoom = self.zoom_target
            if self.zoom <= 1.02:
                self.zoom_centre[0] += (LOGICAL_W / 2 - self.zoom_centre[0]) * min(1.0, dt * 4)
                self.zoom_centre[1] += (LOGICAL_H / 2 - self.zoom_centre[1]) * min(1.0, dt * 4)

        for cloud in self.clouds:
            cloud["x"] += cloud["speed"] * dt
            if cloud["x"] > LOGICAL_W + 80:
                cloud["x"] = -100

        snap = self.app.data.snapshot()
        n = len(snap.active)
        if n != self._hut_count:
            self._hut_count = n
            self.huts = []
            for i in range(min(n, len(self.hut_slots))):
                sx, sy, _ = self.hut_slots[i]
                wx, wy = iso(sx, sy)
                self.huts.append(
                    {
                        "pos": (wx, wy + 8),
                        "spawn": t - i * 0.08,
                        "index": i,
                        "phase": self.rng.uniform(0, math.tau),
                        "workshop": i % 4 == 3,
                    }
                )

    # -- draw ---------------------------------------------------------------
    def _flipped(self, frame, flip: bool):
        key = (id(frame), flip)
        if key not in self._flip_cache:
            self._flip_cache[key] = pygame.transform.flip(frame, True, False) if flip else frame
        return self._flip_cache[key]

    def _scaled(self, frame, w: int, h: int):
        key = (id(frame), w, h)
        if key not in self._scale_cache:
            self._scale_cache[key] = pygame.transform.scale(frame, (max(1, w), max(1, h)))
        return self._scale_cache[key]

    def _smoke(self, frame, step: int, alpha: int):
        key = (id(frame), step, alpha)
        if key not in self._smoke_cache:
            surf = frame.copy()
            surf.set_alpha(alpha)
            self._smoke_cache[key] = surf
        return self._smoke_cache[key]

    def _cloud_shadow(self, frame):
        key = id(frame)
        if key not in self._cloud_shadows:
            surf = frame.copy()
            surf.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surf.set_alpha(40)
            self._cloud_shadows[key] = surf
        return self._cloud_shadows[key]

    def draw(self, surface, t):
        snap = self.app.data.snapshot()
        world = self.world_canvas
        world.fill((40, 90, 120))
        wf = int(t * 2) % 4
        gx = LOGICAL_W / 2 - GROUND_OX - self.focus[0]
        gy = LOGICAL_H / 2 - GROUND_OY - self.focus[1]
        ground = self.grounds[wf]
        src = pygame.Rect(-int(gx), -int(gy), LOGICAL_W, LOGICAL_H).clip(ground.get_rect())
        world.blit(ground, (int(gx) + src.x, int(gy) + src.y), src)

        for cloud in self.clouds:
            spr = self._sprite("cloud")
            frame = spr.frames[cloud["variant"] % len(spr.frames)]
            shadow = self._cloud_shadow(frame)
            world.blit(shadow, (int(cloud["x"] + 6 - spr.anchor[0]), int(cloud["y"] + 26 - spr.anchor[1])))

        props = []
        self._queue_props(props, snap, t)
        props.sort(key=lambda p: p[0])
        for _, fn in props:
            fn()

        for cloud in self.clouds:
            spr = self._sprite("cloud")
            y = cloud["y"] + math.sin(t * 0.3 + cloud["phase"]) * 2
            world.blit(
                spr.frames[cloud["variant"] % len(spr.frames)],
                (int(cloud["x"] - spr.anchor[0]), int(y - spr.anchor[1])),
            )

        if self.zoom > 1.001:
            zw, zh = LOGICAL_W / self.zoom, LOGICAL_H / self.zoom
            rect = pygame.Rect(0, 0, int(zw), int(zh))
            rect.center = (int(self.zoom_centre[0]), int(self.zoom_centre[1]))
            rect.clamp_ip(world.get_rect())
            surface.blit(pygame.transform.scale(world.subsurface(rect), (LOGICAL_W, LOGICAL_H)), (0, 0))
        else:
            surface.blit(world, (0, 0))

        self.night.set_alpha(int(70 * (0.5 - 0.5 * math.cos(math.tau * t / 720))))
        surface.blit(self.night, (0, 0))
        self._draw_hud(surface, snap, t)

    def _queue_props(self, props, snap, t):
        cx, cy = self._castle_screen()
        castle_name = "castle_gate_open" if self.zoom >= 1.6 else "castle"
        castle = self._sprite(castle_name)
        hover = pygame.Rect(int(cx) - 64, int(cy) - 64, 128, 128).collidepoint(self.mouse_lpos)
        lift = 1 if hover else 0

        def draw_castle(cx=cx, cy=cy, castle=castle, hover=hover, lift=lift):
            castle.blit(world := self.world_canvas, cx, cy - lift, t)
            rect = pygame.Rect(int(cx) - castle.anchor[0], int(cy) - castle.anchor[1] - lift, castle.w, castle.h)
            flag = self._sprite("flag")
            flag.blit(world, cx - 30, cy - 96 - lift, t)
            flag.blit(world, cx + 30, cy - 96 - lift, t)
            self._sprite("banner").blit(world, cx, cy - 60 - lift, t)
            if hover:
                pygame.draw.rect(world, (238, 240, 244), rect, 1)

        props.append((cy, draw_castle))

        for hut in self.huts:
            hx, hy = self._world_to_screen(*hut["pos"])
            spr = self._sprite("workshop" if hut["workshop"] else "hut")
            p = _ease((t - hut["spawn"]) / 0.6)
            phase = hut["phase"]

            def draw_hut(hx=hx, hy=hy, spr=spr, p=p, phase=phase, idx=hut["index"]):
                world = self.world_canvas
                frame = spr.frames[idx % len(spr.frames)]
                w, h = int(spr.w * p), int(spr.h * p)
                if w > 0 and h > 0:
                    world.blit(self._scaled(frame, w, h), (int(hx - spr.anchor[0] * p), int(hy - spr.anchor[1] * p)))
                u = t * 0.6 + phase
                worker = self._sprite("worker" if idx % 2 == 0 else "worker_b")
                wframe = self._flipped(worker.frame(t, phase), math.cos(u) < 0)
                wx, wy = hx + 14 * math.sin(u), hy + 6 * math.sin(2 * u) - 4
                world.blit(wframe, (int(wx) - worker.anchor[0], int(wy) - worker.anchor[1]))
                smoke = self._sprite("smoke")
                off = (t * 8 + phase * 10) % 16
                sframe = self._smoke(smoke.frame(t, phase), int(off // 4), max(0, 255 - int(off * 14)))
                world.blit(sframe, (int(hx) + 6 - smoke.anchor[0], int(hy - spr.h + 6 - off) - smoke.anchor[1] + 8))
                if idx % 3 == 0:
                    self._sprite("flag").blit(world, hx - 14, hy - 2, t, phase)

            props.append((hy, draw_hut))

        for i, mission in enumerate(snap.completed[:24]):
            sx, sy = self.monument_slots[i]
            wx, wy = self._world_to_screen(*iso(sx, sy))
            wy += 8

            def draw_monument(wx=wx, wy=wy, i=i, failed=mission.failed):
                world = self.world_canvas
                if failed:
                    self._sprite("rock").blit(world, wx + 4, wy, t)
                    self._sprite("flag").blit(world, wx, wy, t, i)
                else:
                    mon = self._sprite("monument")
                    world.blit(
                        mon.frames[i % len(mon.frames)],
                        (int(wx) - mon.anchor[0], int(wy) - mon.anchor[1]),
                    )

            props.append((wy, draw_monument))

        for tx, ty, kind, seed in self.scatter:
            wx, wy = self._world_to_screen(*iso(tx, ty))
            wy += 8

            def draw_scatter(wx=wx, wy=wy, kind=kind, seed=seed):
                spr = self._sprite(kind)
                sway = round(math.sin(t * 0.7 + seed * math.tau)) if kind in ("tree", "pine") else 0
                spr.blit(self.world_canvas, wx + sway, wy, t, seed * 4)

            props.append((wy, draw_scatter))

        wx, wy = self._world_to_screen(*iso(-7, 3))
        props.append((wy + 8, lambda wx=wx, wy=wy: self._sprite("windmill").blit(self.world_canvas, wx, wy + 8, t)))

    def _draw_hud(self, surface, snap, t):
        failed = len(snap.failed) + sum(1 for m in snap.completed if m.failed)
        ok = sum(1 for m in snap.completed if not m.failed)
        lines = [
            f"Active  {len(snap.active)}",
            f"Queued  {len(snap.queue)}",
            f"Done    {ok} ok  {failed} failed",
        ]
        panel = pygame.Rect(4, 4, 118, 10 + len(lines) * 10)
        shade = pygame.Surface(panel.size, pygame.SRCALPHA)
        shade.fill((27, 31, 40, 200))
        surface.blit(shade, panel.topleft)
        pygame.draw.rect(surface, (27, 31, 40), panel, 2)
        for i, line in enumerate(lines):
            draw_text(surface, line, (10, 8 + i * 10), shadow=(10, 12, 18))
        alpha = int(140 + 90 * math.sin(t * 1.5))
        hint = pygame.Surface((LOGICAL_W, 14), pygame.SRCALPHA)
        draw_text(hint, "Click the castle or press Enter", (LOGICAL_W // 2, 2), (238, 240, 244),
                  shadow=(10, 12, 18), align="center")
        hint.set_alpha(alpha)
        surface.blit(hint, (0, LOGICAL_H - 14))
