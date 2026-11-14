"""Fase 4: reentrada atmosférica (control manual del ángulo de ataque) y paracaídas."""
import math
import random
import pygame
from ui import *
from data import EARTH_R, EARTH_MU

DT = 1 / 30
MASS = 8000.0
AREA = 20.0
K_HEAT = 1.15e-7
CL_K = 0.15
CHUTE_CDA = 270.0
CHUTE_MAX_G = 6.0
T_INF = 9.0
PX, PY, PW, PH = 930, 76, 340, 444


def density(alt):
    return 1.225 * math.exp(-max(alt, 0) / 7500.0)


class Reentry:
    name = "REENTRADA"

    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.r = EARTH_R + 115e3
        self.theta = 0.0
        self.vr = -500.0
        self.vt = 6000.0
        self.alpha = 30.0
        self.t = 0.0
        self.temp = 20.0
        self.integrity = 100.0
        self.chute = 0          # 0 cerrado, 1 inflando, 2 abierto, -1 rasgado
        self.chute_t = 0.0
        self.status = "running"
        self.title = ""
        self.end_reason = ""
        self.events = []
        self.g = 0.0
        self.phase0 = self.rng.uniform(0, 6.28)
        self.dipped = False
        self.max_temp = 20.0
        self.landing_speed = 0.0
        self.log = [("Entrada en la atmósfera. Mantén el ángulo dentro de la banda verde.", "info")]
        self.flash = 0.0
        self.warn_t = 0.0
        self.ff = 1

    # ------------------------------------------------------------ cálculos
    @property
    def alt(self):
        return self.r - EARTH_R

    @property
    def speed(self):
        return math.hypot(self.vr, self.vt)

    def alpha_star(self):
        a = self.alt
        k = max(0.0, min(1.0, (a - 35000) / 75000.0))
        return 12 + 26 * k + 6 * math.sin(0.3 * self.t + self.phase0)

    def say(self, m, lvl="info"):
        self.log.append((m, lvl))
        self.log = self.log[-8:]

    def open_chute(self):
        if self.status != "running" or self.chute != 0:
            return
        if self.alt > 40000:
            self.say("Demasiado alto: el paracaídas no se puede abrir aún.", "warn")
            return
        q = 0.5 * density(self.alt) * self.speed ** 2
        if self.speed > 220 or q > 14000:
            self.chute = -1
            self.say("¡PARACAÍDAS RASGADO! Lo abriste demasiado pronto (demasiada velocidad).", "bad")
            self.events.append("tear")
        else:
            self.chute = 1
            self.chute_t = 0.0
            self.say("Paracaídas desplegándose...", "good")
            self.events.append("chute")

    def abort(self):
        if self.status == "running":
            self.fail("¡ABORTO! Autodestrucción de la nave.", "ABORTADA")

    def fail(self, why, title="MISIÓN FALLIDA"):
        self.status = "lost"
        self.title = title
        self.end_reason = why
        self.events.append("boom")
        self.flash = 1.0
        self.say(why, "bad")

    # ------------------------------------------------------------ bucle
    def update(self, dt, keys, mouse_ctl):
        if self.status != "running":
            self.flash = max(0.0, self.flash - dt)
            return
        pitch = keys.get("pitch", 0) + mouse_ctl.get("pitch", 0)
        ff = 3 if (self.chute == 0 and 8000 < self.alt < 38000) else 1
        self.ff = ff
        self._acc = getattr(self, "_acc", 0.0) + dt * 1.7 * ff
        n = 0
        while self._acc >= DT and n < 120:
            self.step(pitch)
            self._acc -= DT
            n += 1
            if self.status != "running":
                break

    def step(self, pitch):
        self.t += DT
        self.alpha = max(0.0, min(90.0, self.alpha + max(-1, min(1, pitch)) * 18.0 * DT))
        alt = self.alt
        rho = density(alt)
        v = max(self.speed, 0.1)
        sa = math.sin(math.radians(self.alpha))
        cd = 0.6 + 0.9 * sa
        cl = CL_K * math.sin(2 * math.radians(self.alpha))
        if self.chute == 0 or self.chute == -1:
            cda = cd * AREA
        else:
            cda = 1.2 * AREA
        drag = 0.5 * rho * v * v * cda
        lift = 0.5 * rho * v * v * cl * AREA if self.chute <= 0 else 0.0
        if self.chute > 0:
            self.chute_t += DT
            frac = min(1.0, self.chute_t / T_INF)
            self.chute = 2 if frac >= 1 else 1
            cp = 0.5 * rho * v * v * CHUTE_CDA * frac * frac
            drag += min(cp, MASS * CHUTE_MAX_G * 9.8)
        ar = self.vt ** 2 / self.r - EARTH_MU / self.r ** 2 + (lift * self.vt / v - drag * self.vr / v) / MASS
        at = -self.vr * self.vt / self.r + (-lift * self.vr / v - drag * self.vt / v) / MASS
        self.g = math.hypot(ar - (self.vt ** 2 / self.r - EARTH_MU / self.r ** 2), at + self.vr * self.vt / self.r) / 9.8
        self.vr += ar * DT
        self.vt += at * DT
        self.r += self.vr * DT
        self.theta += self.vt / self.r * DT
        # calor
        err = abs(self.alpha - self.alpha_star())
        flux = K_HEAT * math.sqrt(rho) * v ** 3
        teq = 20 + flux * (1 + (err / 6.0) ** 2)
        self.temp += (teq - self.temp) * DT / 9.0
        self.max_temp = max(self.max_temp, self.temp)
        if self.temp > 1200:
            self.integrity -= (self.temp - 1200) * 0.04 * DT
            self.warn_t += DT
            if self.warn_t > 3:
                self.say("¡ESCUDO TÉRMICO SOBRECALENTADO! Corrige el ángulo.", "bad")
                self.events.append("alarm")
                self.warn_t = 0.0
        if self.temp > 1700 or self.integrity <= 0:
            self.fail("La nave se ha desintegrado por el calor de la reentrada (ángulo incorrecto).", "SE HA QUEMADO")
            return
        if self.g > 16:
            self.fail("Fuerzas G excesivas: la nave se ha destruido.", "G EXCESIVAS")
            return
        if alt < 110e3:
            self.dipped = True
        if self.dipped and alt > 135e3 and self.vr > 0:
            self.fail("Rebote atmosférico: entraste con muy poco ángulo y la nave ha salido de nuevo al espacio.", "REBOTE")
            return
        if self.r <= EARTH_R:
            self.r = EARTH_R
            self.landing_speed = self.speed
            if self.chute == 2 and self.speed < 28:
                self.status = "won"
                self.title = "ATERRIZAJE COMPLETADO"
                self.end_reason = f"Aterrizaje suave a {self.speed:.0f} m/s. ¡Misión completa!"
                self.events.append("land")
                self.say(self.end_reason, "good")
            elif self.chute in (1, 2):
                self.fail(f"Abriste el paracaídas demasiado tarde: impacto a {self.speed:.0f} m/s.", "IMPACTO")
            else:
                self.fail(f"Te estrellaste a {self.speed:.0f} m/s sin paracaídas.", "IMPACTO")

    # ------------------------------------------------------------ dibujo
    def sky(self):
        k = max(0.0, min(1.0, 1 - self.alt / 90000.0))
        return (int(4 + 100 * k), int(6 + 150 * k), int(16 + 220 * k))

    def draw_scene(self, surf):
        scene = pygame.Surface((W, 530))
        scene.fill(self.sky())
        if self.alt > 20000:
            rs = random.Random(5)
            for _ in range(90):
                pygame.draw.circle(scene, (190, 190, 200), (rs.randrange(W), rs.randrange(380)), 1)
        cx = 460
        cy = 170
        gy = cy + 45 + self.alt * 0.014 if self.alt < 40000 else 9999
        if gy < 530:
            pygame.draw.rect(scene, (50, 105, 55), (0, gy, W, 530 - gy))
            for i in range(0, W, 90):
                pygame.draw.polygon(scene, (40, 90, 48), [(i - ((self.theta * 6.4e6) % 90), gy), (i + 45 - ((self.theta * 6.4e6) % 90), gy - 16), (i + 90 - ((self.theta * 6.4e6) % 90), gy)])
        # líneas de flujo
        sp = min(1.0, self.speed / 7000.0)
        for i in range(14):
            x = (i * 97 + self.t * 900 * sp) % 900
            y = 20 + (i * 53) % 340
            pygame.draw.line(scene, (255, 255, 255), (900 - x, y), (900 - x + 30 * sp, y), 1)
        self.draw_ship(scene, cx, cy)
        if self.flash > 0:
            pygame.draw.circle(scene, (255, 210, 120), (cx, cy), int(160 * (1.2 - self.flash)))
        surf.blit(scene, (0, 0))

    def draw_ship(self, scene, cx, cy):
        if self.status == "lost" and self.flash <= 0:
            return
        heat = max(0.0, min(1.0, (self.temp - 300) / 1300.0))
        ang = -self.alpha if self.alt > 35000 else 80
        spr = pygame.Surface((220, 160), pygame.SRCALPHA)
        if heat > 0.02:
            for k in range(6):
                pygame.draw.ellipse(spr, (255, 120 + 20 * k, 40, int(130 * heat)), (95 - k * 12, 40 - k * 4, 100 + k * 18, 80 + k * 8))
        pygame.draw.rect(spr, (235, 235, 240), (60, 60, 70, 40))
        pygame.draw.polygon(spr, (205, 50, 50), [(130, 60), (165, 80), (130, 100)])
        pygame.draw.rect(spr, (70, 50, 40), (52, 58, 10, 44))    # escudo térmico (parte trasera)
        img = pygame.transform.rotate(spr, ang)
        scene.blit(img, img.get_rect(center=(cx, cy)))
        if self.chute > 0:
            frac = min(1.0, self.chute_t / T_INF)
            w = 140 * frac
            pygame.draw.ellipse(scene, (240, 120, 40), (cx - w / 2, cy - 130 * frac - 20, w, 70 * frac))
            pygame.draw.line(scene, (200, 200, 200), (cx - w / 2 + 6, cy - 100 * frac), (cx, cy - 10), 1)
            pygame.draw.line(scene, (200, 200, 200), (cx + w / 2 - 6, cy - 100 * frac), (cx, cy - 10), 1)
        if self.chute == -1:
            pygame.draw.line(scene, (240, 120, 40), (cx, cy - 20), (cx + 40, cy - 90), 3)

    def draw_hud(self, surf):
        panel(surf, (0, 530, W, 190), (10, 13, 20), None, 0)
        pygame.draw.line(surf, ACCENT, (0, 530), (W, 530), 2)
        text(surf, "REENTRADA · TELEMETRÍA" + ("   (caída acelerada ×3)" if self.ff > 1 else ""), (14, 540), 13, ACCENT, True)
        rows = [("Altitud", f"{self.alt / 1000:,.1f} km", TEXT),
                ("Velocidad", f"{self.speed:,.0f} m/s", TEXT),
                ("Velocidad vertical", f"{self.vr:,.0f} m/s", TEXT),
                ("Fuerza G", f"{self.g:.1f} g", GOOD if self.g < 5 else (WARN if self.g < 10 else BAD)),
                ("Integridad", f"{self.integrity:.0f}%", GOOD if self.integrity > 60 else BAD)]
        for k, (a, b, c) in enumerate(rows):
            text(surf, a, (14, 564 + k * 22), 14, DIM)
            text(surf, b, (300, 564 + k * 22), 14, c, True, "topright")
        # temperatura
        text(surf, "Temp. escudo térmico", (340, 564), 14, DIM)
        col = GOOD if self.temp < 900 else (WARN if self.temp < 1200 else BAD)
        text(surf, f"{self.temp:,.0f} °C", (640, 564), 14, col, True, "topright")
        bar(surf, (340, 584, 300, 10), self.temp / 1700, col)
        # ángulo
        a, ast = self.alpha, self.alpha_star()
        text(surf, f"Ángulo de ataque: {a:.0f}°   ideal: {ast:.0f}°", (340, 606), 14, TEXT, True)
        gx, gw = 340, 300
        pygame.draw.rect(surf, (45, 50, 66), (gx, 630, gw, 14), border_radius=3)
        lo, hi = ast - 4, ast + 4
        pygame.draw.rect(surf, (40, 150, 80), (gx + gw * max(0, lo) / 90, 630, gw * (min(90, hi) - max(0, lo)) / 90, 14))
        pygame.draw.rect(surf, TEXT, (gx + gw * a / 90 - 2, 625, 4, 24))
        err = abs(a - ast)
        text(surf, "Error: %.0f°  → calor ×%.1f" % (err, 1 + (err / 6) ** 2), (340, 654), 13, GOOD if err < 4 else (WARN if err < 8 else BAD))
        # paracaídas
        st = {0: "CERRADO", 1: "ABRIÉNDOSE", 2: "ABIERTO", -1: "RASGADO"}[self.chute]
        text(surf, "Paracaídas: " + st, (700, 564), 15, GOOD if self.chute > 0 else (BAD if self.chute < 0 else TEXT), True)
        text(surf, "Zona segura: entre 7 y 2 km de altitud", (700, 586), 13, DIM)
        text(surf, "y por debajo de 220 m/s (ESPACIO)", (700, 604), 13, DIM)
        for k, (m, lvl) in enumerate(self.log[-5:]):
            text(surf, m[:70], (700, 630 + k * 16), 12, {"info": DIM, "good": GOOD, "warn": WARN, "bad": BAD}[lvl])

    # ------------------------------------------------------------ panel
    def rects(self):
        bx, bw = PX + 20, PW - 40
        return {"up": pygame.Rect(bx, PY + 40, bw, 62), "down": pygame.Rect(bx, PY + 112, bw, 62),
                "chute": pygame.Rect(bx, PY + 200, bw, 70)}

    def mouse_ctl(self):
        c = {}
        if self.status != "running" or not pygame.mouse.get_pressed()[0]:
            return c
        m, r = pygame.mouse.get_pos(), self.rects()
        if r["up"].collidepoint(m):
            c["pitch"] = 1
        if r["down"].collidepoint(m):
            c["pitch"] = -1
        return c

    def click(self, pos):
        if self.rects()["chute"].collidepoint(pos):
            self.open_chute()
            return True
        return False

    def draw_panel(self, surf, mouse):
        if self.status != "running":
            return
        ov = pygame.Surface((PW, PH), pygame.SRCALPHA)
        pygame.draw.rect(ov, (10, 13, 20, 215), (0, 0, PW, PH), border_radius=10)
        surf.blit(ov, (PX, PY))
        pygame.draw.rect(surf, ACCENT, (PX, PY, PW, PH), 2, border_radius=10)
        text(surf, "CONTROL DE REENTRADA", (PX + PW // 2, PY + 10), 15, ACCENT, True, "midtop")
        lab = {"up": ("▲ AUMENTAR ÁNGULO", "mantener · W / ↑"), "down": ("▼ REDUCIR ÁNGULO", "mantener · S / ↓"),
               "chute": ("ABRIR PARACAÍDAS", "ESPACIO · ni muy pronto ni muy tarde")}
        for k, r in self.rects().items():
            ok = k != "chute" or self.chute == 0
            blink = k == "chute" and 2000 < self.alt < 7000 and self.chute == 0 and (pygame.time.get_ticks() // 300) % 2 == 0
            col = (200, 120, 20) if blink else (ACCENT if r.collidepoint(mouse) and ok else PANEL2)
            panel(surf, r, col, radius=6)
            text(surf, lab[k][0], (r.centerx, r.centery - 9), 17, TEXT, True, "center")
            text(surf, lab[k][1], (r.centerx, r.centery + 13), 12, (210, 215, 225), False, "center")
        tips = ["Mantén el ángulo en la banda verde:",
                "el ideal cambia con la altitud y oscila,",
                "así que corrige sin parar. Poco ángulo",
                "= rebote o calor; mucho error = fuego.",
                "Entre 7 y 2 km abre el paracaídas."]
        for k, t in enumerate(tips):
            text(surf, t, (PX + 20, PY + 290 + k * 22), 13, DIM)
