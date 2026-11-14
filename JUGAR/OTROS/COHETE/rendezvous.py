"""Fase 3: acoplamiento con un satélite en órbita (movimiento relativo, ecuaciones de Clohessy-Wiltshire)."""
import math
import random
import pygame
from ui import *

DT = 1 / 30
N_ORB = 0.0003           # velocidad angular orbital efectiva (rad/s), reducida para jugar
RCS_ACC = 0.9            # m/s2
RCS_DV = 120.0           # m/s totales de combustible RCS
TURN = 35.0              # grados/s
CONTACT = 6.0            # m: distancia de contacto
PX, PY, PW, PH = 930, 76, 340, 444


class Rendezvous:
    name = "ACOPLAMIENTO"

    def __init__(self, seed=0):
        r = random.Random(seed)
        self.x = r.uniform(20, 40) * r.choice([-1, 1])      # radial (m), + = arriba
        self.y = -r.uniform(250, 350)                      # a lo largo de la órbita (m)
        d0 = math.hypot(self.x, self.y)
        v0 = r.uniform(2.5, 3.5)
        self.vx = -self.x / d0 * v0 + r.uniform(-0.15, 0.15)     # empiezas apuntando más o menos al satélite
        self.vy = -self.y / d0 * v0
        self.h = 0.0                                         # rumbo de la nave (grados, 0 = hacia delante)
        self.fuel = 100.0
        self.t = 0.0
        self.status = "running"      # running, won, lost
        self.title = ""
        self.end_reason = ""
        self.events = []
        self.log = [("Satélite detectado delante. Acércate despacio y alinea la nariz con el puerto.", "info")]
        self.stars = [(r.randrange(W), r.randrange(530), r.choice([1, 1, 2])) for _ in range(120)]
        self.trail = []
        self.thrusting = 0.0
        self.flash = 0.0
        self.won_timer = 0.0

    # ------------------------------------------------------------ cálculos
    @property
    def rng_(self):
        return math.hypot(self.x, self.y)

    def closing(self):
        d = self.rng_
        return -(self.x * self.vx + self.y * self.vy) / d if d > 0.01 else 0.0

    def rel_speed(self):
        return math.hypot(self.vx, self.vy)

    def heading_error(self):
        """Ángulo entre la nariz y la línea de visión al satélite."""
        los = math.degrees(math.atan2(-self.x, -self.y))
        e = (self.h - los + 180) % 360 - 180
        return e

    def cone_angle(self):
        """Ángulo respecto al eje del puerto del satélite (que mira hacia -y)."""
        return math.degrees(math.atan2(abs(self.x), -self.y)) if self.y < 0 else 90.0

    def safe_speed(self):
        return max(0.45, min(12.0, self.rng_ / 60.0 + 0.3))

    def say(self, m, lvl="info"):
        self.log.append((m, lvl))
        self.log = self.log[-8:]

    # ------------------------------------------------------------ bucle
    def abort(self):
        if self.status == "running":
            self.finish_fail("¡ABORTO! Autodestrucción de la nave.", "ABORTADA")

    def finish_fail(self, why, title="MISIÓN FALLIDA"):
        self.status = "lost"
        self.title = title
        self.end_reason = why
        self.events.append("boom")
        self.flash = 1.0
        self.say(why, "bad")

    def update(self, dt, keys, mouse_ctl):
        if self.status != "running":
            self.flash = max(0.0, self.flash - dt)
            self.won_timer += dt
            return
        rot = keys.get("rot", 0) + mouse_ctl.get("rot", 0)
        thr = keys.get("thr", 0) + mouse_ctl.get("thr", 0)
        self.thrusting = 0.0
        self._acc = getattr(self, "_acc", 0.0) + dt * 1.7
        n = 0
        while self._acc >= DT and n < 40:
            self.step(rot, thr)
            self._acc -= DT
            n += 1
            if self.status != "running":
                break

    def step(self, rot, thr):
        self.t += DT
        self.h = (self.h + max(-1, min(1, rot)) * TURN * DT) % 360
        ax = ay = 0.0
        thr = max(-1, min(1, thr))
        if thr and self.fuel > 0:
            a = RCS_ACC * thr
            ax = a * math.sin(math.radians(self.h))
            ay = a * math.cos(math.radians(self.h))
            self.fuel = max(0.0, self.fuel - abs(a) * DT / RCS_DV * 100)
            self.thrusting = thr
        n = N_ORB
        ax += 3 * n * n * self.x + 2 * n * self.vy
        ay += -2 * n * self.vx
        self.vx += ax * DT
        self.vy += ay * DT
        self.x += self.vx * DT
        self.y += self.vy * DT
        if self.t % 0.3 < DT:
            self.trail.append((self.x, self.y))
            self.trail = self.trail[-60:]
        d = self.rng_
        if d <= CONTACT:
            ok_v = self.rel_speed() < 1.2
            ok_h = abs(self.heading_error()) < 20
            ok_c = self.cone_angle() < 30
            if ok_v and ok_h and ok_c:
                self.status = "won"
                self.title = "ACOPLAMIENTO COMPLETADO"
                self.end_reason = "Acoplamiento suave con el satélite."
                self.events.append("dock")
                self.say("¡ACOPLAMIENTO COMPLETADO!", "good")
            else:
                why = "Colisión con el satélite: "
                why += "demasiada velocidad." if not ok_v else ("nariz mal alineada." if not ok_h else "aproximación fuera del eje del puerto.")
                self.finish_fail(why, "COLISIÓN")
        elif d > 6000:
            self.finish_fail("Has perdido de vista al satélite.", "OBJETIVO PERDIDO")
        elif self.fuel <= 0 and self.rel_speed() > 0 and self.t > 5:
            if self.closing() < 0.05 and d > 50:
                self.fuel_out = getattr(self, "fuel_out", 0.0) + DT
                if self.fuel_out > 20:
                    self.finish_fail("Sin combustible RCS y alejándote del satélite.", "SIN COMBUSTIBLE")

    # ------------------------------------------------------------ dibujo
    def draw_scene(self, surf):
        scene = pygame.Surface((W, 530))
        scene.fill((2, 3, 10))
        for sx, sy, s in self.stars:
            pygame.draw.circle(scene, (200, 200, 210), (sx, sy), s)
        pygame.draw.circle(scene, (25, 70, 150), (460, 530 + 3400), 3480)
        pygame.draw.circle(scene, (40, 100, 190), (460, 530 + 3400), 3400)
        cx, cy = 460, 255
        d = max(self.rng_, 0.1)
        s = max(0.04, min(14.0, 220.0 / d))
        tx, ty = cx - self.y * s, cy + self.x * s
        # estela
        pts = [(cx + (py - self.y) * s * -1 * -1, cy - (px - self.x) * s) for px, py in self.trail]
        pts = [(cx + (self.y - py) * s * -1 * -1 + 0, 0) for px, py in self.trail]
        for i, (px, py) in enumerate(self.trail):
            qx = tx + py * s
            qy = ty - px * s
            if 0 <= qx < 900 and 0 <= qy < 530:
                pygame.draw.circle(scene, (60, 90, 140), (int(qx), int(qy)), 2)
        # satélite
        self.draw_sat(scene, tx, ty, max(0.35, min(2.0, s * 0.9)))
        # línea de visión
        pygame.draw.line(scene, (50, 120, 80), (cx, cy), (tx, ty), 1)
        # vector de velocidad relativa
        vx_s, vy_s = -self.vy * 6, self.vx * 6
        pygame.draw.line(scene, WARN, (cx, cy), (cx + vx_s, cy + vy_s), 2)
        # nave
        self.draw_ship(scene, cx, cy)
        if self.flash > 0:
            pygame.draw.circle(scene, (255, 200, 100), (int(cx), int(cy)), int(120 * (1.2 - self.flash)))
        dist = f"{d / 1000:.2f} km" if d >= 1000 else f"{d:.0f} m"
        text(scene, "DISTANCIA AL SATÉLITE", (20, 16), 14, DIM, True)
        text(scene, dist, (20, 34), 40, TEXT, True)
        c = self.closing()
        if c > 0.3:
            eta = d / c
            text(scene, f"Llegada en ~{eta:.0f} s a la velocidad actual ({c:.1f} m/s)", (20, 82), 15, GOOD if eta < 400 else WARN)
        else:
            text(scene, "Sin acercamiento: empuja hacia el satélite", (20, 82), 15, WARN)
        text(scene, "Línea verde: hacia el satélite · línea naranja: tu movimiento relativo", (14, 505), 12, DIM)
        surf.blit(scene, (0, 0))

    def draw_sat(self, scene, x, y, k):
        pygame.draw.rect(scene, (180, 185, 195), (x - 18 * k, y - 14 * k, 36 * k, 28 * k))
        pygame.draw.rect(scene, (50, 90, 190), (x - 70 * k, y - 8 * k, 48 * k, 16 * k))
        pygame.draw.rect(scene, (50, 90, 190), (x + 22 * k, y - 8 * k, 48 * k, 16 * k))
        pygame.draw.rect(scene, (255, 210, 60), (x - 24 * k, y - 5 * k, 6 * k, 10 * k))   # puerto de acoplamiento (mira atrás)
        text(scene, "SATÉLITE", (x, y - 26 * k - 6), 12, TEXT, True, "midbottom")

    def draw_ship(self, scene, cx, cy):
        spr = pygame.Surface((90, 50), pygame.SRCALPHA)
        pygame.draw.rect(spr, (235, 235, 240), (10, 14, 50, 22))
        pygame.draw.polygon(spr, (205, 50, 50), [(60, 14), (84, 25), (60, 36)])
        pygame.draw.rect(spr, (90, 90, 98), (4, 18, 8, 14))
        if self.thrusting > 0:
            pygame.draw.polygon(spr, (255, 200, 90), [(4, 22), (-0, 25), (4, 28)])
        if self.thrusting < 0:
            pygame.draw.polygon(spr, (255, 200, 90), [(84, 23), (90, 25), (84, 27)])
        img = pygame.transform.rotate(spr, self.h)
        scene.blit(img, img.get_rect(center=(cx, cy)))

    def draw_hud(self, surf):
        panel(surf, (0, 530, W, 190), (10, 13, 20), None, 0)
        pygame.draw.line(surf, ACCENT, (0, 530), (W, 530), 2)
        text(surf, "ACOPLAMIENTO · TELEMETRÍA", (14, 540), 13, ACCENT, True)
        d, c, vs = self.rng_, self.closing(), self.safe_speed()
        he, ca = self.heading_error(), self.cone_angle()
        lat = abs(self.x) if self.y < 0 else abs(self.x)
        rows = [("Distancia al satélite", (f"{d / 1000:.2f} km" if d >= 1000 else f"{d:,.0f} m"), TEXT),
                ("Velocidad relativa", f"{self.rel_speed():.1f} m/s", GOOD if self.rel_speed() < vs * 1.3 else WARN),
                ("Velocidad de acercamiento", f"{c:.1f} m/s", GOOD if 0 <= c <= vs * 1.3 else (BAD if c > vs * 2 else WARN)),
                ("Velocidad máx. recomendada", f"{vs:.1f} m/s", DIM),
                ("Error de rumbo (nariz → satélite)", f"{he:+.0f}°", GOOD if abs(he) < 20 else (WARN if abs(he) < 40 else BAD)),
                ("Ángulo respecto al eje del puerto", f"{ca:.0f}°", GOOD if ca < 30 else WARN),
                ("Desviación lateral", f"{lat:,.0f} m", TEXT)]
        for k, (a, b, col) in enumerate(rows):
            text(surf, a, (14, 562 + k * 20), 14, DIM)
            text(surf, b, (350, 562 + k * 20), 14, col, True, "topright")
        text(surf, "Combustible RCS", (400, 562), 14, DIM)
        bar(surf, (400, 584, 220, 10), self.fuel / 100, ACCENT if self.fuel > 20 else BAD)
        text(surf, f"{self.fuel:.0f}%", (630, 578), 14, TEXT, True)
        text(surf, "Requisitos para acoplar (a < 6 m):", (400, 612), 14, ACCENT, True)
        reqs = [("Velocidad relativa < 1.2 m/s", self.rel_speed() < 1.2),
                ("Error de rumbo < 20°", abs(he) < 20),
                ("Dentro del cono del puerto (< 30°)", ca < 30)]
        for k, (a, ok) in enumerate(reqs):
            text(surf, ("✔ " if ok else "✘ ") + a, (400, 634 + k * 20), 14, GOOD if ok else DIM)
        for k, (m, lvl) in enumerate(self.log[-8:]):
            text(surf, m[:62], (700, 562 + k * 18), 12, {"info": DIM, "good": GOOD, "warn": WARN, "bad": BAD}[lvl])

    # ------------------------------------------------------------ panel
    def panel_rects(self):
        bx, bw = PX + 20, PW - 40
        return {"left": pygame.Rect(bx, PY + 40, bw // 2 - 4, 54), "right": pygame.Rect(bx + bw // 2 + 4, PY + 40, bw // 2 - 4, 54),
                "fwd": pygame.Rect(bx, PY + 110, bw, 54), "back": pygame.Rect(bx, PY + 176, bw, 54)}

    def mouse_ctl(self):
        c = {}
        if self.status != "running" or not pygame.mouse.get_pressed()[0]:
            return c
        m, r = pygame.mouse.get_pos(), self.panel_rects()
        if r["left"].collidepoint(m):
            c["rot"] = 1
        if r["right"].collidepoint(m):
            c["rot"] = -1
        if r["fwd"].collidepoint(m):
            c["thr"] = 1
        if r["back"].collidepoint(m):
            c["thr"] = -1
        return c

    def draw_panel(self, surf, mouse):
        if self.status != "running":
            return
        ov = pygame.Surface((PW, PH), pygame.SRCALPHA)
        pygame.draw.rect(ov, (10, 13, 20, 215), (0, 0, PW, PH), border_radius=10)
        surf.blit(ov, (PX, PY))
        pygame.draw.rect(surf, ACCENT, (PX, PY, PW, PH), 2, border_radius=10)
        text(surf, "CONTROL RCS", (PX + PW // 2, PY + 10), 15, ACCENT, True, "midtop")
        labels = {"left": ("◄ GIRAR", "A / ←"), "right": ("GIRAR ►", "D / →"),
                  "fwd": ("EMPUJAR ADELANTE", "mantener · W / ↑"), "back": ("FRENAR (empuje inverso)", "mantener · S / ↓")}
        for k, r in self.panel_rects().items():
            panel(surf, r, ACCENT if r.collidepoint(mouse) else PANEL2, radius=6)
            text(surf, labels[k][0], (r.centerx, r.centery - 8), 16, TEXT, True, "center")
            text(surf, labels[k][1], (r.centerx, r.centery + 12), 12, (210, 215, 225), False, "center")
        tips = ["1. Gira la nave (nariz = rumbo del empuje).",
                "    Mantén la línea naranja sobre la verde.",
                "2. Empuja para acercarte, frena antes",
                "    de llegar: ¡el empuje es inercial!",
                "3. Deja la velocidad < 1.2 m/s al",
                "    llegar, alineado con el puerto (►)."]
        for k, t in enumerate(tips):
            text(surf, t, (PX + 20, PY + 250 + k * 22), 13, DIM)
