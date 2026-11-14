"""Dibujo de la escena de vuelo: cielo, tierra, clima, cohete, explosiones."""
import math
import random
import copy
import pygame
from ui import W
from data import *
from rocketmodel import draw_rocket, rocket_height
from cities import CITIES

SCENE_H = 530


class Scene:
    def __init__(self, cfg, seed=0):
        self.cfg = cfg
        self.rng = random.Random(seed)
        self.stars = [(self.rng.randrange(W), self.rng.randrange(SCENE_H), self.rng.choice([1, 1, 2])) for _ in range(140)]
        self.clouds = [(self.rng.uniform(0, 1), self.rng.uniform(0, 1), self.rng.uniform(0.6, 1.6)) for _ in range(14)]
        self.rain = [(self.rng.randrange(W), self.rng.randrange(SCENE_H)) for _ in range(170)]
        self.particles = []
        self.debris = []
        self.shake = 0.0
        self.frame = 0
        self.scale = 0.9
        h = rocket_height(cfg, len(cfg["stages"]), 1.0)
        self.scale = max(0.22, min(0.55, 125 / max(h, 1)))   # el cohete se ve más pequeño que en el constructor
        self.fire_t = 0.0
        self.cache_key = None
        self.sprite = None
        self.bolt = None

    # ------------------------------------------------------------ eventos
    def handle_events(self, sim):
        for ev in sim.events:
            if ev[0] == "explosion":
                self.explode(sim)
            elif ev[0] == "sep":
                self.drop_stage(sim, ev[1])
        sim.events.clear()

    def explode(self, sim):
        self.shake = 1.0
        sc = 0.12 / (1 + max(sim.alt, 0) / 5000.0)
        for ci in sim.cities_hit:
            tx = W // 2 + (CITIES[ci][0] - sim.theta * EARTH_R) * sc
            for _ in range(14):
                self.particles.append([W // 2, 250, (tx - W // 2) + self.rng.uniform(-30, 30), self.rng.uniform(120, 260), 1.4, (255, 150, 40), 5])
        cx, cy = W // 2, 250
        for _ in range(180):
            a = self.rng.uniform(0, math.tau)
            v = self.rng.uniform(40, 420)
            col = self.rng.choice([(255, 220, 90), (255, 140, 40), (230, 70, 40), (90, 90, 95), (240, 240, 240)])
            self.particles.append([cx, cy, math.cos(a) * v, math.sin(a) * v, self.rng.uniform(0.8, 2.6), col, self.rng.uniform(2, 7)])

    def drop_stage(self, sim, idx):
        sub = copy.deepcopy(self.cfg)
        sub["stages"] = [self.cfg["stages"][idx]]
        sub.update(crewed=False, tower=False, fins=False, shield=False, name="")
        h = rocket_height(sub, 1, self.scale) + 40
        surf = pygame.Surface((160, int(h) + 40), pygame.SRCALPHA)
        draw_rocket(surf, sub, 80, surf.get_height() - 20, self.scale, 1)
        self.debris.append({"x": W / 2, "y": 330.0, "vx": self.rng.uniform(-30, 30), "vy": 40.0, "ang": 0.0,
                            "spin": self.rng.uniform(-40, 40), "surf": surf})
        for _ in range(25):
            self.particles.append([W // 2, 300, self.rng.uniform(-60, 60), self.rng.uniform(0, 100), 0.6, (255, 230, 150), 3])

    # ------------------------------------------------------------ dibujo
    def draw(self, surf, sim, dt):
        self.frame += 1
        if sim.status == "exploded":
            self.fire_t += dt
        w = sim.weather
        alt = max(sim.alt, 0)
        sky = w.sky_color(alt)
        scene = pygame.Surface((W, SCENE_H))
        scene.fill(sky)
        self.draw_stars(scene, w, alt)
        h_px = rocket_height(self.cfg, len(self.cfg["stages"]) - sim.cur, self.scale)
        ground_y = 250 + h_px / 2 + 8 + 105 * (1 - math.exp(-alt / 1500.0)) + 30 * (1 - math.exp(-alt / 150000.0))
        self.draw_ground(scene, w, alt, ground_y, sim)
        self.draw_clouds(scene, w, alt, sim)
        if sim.status != "exploded" and sim.status != "crashed":
            self.draw_rocket(scene, sim, h_px)
        self.draw_fx(scene, sim, dt)
        if w.rain and alt < 20000:
            self.draw_rain(scene, w, alt)
        if w.flash > 0:
            fl = pygame.Surface((W, SCENE_H), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(150 * w.flash)))
            scene.blit(fl, (0, 0))
            if w.flash > 0.5 and alt < 20000:
                self.draw_bolt(scene, w)
        ox = oy = 0
        if self.shake > 0:
            self.shake = max(0, self.shake - dt * 1.5)
            ox, oy = self.rng.randint(-8, 8) * self.shake, self.rng.randint(-8, 8) * self.shake
        surf.blit(scene, (ox, oy))

    def draw_stars(self, scene, w, alt):
        a = w.star_alpha(alt)
        if a <= 0.05:
            return
        for x, y, s in self.stars:
            c = int(220 * a)
            pygame.draw.circle(scene, (c, c, c), (x, y), s)

    def draw_ground(self, scene, w, alt, gy, sim):
        rpx = max(1100.0, 4200.0 / (1 + alt / 12000.0))
        cx = W // 2
        low = max(0.0, 1 - alt / 60000)
        day = w.daylight() * 0.8 + 0.2
        land = (int((50 + 20 * low) * day), int((110 - 10 * (1 - low)) * day), int((55 + 90 * (1 - low)) * day))
        sea = (int(30 * day), int(80 * day), int(170 * day))
        col = [land[i] * low + sea[i] * (1 - low) for i in range(3)]
        halo = pygame.Surface((W, SCENE_H), pygame.SRCALPHA)
        if alt > 8000:
            pygame.draw.circle(halo, (110, 170, 255, int(70 * day)), (cx, int(gy + rpx)), int(rpx + 14 + alt / 4000))
            scene.blit(halo, (0, 0))
        pygame.draw.circle(scene, tuple(int(c) for c in col), (cx, int(gy + rpx)), int(rpx))
        self.draw_cities(scene, w, alt, gy, rpx, sim)
        if alt < 4000:
            pad_h = max(0, 1 - alt / 800) * 18
            if pad_h > 0:
                pygame.draw.rect(scene, (90, 90, 96), (cx - 45, gy - 4, 90, 8))
                pygame.draw.rect(scene, (70, 70, 76), (cx - 60, gy - pad_h, 8, pad_h))
                pygame.draw.rect(scene, (70, 70, 76), (cx + 52, gy - pad_h, 8, pad_h))
            # marcas de movimiento horizontal
            off = (sim.theta * EARTH_R) % 120
            for k in range(-2, 12):
                x = k * 120 - off
                pygame.draw.line(scene, [int(c * 0.8) for c in col], (x, gy + 6), (x - 30, gy + 20), 2)

    def draw_cities(self, scene, w, alt, gy, rpx, sim):
        if alt > 250e3:
            return
        sc = 0.12 / (1 + alt / 5000.0)
        bf = 1.0 / (1 + alt / 25000.0)
        cx = W // 2
        dr = sim.theta * EARTH_R
        night = 1 - w.daylight()
        fire_on = sim.status == "exploded" and bool(sim.cities_hit)
        f = pygame.font.SysFont("dejavusans", 11)
        for i, (d, name, n) in enumerate(CITIES):
            px = cx + (d - dr) * sc
            if px < -120 or px > W + 120:
                continue
            dx = px - cx
            y = gy + rpx - math.sqrt(max(rpx * rpx - dx * dx, 1))
            burning = fire_on and i in sim.cities_hit and self.fire_t > 1.0
            rl = random.Random(i * 31)
            for k in range(n):
                bx = px + (k - n / 2) * 8 * bf
                bh = (7 + rl.randint(0, 18)) * bf
                bw = max(2, 6 * bf)
                if burning:
                    bh *= 0.35
                    pygame.draw.rect(scene, (35, 30, 30), (bx, y - bh, bw, bh))
                    fh = (10 + 14 * random.random()) * bf * 1.4
                    pygame.draw.polygon(scene, (255, 140, 30), [(bx - bw, y - bh), (bx + bw * 2, y - bh), (bx + bw * 0.5, y - bh - fh)])
                    pygame.draw.polygon(scene, (255, 230, 90), [(bx, y - bh), (bx + bw, y - bh), (bx + bw * 0.5, y - bh - fh * 0.55)])
                    if random.random() < 0.15:
                        self.particles.append([bx, y - bh - fh, random.uniform(-10, 10), -random.uniform(20, 50), 1.5, (70, 70, 74), 4])
                else:
                    col = (95, 100, 120) if night < 0.5 else (30, 32, 44)
                    pygame.draw.rect(scene, col, (bx, y - bh, bw, bh))
                    if night > 0.4 and bh > 4:
                        pygame.draw.rect(scene, (255, 220, 120), (bx + 1, y - bh + 2, max(1, bw - 2), 2))
            if alt < 40000:
                label = name + ("  ¡EN LLAMAS!" if burning else "")
                img = f.render(label, True, (255, 120, 60) if burning else (230, 230, 235))
                scene.blit(img, (px - img.get_width() / 2, y + 6))

    def draw_clouds(self, scene, w, alt, sim):
        if alt > 22000 or w.cond == 0:
            return
        n = 8 if w.cond == 1 else 14
        shade = max(20, int(215 * (w.daylight() * 0.8 + 0.2) - (60 if w.cond >= 2 else 0)))
        col = (shade, shade, min(255, shade + 10))
        base = 250 + 165 * math.log10(1 + alt / 300) * 0 + 0
        for i in range(n):
            fx, fy, s = self.clouds[i]
            layer = 0.4 + fy
            x = (fx * W * 1.6 - sim.theta * EARTH_R * 0.08 * layer) % (W * 1.6) - W * 0.3
            cloud_alt = 1500 + fy * 9000
            y = 250 - (cloud_alt - alt) * 0.045 * (1 + 0.0 * layer)
            if -60 < y < SCENE_H + 40:
                for dx, dy, r in [(-30, 4, 24), (0, -8, 32), (34, 2, 26), (60, 8, 18)]:
                    pygame.draw.circle(scene, col, (int(x + dx * s), int(y + dy * s)), int(r * s))

    def draw_rocket(self, scene, sim, h_px):
        n = len(self.cfg["stages"]) - sim.cur
        thrusting = sim.status == "flying" and sim.thrust_now()[0] > 0
        flame = sim.throttle if thrusting else 0.0
        spr = pygame.Surface((300, 460), pygame.SRCALPHA)
        # nota: dibujamos el cohete con las etapas restantes (se reindexan)
        sub = copy.copy(self.cfg)
        sub["stages"] = self.cfg["stages"][sim.cur:]
        draw_rocket(spr, sub, 150, 230 + h_px / 2, self.scale, n, flame, pygame.font.SysFont("dejavusans", 11, bold=True), self.frame)
        ang = -sim.pitch if sim.status == "flying" else 0
        if abs(ang) > 0.1:
            spr = pygame.transform.rotate(spr, ang)
        # la plataforma gira con el cohete; usamos centro fijo
        rect = spr.get_rect(center=(W // 2, 250 + 0))
        scene.blit(spr, rect)

    def draw_fx(self, scene, sim, dt):
        for p in self.particles[:]:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 60 * dt
            p[4] -= dt
            if p[4] <= 0:
                self.particles.remove(p)
                continue
            pygame.draw.circle(scene, p[5], (int(p[0]), int(p[1])), max(1, int(p[6] * min(1, p[4]))))
        for d in self.debris[:]:
            d["x"] += d["vx"] * dt
            d["y"] += d["vy"] * dt
            d["vy"] += 90 * dt
            d["ang"] += d["spin"] * dt
            img = pygame.transform.rotate(d["surf"], d["ang"])
            scene.blit(img, img.get_rect(center=(d["x"], d["y"])))
            if d["y"] > SCENE_H + 250:
                self.debris.remove(d)

    def draw_rain(self, scene, w, alt):
        slant = 6 if w.wind_dir > 0 else -6
        for i, (x, y) in enumerate(self.rain):
            ny = (y + 14 + (i % 5)) % SCENE_H
            nx = (x + slant * 0.5) % W
            self.rain[i] = (nx, ny)
            pygame.draw.line(scene, (150, 170, 210), (nx, ny), (nx + slant, ny + 12), 1)

    def draw_bolt(self, scene, w):
        x = int(w.bolt_x * W)
        y = 0
        pts = [(x, y)]
        while y < 330:
            y += self.rng.randint(25, 50)
            x += self.rng.randint(-30, 30)
            pts.append((x, y))
        pygame.draw.lines(scene, (255, 255, 235), False, pts, 3)
