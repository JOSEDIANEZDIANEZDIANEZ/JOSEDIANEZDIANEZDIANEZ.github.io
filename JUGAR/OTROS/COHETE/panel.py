"""Panel de control en pantalla: palanca de acelerador y botones para salvar el vuelo."""
import pygame
from ui import *
from faults import FAULT_INFO

PX, PY, PW, PH = 930, 76, 340, 444


class ControlPanel:
    def __init__(self):
        self.slider = pygame.Rect(PX + 24, PY + 52, 46, 270)
        bx, bw = PX + 100, PW - 116
        self.b_left = pygame.Rect(bx, PY + 36, bw // 2 - 3, 38)
        self.b_right = pygame.Rect(bx + bw // 2 + 3, PY + 36, bw // 2 - 3, 38)
        names = ["cool", "vent", "reset", "sep", "auto", "engine", "warp"]
        self.btn = {}
        y = PY + 84
        for n in names:
            self.btn[n] = pygame.Rect(bx, y, bw, 40)
            y += 46
        self.dragging = False

    # ------------------------------------------------------------ eventos
    def handle(self, event, sim, flight, snd):
        if sim.status != "flying":
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.slider.inflate(30, 20).collidepoint(event.pos):
                self.dragging = True
                self.set_from_mouse(event.pos[1], sim)
                return True
            p = event.pos
            if self.btn["reset"].collidepoint(p):
                flight.reset_pulse = True
                snd.play("click")
                return True
            if self.btn["sep"].collidepoint(p):
                sim.separate()
                return True
            if self.btn["auto"].collidepoint(p):
                sim.autopilot = not sim.autopilot
                if not sim.autopilot:
                    sim.pitch_cmd = sim.pitch
                sim.say("Piloto automático " + ("ACTIVADO" if sim.autopilot else "DESACTIVADO"), "info")
                snd.play("click")
                return True
            if self.btn["engine"].collidepoint(p):
                sim.toggle_engine()
                return True
            if self.btn["warp"].collidepoint(p):
                flight.warp_i = (flight.warp_i + 1) % 4
                snd.play("click")
                return True
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from_mouse(event.pos[1], sim)
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        return False

    def set_from_mouse(self, y, sim):
        f = 1 - (y - self.slider.y) / self.slider.h
        sim.throttle = max(0.0, min(1.0, round(f * 20) / 20))

    def ctl(self, sim):
        """Contribución del ratón a los controles (botones mantenidos)."""
        c = {}
        if sim.status != "flying" or not pygame.mouse.get_pressed()[0]:
            return c
        m = pygame.mouse.get_pos()
        if self.btn["cool"].collidepoint(m):
            c["coolant"] = True
        if self.btn["vent"].collidepoint(m):
            c["vent"] = True
        if self.b_left.collidepoint(m):
            c["pitch"] = -1
        if self.b_right.collidepoint(m):
            c["pitch"] = 1
        return c

    # ------------------------------------------------------------ dibujo
    def draw(self, surf, sim, mouse, warp):
        if sim.status != "flying":
            return
        ov = pygame.Surface((PW, PH), pygame.SRCALPHA)
        pygame.draw.rect(ov, (10, 13, 20, 215), (0, 0, PW, PH), border_radius=10)
        surf.blit(ov, (PX, PY))
        pygame.draw.rect(surf, ACCENT, (PX, PY, PW, PH), 2, border_radius=10)
        text(surf, "PANEL DE CONTROL", (PX + PW // 2, PY + 8), 14, ACCENT, True, "midtop")
        blink = (pygame.time.get_ticks() // 350) % 2 == 0
        act = sim.faults.active
        # palanca de acelerador
        r = self.slider
        text(surf, "ACELERADOR", (r.centerx, PY + 30), 11, DIM, True, "midtop")
        pygame.draw.rect(surf, (45, 50, 66), r, border_radius=8)
        if "pogo" in act:
            zone = pygame.Rect(r.x, r.y + int(r.h * (1 - 0.65)), r.w, int(r.h * 0.30))
            pygame.draw.rect(surf, (40, 150, 80) if blink else (30, 110, 60), zone, border_radius=4)
        fill_h = int(r.h * sim.throttle)
        pygame.draw.rect(surf, ACCENT, (r.x + 14, r.bottom - fill_h, r.w - 28, fill_h), border_radius=4)
        hy = r.bottom - fill_h
        pygame.draw.rect(surf, (235, 235, 240), (r.x - 6, hy - 9, r.w + 12, 18), border_radius=5)
        pygame.draw.line(surf, (90, 90, 100), (r.x - 2, hy), (r.right + 2, hy), 2)
        text(surf, f"{sim.throttle * 100:.0f}%", (r.centerx, r.bottom + 6), 16, TEXT, True, "midtop")
        text(surf, "arrastra", (r.centerx, r.bottom + 26), 11, DIM, False, "midtop")
        # botones
        def b(rect, label, color=PANEL2, hot=ACCENT, alert=False, sub=""):
            over = rect.collidepoint(mouse)
            col = hot if over else color
            if alert and blink:
                col = (200, 120, 20)
            panel(surf, rect, col, radius=6)
            text(surf, label, (rect.centerx, rect.centery - (7 if sub else 0)), 15, TEXT, True, "center")
            if sub:
                text(surf, sub, (rect.centerx, rect.centery + 9), 11, (210, 215, 225), False, "center")
        b(self.b_left, "◄ CABECEO", sub="A / ←")
        b(self.b_right, "CABECEO ►", sub="D / →")
        b(self.btn["cool"], "REFRIGERAR", alert="vibration" in act, sub=f"mantener · C · {sim.coolant:.0f}%")
        b(self.btn["vent"], "VENTEAR PRESIÓN", alert="pressure" in act, sub="mantener · V")
        cd = sim.faults.reset_cool
        b(self.btn["reset"], "REINICIAR SISTEMAS", alert="avionics" in act and cd <= 0,
          sub="R" if cd <= 0 else f"espera {cd:.0f}s")
        empty = sim.fuel_frac() <= 0.001 and sim.cur < sim.n_stages - 1
        b(self.btn["sep"], "SEPARAR ETAPA", (40, 100, 70) if empty else PANEL2, alert=empty, sub="ESPACIO")
        b(self.btn["auto"], "PILOTO AUTO: " + ("SÍ" if sim.autopilot else "NO"),
          (40, 100, 70) if sim.autopilot else PANEL2, sub="G")
        has_fuel = sim.cur < sim.n_stages and sim.prop[sim.cur] > 0
        b(self.btn["engine"], "ENCENDER MOTORES" if sim.engine_cut else "APAGAR MOTORES",
          (150, 50, 40) if not sim.engine_cut else (40, 120, 70), alert=sim.engine_cut and has_fuel, sub="E")
        b(self.btn["warp"], f"TIEMPO ×{[1, 2, 4, 8][warp]}", sub="T")
