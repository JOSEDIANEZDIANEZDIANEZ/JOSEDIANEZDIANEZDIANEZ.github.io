"""Etapa 2: prueba de vuelo con telemetría y controles."""
import math
import pygame
from data import *
from ui import *
from sim import Sim, DT
from scene import Scene, SCENE_H
from faults import FAULT_INFO
from weather import Weather
from panel import ControlPanel
from sound import Sounds
from rendezvous import Rendezvous
from reentry import Reentry
from cities import CITIES

TEL_Y = SCENE_H
WARPS = [1, 2, 4, 8]


def level_color(v, warn, bad):
    return BAD if v >= bad else (WARN if v >= warn else GOOD)


class FlightScreen:
    def __init__(self, cfg, snd=None):
        self.cfg = cfg
        self.snd = snd or Sounds()
        self.panel = ControlPanel()
        self.weather = Weather()
        self.new_sim()
        self.btn_abort = Button((W - 190, 12, 178, 54), "ABORTAR  (X)", (170, 30, 30), (240, 60, 50), 20)
        self.btn_start = Button((W // 2 - 270, 230, 250, 54), "INICIAR CUENTA ATRÁS", (40, 120, 70), (60, 170, 100), 17)
        self.btn_wait = Button((W // 2 + 10, 230, 260, 54), "Esperar (cambia el clima)", PANEL2, ACCENT, 16)
        self.btn_back = Button((W // 2 - 270, 300, 540, 44), "Volver al constructor (Esc)", PANEL2, ACCENT, 16)
        self.btn_res_build = Button((W // 2 - 270, 440, 260, 50), "Modificar cohete", PANEL2, ACCENT, 17)
        self.btn_res_retry = Button((W // 2 + 10, 440, 260, 50), "Repetir prueba", (40, 120, 70), (60, 170, 100), 17)
        self.warp_i = 0
        self.acc = 0.0

    def new_sim(self):
        self.sim = Sim(self.cfg, self.weather)
        self.scene = Scene(self.cfg)
        self.end_timer = 0.0
        self.warp_i = 0
        self.phase = "ascent"
        self.mod = None
        self.mod_end_t = 0.0
        self.orbit_timer = 0.0
        self.milestones = []
        self.total = 0

    def retry(self):
        self.snd.stop_all()
        self.weather = Weather()
        self.new_sim()

    # --------------------------------------------------------------- eventos
    def handle(self, event):
        if self.phase != "ascent":
            return self.handle_mod(event)
        s = self.sim
        pre = s.status == "pad"
        flying = s.status in ("countdown", "flying")
        if self.panel.handle(event, s, self, self.snd):
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.snd.toggle_mute()
        done = self.ascent_done()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and (pre or done):
                return "builder"
            if event.key == pygame.K_RETURN:
                if pre:
                    s.start_countdown()
                elif done:
                    self.retry()
            if event.key == pygame.K_x and (flying or pre):
                s.abort()
            if event.key == pygame.K_SPACE:
                s.separate()
            if event.key == pygame.K_g:
                s.autopilot = not s.autopilot
                if not s.autopilot:
                    s.pitch_cmd = s.pitch
                s.say("Piloto automático " + ("ACTIVADO" if s.autopilot else "DESACTIVADO"), "info")
            if event.key == pygame.K_t:
                self.warp_i = (self.warp_i + 1) % len(WARPS)
            if event.key == pygame.K_e and s.status == "flying":
                s.toggle_engine()
            if event.key == pygame.K_r and s.status == "flying":
                self.reset_pulse = True
        if pre:
            if self.btn_start.clicked(event):
                s.start_countdown()
            if self.btn_wait.clicked(event):
                for _ in range(120):
                    self.weather.update(1.0)
            if self.btn_back.clicked(event):
                return "builder"
        if self.btn_abort.clicked(event) and (flying or pre):
            s.abort()
        if done:
            if self.btn_res_build.clicked(event):
                return "builder"
            if self.btn_res_retry.clicked(event):
                self.retry()
        return None

    reset_pulse = False

    # --------------------------------------------------------------- bucle
    def update(self, dt):
        if self.phase != "ascent":
            return self.update_mod(dt)
        s = self.sim
        k = pygame.key.get_pressed()
        ctl = {
            "thr": (k[pygame.K_w] or k[pygame.K_UP]) - (k[pygame.K_s] or k[pygame.K_DOWN]),
            "pitch": (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT]),
            "coolant": k[pygame.K_c], "vent": k[pygame.K_v], "reset": self.reset_pulse,
        }
        mc = self.panel.ctl(s)
        ctl["coolant"] = ctl["coolant"] or mc.get("coolant", False)
        ctl["vent"] = ctl["vent"] or mc.get("vent", False)
        if mc.get("pitch"):
            ctl["pitch"] = mc["pitch"]
        self.snd.hold_hiss(s.status == "flying" and bool(ctl["coolant"] or ctl["vent"]))
        self.reset_pulse = False
        if s.status in ("countdown", "flying"):
            self.acc += dt * (WARPS[self.warp_i] * 1.7 if s.status == "flying" else 1)
            n = 0
            while self.acc >= DT and n < 60:
                s.update(ctl)
                ctl["reset"] = False
                self.acc -= DT
                n += 1
            self.acc = min(self.acc, DT)
        if s.status in ("exploded", "crashed"):
            self.end_timer += dt
            self.warp_i = 0
        if s.status == "orbit":
            self.warp_i = 0
            self.end_timer += dt
        self.snd.process(s, dt)
        self.scene.handle_events(s)
        if s.status == "orbit" and s.result == "orbita_alta":
            self.orbit_timer += dt
            if self.orbit_timer > 3.0:
                self.total = s.score()
                self.milestones.append("Órbita alta alcanzada")
                self.start_phase("rendezvous")

    # --------------------------------------------------------------- dibujo
    def draw(self, surf, mouse, dt):
        if self.phase != "ascent":
            return self.draw_mod(surf, mouse, dt)
        s = self.sim
        self.scene.draw(surf, s, dt)
        self.draw_telemetry(surf)
        self.draw_alerts(surf)
        self.panel.draw(surf, s, mouse, self.warp_i)
        if s.status in ("countdown", "flying", "pad"):
            self.btn_abort.draw(surf, mouse)
        if s.status == "pad":
            self.draw_prelaunch(surf, mouse)
        if s.status == "countdown":
            text(surf, f"{max(0, math.ceil(s.countdown))}", (W // 2, 140), 90, WARN, True, "center")
        if s.status == "orbit" and s.result == "orbita_alta":
            text(surf, "¡ÓRBITA ALTA ALCANZADA!", (W // 2, 90), 36, GOOD, True, "center")
            text(surf, "Preparando el acoplamiento con el satélite...", (W // 2, 130), 18, TEXT, False, "center")
        elif self.ascent_done():
            self.draw_result(surf, mouse)

    def ascent_done(self):
        s = self.sim
        if s.status == "orbit":
            return s.result != "orbita_alta"
        return s.status in ("exploded", "crashed", "aborted") and (self.end_timer > (5.5 if s.cities_hit else 2.0) or s.status == "aborted")

    # ------------------------------------------------------------ fases nuevas
    def start_phase(self, name):
        self.snd.stop_all()
        self.phase = name
        self.mod_end_t = 0.0
        self.mod = Rendezvous(self.rngseed()) if name == "rendezvous" else Reentry(self.rngseed())

    def rngseed(self):
        return int(pygame.time.get_ticks()) % 1000

    def mod_finished(self):
        m = self.mod
        if m.status == "lost":
            return self.mod_end_t > 1.5
        return m.status == "won" and self.phase == "reentry" and self.mod_end_t > 1.5

    def handle_mod(self, event):
        m = self.mod
        done = self.mod_finished()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                self.snd.toggle_mute()
            if event.key == pygame.K_x and m.status == "running":
                m.abort()
            if event.key == pygame.K_SPACE and self.phase == "reentry":
                m.open_chute()
            if done and event.key == pygame.K_ESCAPE:
                return "builder"
            if done and event.key == pygame.K_RETURN:
                self.retry()
        if self.btn_abort.clicked(event) and m.status == "running":
            m.abort()
        if self.phase == "reentry" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m.click(event.pos)
        if done:
            if self.btn_res_build.clicked(event):
                return "builder"
            if self.btn_res_retry.clicked(event):
                self.retry()
        return None

    def update_mod(self, dt):
        m = self.mod
        k = pygame.key.get_pressed()
        up = (k[pygame.K_w] or k[pygame.K_UP]) - (k[pygame.K_s] or k[pygame.K_DOWN])
        if self.phase == "rendezvous":
            keys = {"rot": (k[pygame.K_a] or k[pygame.K_LEFT]) - (k[pygame.K_d] or k[pygame.K_RIGHT]), "thr": up}
        else:
            keys = {"pitch": up}
        m.update(dt, keys, m.mouse_ctl())
        self.snd.hold_hiss(self.phase == "rendezvous" and m.status == "running" and m.thrusting != 0)
        for ev in m.events:
            self.snd.play({"boom": "boom", "dock": "beep_go", "chute": "sep", "tear": "alarm", "alarm": "alarm", "land": "win"}.get(ev, "click"))
        m.events.clear()
        if m.status != "running":
            self.mod_end_t += dt
        if self.phase == "rendezvous" and m.status == "won" and self.mod_end_t > 3.0:
            self.total += 500
            self.milestones.append("Acoplamiento con el satélite")
            self.start_phase("reentry")
            return
        if self.phase == "reentry" and m.status == "won" and "Reentrada y aterrizaje" not in self.milestones:
            self.milestones.append("Reentrada y aterrizaje")
            self.total += 800 + int(m.integrity * 2)
            if self.cfg["crewed"]:
                self.total = int(self.total * 1.5)

    def draw_mod(self, surf, mouse, dt):
        m = self.mod
        m.draw_scene(surf)
        m.draw_hud(surf)
        m.draw_panel(surf, mouse)
        if m.status == "running":
            self.btn_abort.draw(surf, mouse)
        elif self.phase == "rendezvous" and m.status == "won":
            text(surf, "¡ACOPLAMIENTO COMPLETADO!", (460, 90), 34, GOOD, True, "center")
            text(surf, "Separando la etapa para la reentrada...", (460, 128), 18, TEXT, False, "center")
        if self.mod_finished():
            self.draw_result_mod(surf, mouse)

    def draw_result_mod(self, surf, mouse):
        m = self.mod
        ov = pygame.Surface((W, SCENE_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        surf.blit(ov, (0, 0))
        win = m.status == "won"
        col = GOOD if win else BAD
        panel(surf, (W // 2 - 330, 100, 660, 420), (14, 17, 26), col)
        text(surf, "MISIÓN COMPLETA" if win else m.title, (W // 2, 120), 34, col, True, "midtop")
        words, line, y = m.end_reason.split(), "", 175
        for wd in words:
            if font(17).size(line + wd)[0] > 600:
                text(surf, line, (W // 2, y), 17, TEXT, False, "midtop")
                y += 24
                line = ""
            line += wd + " "
        text(surf, line, (W // 2, y), 17, TEXT, False, "midtop")
        y += 40
        for name in ["Órbita alta alcanzada", "Acoplamiento con el satélite", "Reentrada y aterrizaje"]:
            ok = name in self.milestones
            text(surf, ("✔ " if ok else "✘ ") + name, (W // 2 - 200, y), 16, GOOD if ok else DIM)
            y += 26
        text(surf, f"Puntuación total: {self.total:,}", (W // 2, y + 12), 20, TEXT, True, "midtop")
        self.btn_res_build.draw(surf, mouse)
        self.btn_res_retry.draw(surf, mouse)
        text(surf, "Esc: constructor · Enter: repetir", (W // 2, 500), 13, DIM, False, "midtop")

    def draw_prelaunch(self, surf, mouse):
        w = self.weather
        px, pw = 30, 540
        panel(surf, (px, 20, pw, 300), (14, 17, 26), ACCENT)
        text(surf, "PLATAFORMA DE LANZAMIENTO", (px + pw // 2, 32), 22, ACCENT, True, "midtop")
        hh = int(w.hour)
        mm = int((w.hour % 1) * 60)
        rows = [("Hora local", f"{hh:02d}:{mm:02d}" + ("  (noche)" if w.is_night else "")),
                ("Clima", w.name), ("Viento", f"{w.wind:.1f} m/s"), ("Temperatura", f"{w.temp:.0f} °C")]
        for k, (a, b) in enumerate(rows):
            text(surf, a, (px + 30, 70 + k * 24), 16, DIM)
            col = BAD if (a == "Clima" and w.cond == 3) else (WARN if a == "Clima" and w.cond == 2 else TEXT)
            text(surf, b, (px + pw - 30, 70 + k * 24), 16, col, True, "topright")
        text(surf, "Tormentas y lluvia aumentan los fallos. Puedes esperar a que mejore.", (px + pw // 2, 172), 13, DIM, False, "midtop")
        self.btn_start.rect.topleft = (px + 20, 200)
        self.btn_wait.rect.topleft = (px + 20 + 255, 200)
        self.btn_back.rect.topleft = (px + 20, 264)
        self.btn_start.rect.size = (250, 54)
        self.btn_wait.rect.size = (245, 54)
        self.btn_back.rect.size = (500, 44)
        self.btn_start.draw(surf, mouse)
        self.btn_wait.draw(surf, mouse)
        self.btn_back.draw(surf, mouse)
        help_lines = ["W/S acelerador · A/D cabeceo · ESPACIO separar etapa",
                      "G piloto automático · C refrigerar · V ventear presión",
                      "R reiniciar sistemas · E apagar motor · T acelerar tiempo",
                      "X ABORTAR (en vuelo destruye el cohete)"]
        panel(surf, (px, 332, pw, 112), (14, 17, 26))
        for k, l in enumerate(help_lines):
            text(surf, l, (px + pw // 2, 342 + k * 24), 13, TEXT, False, "midtop")

    def draw_alerts(self, surf):
        s = self.sim
        if s.status != "flying":
            return
        y = 12
        blink = (pygame.time.get_ticks() // 300) % 2 == 0
        if s.orbit_ready and not s.engine_cut:
            panel(surf, (20, y, 560, 60), (10, 40, 20), GOOD)
            text(surf, "¡ÓRBITA LOGRADA! Pulsa E: APAGAR MOTORES", (32, y + 6), 20, GOOD, True)
            text(surf, f"Si no, se apagarán solos en {max(0, s.orbit_ready_t):.0f} s. Después irás al satélite.", (32, y + 34), 14, TEXT)
            y += 70
        elif not s.faults.active and s.sep_timer is None and s.alt > 20000:
            apo, per = s.orbit()
            if s.engine_cut and s.cur >= s.n_stages - 1 and not s.orbit_ready:
                msg = None
            else:
                ap = "∞" if apo == float("inf") else f"{apo/1000:.0f}"
                pr = f"{per/1000:.0f}" if per > 0 else "—"
                msg = f"OBJETIVO: perigeo ≥120 km (ahora {pr}) y apogeo ≥500 km (ahora {ap}). Sigue acelerando con el cohete inclinado."
            if msg:
                text(surf, msg, (22, y + 2), 13, TEXT, True)
        for k, sev in s.faults.active.items():
            name, fix = FAULT_INFO[k]
            col = BAD if sev > 0.6 and blink else WARN
            panel(surf, (20, y, 560, 44), (40, 14, 14), col)
            text(surf, "⚠ " + name, (32, y + 4), 16, col, True)
            text(surf, fix, (32, y + 24), 12, TEXT)
            bar(surf, (420, y + 16, 150, 12), sev, col)
            y += 50
        if s.sep_timer is not None:
            col = BAD if blink else WARN
            panel(surf, (20, y, 560, 70), (50, 12, 12), col)
            text(surf, "¡SEPARA LA ETAPA! (ESPACIO)", (32, y + 6), 24, col, True)
            text(surf, f"Explotará en {max(0, s.sep_timer):.0f} s", (32, y + 38), 20, TEXT, True)
            bar(surf, (330, y + 44, 240, 12), s.sep_timer / s.SEP_MARGIN, col)
        elif s.fuel_frac() < 0.10 and s.cur < s.n_stages - 1 and s.prop[s.cur] > 0:
            text(surf, "Combustible casi agotado: prepárate para separar (ESPACIO)", (30, y + 4), 16, WARN, True)
        # consejos para el jugador
        tips = []
        if s.ignited and s.engine_cut and s.prop[s.cur] > 0 and not s.orbit_ready and s.alt < 120e3:
            tips.append("Motores APAGADOS: pulsa E para encenderlos.")
        if s.ignited and not s.engine_cut:
            if s.vr < -50 and s.alt < 100e3:
                tips.append("¡ESTÁS CAYENDO! Acelerador al 100 % y apunta más alto (cabeceo menor).")
            if s.throttle < 0.9 and not s.faults.active:
                tips.append("Acelerador bajo: súbelo al 100 % (arrastra el slider o ↑).")
            if "avionics" in s.faults.active:
                tips.append("Aviónica averiada: pulsa R y espera; hasta entonces el empuje es débil.")
            if not s.autopilot:
                tips.append("Piloto automático apagado: pulsa G para que el cohete se incline solo.")
        if tips:
            ty = y + (80 if s.sep_timer is not None else 6)
            for i, tip in enumerate(tips[:3]):
                text(surf, "▶ " + tip, (24, ty + i * 20), 15, WARN, True)

    def draw_result(self, surf, mouse):
        s = self.sim
        ov = pygame.Surface((W, SCENE_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        surf.blit(ov, (0, 0))
        win = s.status == "orbit"
        col = GOOD if win else (WARN if s.status == "aborted" else BAD)
        panel(surf, (W // 2 - 330, 100, 660, 420), (14, 17, 26), col)
        title = {"orbit": "MISIÓN CUMPLIDA" if s.result == "orbita_alta" else "ÓRBITA BAJA",
                 "exploded": "COHETE DESTRUIDO", "crashed": "MISIÓN FALLIDA", "aborted": "LANZAMIENTO ABORTADO"}[s.status]
        text(surf, title, (W // 2, 120), 34, col, True, "midtop")
        # texto largo con ajuste
        words, line, y = s.end_reason.split(), "", 175
        for wd in words:
            if font(17).size(line + wd)[0] > 600:
                text(surf, line, (W // 2, y), 17, TEXT, False, "midtop")
                y += 24
                line = ""
            line += wd + " "
        text(surf, line, (W // 2, y), 17, TEXT, False, "midtop")
        y += 40
        if s.cities_hit:
            names = ", ".join(CITIES[i][1] for i in s.cities_hit)
            text(surf, "¡Los restos han destruido: " + names + "!", (W // 2, y), 16, BAD, True, "midtop")
            y += 28
        if s.cfg["crewed"] and s.status in ("exploded", "crashed"):
            msg = "Tripulación a salvo gracias a la torre de escape." if s.crew_saved else "La tripulación ha perdido la vida."
            text(surf, msg, (W // 2, y), 16, GOOD if s.crew_saved else BAD, True, "midtop")
            y += 30
        apo, per = s.orbit()
        info = [("Altitud máxima", f"{s.max_alt / 1000:,.0f} km"), ("Tiempo de vuelo", f"{s.t:,.0f} s"),
                ("Integridad final", f"{s.integrity:.0f}%"), ("Puntuación", f"{s.score():,}")]
        for k, (a, b) in enumerate(info):
            text(surf, a, (W // 2 - 200, 300 + k * 26), 16, DIM)
            text(surf, b, (W // 2 + 200, 300 + k * 26), 16, TEXT, True, "topright")
        self.btn_res_build.draw(surf, mouse)
        self.btn_res_retry.draw(surf, mouse)
        text(surf, "Esc: constructor · Enter: repetir", (W // 2, 500), 13, DIM, False, "midtop")

    # --------------------------------------------------------------- telemetría
    def draw_telemetry(self, surf):
        s = self.sim
        panel(surf, (0, TEL_Y, W, H - TEL_Y), (10, 13, 20), None, 0)
        pygame.draw.line(surf, ACCENT, (0, TEL_Y), (W, TEL_Y), 2)
        x0 = 14
        y0 = TEL_Y + 10
        text(surf, "TELEMETRÍA", (x0, y0), 13, ACCENT, True)
        alt = max(s.alt, 0)
        rows1 = [("Altitud", f"{alt / 1000:,.1f} km", TEXT),
                 ("Velocidad", f"{s.speed:,.0f} m/s", TEXT),
                 ("Vel. vertical", f"{s.vr:,.0f} m/s", TEXT),
                 ("Vel. horizontal", f"{s.vt:,.0f} m/s", TEXT),
                 ("Mach", f"{s.mach:.1f}", TEXT),
                 ("Fuerza G", f"{s.gforce:.1f} g", level_color(s.gforce, 4, 7)),
                 ("Presión dinámica (q)", f"{s.q / 1000:.1f} kPa", level_color(s.q, 25000, 40000)),
                 ("Rozamiento (casco)", f"{s.temp_skin:.0f} °C", level_color(s.temp_skin, 450, 700))]
        for k, (a, b, c) in enumerate(rows1):
            text(surf, a, (x0, y0 + 22 + k * 19), 14, DIM)
            text(surf, b, (x0 + 300, y0 + 22 + k * 19), 14, c, True, "topright")
        x1 = 350
        gauges = [("Temp. motor", s.temp_eng, 1400, f"{s.temp_eng:.0f} °C", 850, 1000),
                  ("Presión tanques", s.pressure, 2.2, f"{s.pressure:.2f} bar", 1.4, 1.7),
                  ("Estrés estructural", s.stress, 1.5, f"{s.stress * 100:.0f}%", 0.7, 1.0)]
        for k, (a, v, mx, lab, w, b) in enumerate(gauges):
            yy = y0 + 22 + k * 30
            text(surf, a, (x1, yy), 14, DIM)
            text(surf, lab, (x1 + 300, yy), 14, level_color(v, w, b), True, "topright")
            bar(surf, (x1, yy + 17, 300, 6), v / mx, level_color(v, w, b))
        inv = [("Combustible etapa", s.fuel_frac(), f"{s.fuel_frac() * 100:.0f}%", ACCENT, True),
               ("Refrigerante", s.coolant / 100, f"{s.coolant:.0f}%", ACCENT, True),
               ("Integridad", s.integrity / 100, f"{s.integrity:.0f}%", GOOD, True)]
        for k, (a, v, lab, col, _) in enumerate(inv):
            yy = y0 + 112 + k * 22
            c = col if (a != "Integridad" or v > 0.5) else (WARN if v > 0.25 else BAD)
            text(surf, a, (x1, yy), 13, DIM)
            text(surf, lab, (x1 + 300, yy), 13, TEXT, True, "topright")
            bar(surf, (x1 + 130, yy + 4, 110, 8), v, c)
        x2 = 680
        apo, per = s.orbit()
        orb_ok = per >= TARGET_ORBIT_ALT and apo >= TARGET_APO
        apo_s = "∞" if apo == float("inf") else f"{apo / 1000:,.0f} km"
        per_s = f"{per / 1000:,.0f} km" if per > -EARTH_R / 2 else "—"
        thrust = s.thrust_now()[0]
        rows3 = [("Etapa", f"{s.cur + 1} / {s.n_stages}", TEXT),
                 ("Masa", f"{s.mass() / 1000:,.0f} t", TEXT),
                 ("Empuje", f"{thrust / 1e6:.1f} MN", TEXT),
                 ("Acelerador", f"{s.throttle * 100:.0f}%" + (" (motor OFF)" if s.engine_cut else ""), TEXT),
                 ("Apogeo", apo_s, TEXT),
                 ("Perigeo (obj. ≥120 km, apogeo ≥500 km)", per_s, GOOD if orb_ok else TEXT)]
        text(surf, "VUELO", (x2, y0), 13, ACCENT, True)
        for k, (a, b, c) in enumerate(rows3):
            text(surf, a, (x2, y0 + 22 + k * 19), 14, DIM)
            text(surf, b, (x2 + 270, y0 + 22 + k * 19), 14, c, True, "topright")
        # cabeceo
        yy = y0 + 22 + 6 * 19 + 4
        text(surf, f"Cabeceo {s.pitch:.0f}°  (guía {s.guide_pitch():.0f}°)  ·  Piloto auto: " + ("SÍ" if s.autopilot else "NO"), (x2, yy), 13, TEXT)
        bar(surf, (x2, yy + 20, 270, 6), 0, ACCENT)
        pygame.draw.rect(surf, GOOD, (x2 + 270 * min(1, max(0, s.guide_pitch() / 100)) - 2, yy + 16, 4, 14))
        pygame.draw.rect(surf, TEXT, (x2 + 270 * min(1, max(0, s.pitch / 100)) - 2, yy + 16, 4, 14))
        # log + clima
        x3 = 990
        w = self.weather
        text(surf, f"Clima: {w.name} · viento {w.wind:.0f} m/s · {int(w.hour):02d}:{int((w.hour % 1) * 60):02d}", (x3, y0), 13, WARN if w.cond >= 2 else DIM)
        text(surf, f"Tiempo ×{WARPS[self.warp_i]} (T) · T+{s.t:,.0f}s", (x3, y0 + 18), 13, DIM)
        colors = {"info": DIM, "good": GOOD, "warn": WARN, "bad": BAD}
        lines = []
        for t, msg, lvl in s.log[-8:]:
            cur = ""
            for wd in msg.split():
                if font(12).size(cur + wd)[0] > 275:
                    lines.append((cur, lvl))
                    cur = "  "
                cur += wd + " "
            lines.append((cur, lvl))
        for k, (ln, lvl) in enumerate(lines[-9:]):
            text(surf, ln, (x3, y0 + 40 + k * 15), 12, colors[lvl])
