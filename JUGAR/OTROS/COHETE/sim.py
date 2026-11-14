"""Simulación física del vuelo (coordenadas polares alrededor de la Tierra)."""
import math
import random
from data import *
from rocketmodel import stage_stats, rocket_summary, payload_mass, G0
from faults import Faults
from cities import hit_cities, CITIES

DIAMETERS = [2.6, 3.8, 5.2]
DT = 1 / 30


def atmos(alt):
    p = math.exp(-max(alt, 0) / 7200.0)       # razón de presión
    return 1.225 * math.exp(-max(alt, 0) / 7500.0), p


class Sim:
    def __init__(self, cfg, weather, seed=None):
        self.cfg = cfg
        self.weather = weather
        self.rng = random.Random(seed)
        self.n_stages = len(cfg["stages"])
        self.stats = [stage_stats(cfg, i) for i in range(self.n_stages)]
        self.summary = rocket_summary(cfg)
        self.prop = [s["prop"] for s in self.stats]
        self.cur = 0                         # etapa activa (la más baja que sigue unida)
        self.status = "pad"                  # pad, countdown, flying, orbit, exploded, aborted, crashed
        self.countdown = 6.0
        self.r = EARTH_R
        self.theta = 0.0
        self.vr = 0.0
        self.vt = 0.0
        self.pitch = 0.0
        self.pitch_cmd = 0.0
        self.throttle = 0.0
        self.engine_cut = True               # los motores empiezan apagados
        self.ignited = False
        self.cities_hit = []
        self.orbit_ready = False
        self.karman = False
        self.thr_saved = 1.0
        self.orbit_ready_t = 0.0
        self.had_fault = False
        self.restoring = False
        self.sep_timer = None          # cuenta atrás para separar una etapa vacía
        self.low_warned = set()
        self.autopilot = True
        self.t = 0.0                         # tiempo de vuelo
        self.temp_eng = 20.0
        self.temp_skin = 20.0
        self.pressure = 1.0
        self.coolant = 100.0
        self.integrity = 100.0
        self.stress = 0.0
        self.gforce = 1.0
        self.q = 0.0
        self.mach = 0.0
        self.accel = 0.0
        self.log = []
        self.events = []                     # eventos visuales: ("sep", etapa) ("explosion",)
        self.faults = Faults(self)
        self.end_reason = ""
        self.crew_saved = None
        self.orbit_hold = 0.0
        self.max_alt = 0.0
        self.result = None                   # "orbita_alta", "orbita_baja", None
        self.say("Cohete en plataforma. Revisa el clima y arranca la cuenta atrás.", "info")

    # ------------------------------------------------------------ utilidades
    def say(self, msg, level="info"):
        self.log.append((self.t, msg, level))
        self.log = self.log[-60:]

    @property
    def alt(self):
        return self.r - EARTH_R

    @property
    def speed(self):
        return math.hypot(self.vr, self.vt)

    def mass(self):
        m = payload_mass(self.cfg)
        for i in range(self.cur, self.n_stages):
            m += self.stats[i]["dry"] + self.prop[i]
        return m

    def fuel_frac(self):
        if self.cur >= self.n_stages:
            return 0
        return self.prop[self.cur] / max(self.stats[self.cur]["prop"], 1)

    def total_fuel_frac(self):
        tot = sum(s["prop"] for s in self.stats)
        return sum(self.prop) / tot

    def orbit(self):
        """Devuelve (apogeo, perigeo) en metros sobre la superficie."""
        v2 = self.vr ** 2 + self.vt ** 2
        eps = v2 / 2 - EARTH_MU / self.r
        h = self.r * self.vt
        if eps >= 0:
            return float("inf"), -EARTH_R
        a = -EARTH_MU / (2 * eps)
        e = math.sqrt(max(0.0, 1 + 2 * eps * h * h / EARTH_MU ** 2))
        return a * (1 + e) - EARTH_R, a * (1 - e) - EARTH_R

    def thrust_now(self):
        if self.cur >= self.n_stages or self.engine_cut or self.prop[self.cur] <= 0:
            return 0.0, 0.0
        s = self.stats[self.cur]
        _, p = atmos(self.alt)
        isp = s["isp_vac"] - (s["isp_vac"] - s["isp_sl"]) * p
        mdot = s["thrust"] / (s["isp_sl"] * G0) * self.throttle * self.faults.thrust_factor()
        # el combustible dura más: mismo empuje con menos consumo
        return mdot * isp * G0, mdot / FUEL_ECON

    # ------------------------------------------------------------ acciones
    def start_countdown(self):
        if self.status == "pad":
            self.status = "countdown"
            self.say("Cuenta atrás iniciada.", "info")

    def separate(self):
        if self.status != "flying" or self.cur >= self.n_stages - 1:
            return
        if self.rng.random() < 0.04:
            self.say("¡Separación atascada! Vuelve a intentarlo.", "bad")
            return
        self.events.append(("sep", self.cur))
        self.cur += 1
        self.temp_eng = max(20.0, self.temp_eng * 0.5)
        self.pressure = 1.0
        self.sep_timer = None
        self.engine_cut = True
        self.say(f"Etapa separada. ¡ENCIENDE los motores de la etapa {self.cur + 1} (E)!", "warn")

    def toggle_engine(self):
        if self.status != "flying":
            return
        if self.cur >= self.n_stages or self.prop[self.cur] <= 0:
            self.say("No queda combustible en esta etapa.", "warn")
            return
        self.engine_cut = not self.engine_cut
        if self.engine_cut:
            self.say("Motores APAGADOS.", "warn")
        else:
            self.ignited = True
            if self.throttle < 0.05:
                self.throttle = 1.0
            self.events.append(("ignite",))
            self.say("Motores ENCENDIDOS.", "good")

    def abort(self):
        if self.status in ("pad", "countdown") or (self.status == "flying" and not self.ignited):
            self.status = "aborted"
            self.end_reason = "Lanzamiento abortado en plataforma. Nadie ha resultado herido."
            return
        if self.status == "flying":
            self.explode("¡ABORTO! El sistema de autodestrucción ha destruido el cohete.", accidental=False)

    def explode(self, why, accidental=True):
        if self.status in ("exploded", "crashed", "orbit"):
            return
        self.status = "exploded"
        self.end_reason = why
        self.events.append(("explosion",))
        self.throttle = 0
        if accidental:
            self.cities_hit = hit_cities(self.theta * EARTH_R, self.alt)
            if self.cities_hit:
                names = ", ".join(CITIES[i][1] for i in self.cities_hit)
                self.say(f"¡Los restos caen sobre la ciudad! Arrasadas: {names}.", "bad")
        if self.cfg["crewed"]:
            if self.cfg["tower"] and self.rng.random() < 0.85:
                self.crew_saved = True
                self.say("La torre de escape ha sacado la cápsula. Tripulación a salvo.", "good")
            else:
                self.crew_saved = False
                self.say("Se ha perdido la tripulación.", "bad")
        self.say(why, "bad")

    # ------------------------------------------------------------ bucle
    def update(self, ctl):
        """ctl: dict con thr (-1..1), pitch (-1..1), coolant, vent, reset."""
        dt = DT
        if self.status != "exploded" and self.weather.update(dt):
            self.faults.lightning()
        if self.status == "countdown":
            self.countdown -= dt
            if self.countdown <= 0:
                self.status = "flying"
                self.throttle = 0.0
                self.say("T-0. Motores apagados: pulsa E (o ENCENDER MOTORES) para la ignición.", "warn")
            return
        if self.status != "flying":
            return
        if self.ignited:
            self.t += dt
        self.control(ctl, dt)
        self.physics(dt)
        if self.ignited:
            self.faults.update(dt, ctl)
        self.check_end(dt)

    def control(self, ctl, dt):
        self.throttle = max(0.0, min(1.0, self.throttle + ctl.get("thr", 0) * 0.6 * dt))
        # recuperación automática del acelerador tras resolver un fallo
        if self.faults.active:
            self.had_fault = True
        elif self.ignited and not self.engine_cut:
            if getattr(self, "had_fault", False):
                self.had_fault = False
                if self.throttle < self.thr_saved - 0.05:
                    self.restoring = True
                    self.say("Fallo resuelto: recupero el acelerador automáticamente.", "good")
            if ctl.get("thr", 0):
                self.restoring = False
            if getattr(self, "restoring", False):
                self.throttle = min(self.thr_saved, self.throttle + 0.4 * dt)
                if self.throttle >= self.thr_saved:
                    self.restoring = False
            else:
                self.thr_saved = max(self.throttle, 0.3) if not self.faults.active else self.thr_saved
        if ctl.get("pitch", 0):
            if self.autopilot:
                self.autopilot = False
                self.pitch_cmd = self.pitch
                self.say("Piloto automático desactivado (control manual).", "warn")
            self.pitch_cmd += ctl["pitch"] * 12 * dt
        if self.autopilot:
            self.pitch_cmd = self.auto_pitch()
        self.pitch_cmd = max(-20.0, min(110.0, self.pitch_cmd))
        mass_f = 1.0 + self.mass() / 1.2e6
        rate = 9.0 / mass_f
        d = self.pitch_cmd - self.pitch
        self.pitch += max(-rate * dt, min(rate * dt, d))
        _, p = atmos(self.alt)
        stab = 0.45 if self.cfg["fins"] else 1.0
        disturb = (self.weather.gust(self.alt) * 0.03 + self.faults.pitch_noise()) * stab * min(1.0, p * 2)
        self.pitch += (disturb + self.faults.pitch_noise_space()) * dt
        # ruido de espacio ya incluido; limitamos
        self.pitch = max(-30.0, min(120.0, self.pitch))

    PROGRAM = [(1.2e3, 0), (4e3, 0), (10e3, 8), (20e3, 24), (35e3, 44), (50e3, 44),
               (70e3, 69), (100e3, 80), (150e3, 92), (250e3, 100)]

    def guide_pitch(self):
        """Cabeceo recomendado: giro gravitatorio abajo; en vacío, el que más sube el perigeo."""
        a = self.alt
        if a >= 70e3 and self.r > 0:
            best = None
            for ang in range(0, 111, 6):
                vr2 = self.vr + 20.0 * math.cos(math.radians(ang))
                vt2 = self.vt + 20.0 * math.sin(math.radians(ang))
                eps = (vr2 ** 2 + vt2 ** 2) / 2 - EARTH_MU / self.r
                if eps >= 0:
                    p = 1e9
                else:
                    h = self.r * vt2
                    sa = -EARTH_MU / (2 * eps)
                    e = math.sqrt(max(0.0, 1 + 2 * eps * h * h / EARTH_MU ** 2))
                    p = sa * (1 - e) - EARTH_R
                if best is None or p > best[0]:
                    best = (p, ang)
            ang = float(best[1])
            if a < 120e3 and self.vr < (120e3 - a) * 0.02:
                ang = min(ang, 70.0)      # evita hundirse en la atmósfera
            return ang
        prog = self.PROGRAM
        if a <= prog[0][0]:
            return 0.0
        for (a0, p0), (a1, p1) in zip(prog, prog[1:]):
            if a <= a1:
                return p0 + (p1 - p0) * (a - a0) / (a1 - a0)
        return float(prog[-1][1])

    def auto_pitch(self):
        return self.guide_pitch()

    def physics(self, dt):
        thrust, mdot = self.thrust_now()
        if mdot > 0:
            self.prop[self.cur] = max(0.0, self.prop[self.cur] - mdot * dt)
            self.faults.fuel_leak(dt)
            if self.prop[self.cur] <= 0:
                self.say("Etapa sin combustible." + (" ¡Separa la etapa!" if self.cur < self.n_stages - 1 else ""), "warn")
        m = self.mass()
        rho, p = atmos(self.alt)
        v = self.speed
        cd = 0.35 + (0.08 if self.cfg["fins"] else 0) + (0.03 if self.weather.rain and self.alt < 12000 else 0)
        area = math.pi * (DIAMETERS[self.cfg["size"]] / 2) ** 2
        drag = 0.5 * rho * v * v * cd * area
        self.q = 0.5 * rho * v * v
        sound = 340 if self.alt < 11000 else 295
        self.mach = v / sound
        ph = math.radians(self.pitch)
        fr = thrust * math.cos(ph)
        ft = thrust * math.sin(ph)
        dr = drag * self.vr / v if v > 0.1 else 0
        dtn = drag * self.vt / v if v > 0.1 else 0
        ar = self.vt ** 2 / self.r - EARTH_MU / self.r ** 2 + (fr - dr) / m
        at = -self.vr * self.vt / self.r + (ft - dtn) / m
        self.accel = math.hypot((fr - dr) / m, (ft - dtn) / m)
        self.gforce = self.accel / G0
        on_pad = self.r <= EARTH_R + 0.5 and self.vr <= 0.01
        if on_pad and ar < 0:
            ar = 0
            self.vr = 0
            at = 0
            self.vt = 0
            self.gforce = 1.0
        self.vr += ar * dt
        self.vt += at * dt
        self.r += self.vr * dt
        self.theta += self.vt / self.r * dt
        if self.r < EARTH_R:
            if self.speed > 25 and self.t > 5:
                self.status = "crashed"
                self.end_reason = "El cohete ha caído a tierra."
                self.events.append(("explosion",))
                self.say(self.end_reason, "bad")
            self.r = EARTH_R
            self.vr = max(0, self.vr)
        self.max_alt = max(self.max_alt, self.alt)
        # temperaturas
        aero = 7.4e-8 * math.sqrt(rho) * v ** 3
        teq_skin = 20 + aero
        self.temp_skin += (teq_skin - self.temp_skin) * dt / 18
        # estrés estructural
        aoa = abs(math.radians(self.pitch) - math.atan2(self.vt, max(self.vr, 0.1))) if v > 50 else 0
        aoa = min(aoa, 1.2)
        tanks = sum(st["tanks"] for st in self.cfg["stages"][self.cur:])
        limit = 42000 * SIZES[self.cfg["size"]]["strength"] / (1 + 0.035 * tanks)
        self.stress = self.q * (1 + 5 * math.sin(aoa)) / limit
        if self.status == "flying" and self.t > 2:
            ratio = self.integrity / 100
            if self.stress > 1.0:
                self.integrity -= (self.stress - 1.0) * 40 * dt
            if self.temp_skin > 750:
                self.integrity -= (self.temp_skin - 750) * 0.02 * dt

    AUTO_CUT = 10.0     # s para apagar motores al lograr la órbita (si no, se apagan solos)
    SEP_MARGIN = 15.0   # segundos para separar una etapa vacía

    def check_separation(self, dt):
        if self.cur >= self.n_stages - 1:
            return
        frac = self.fuel_frac()
        if frac < 0.10 and self.cur not in self.low_warned and self.prop[self.cur] > 0:
            self.low_warned.add(self.cur)
            self.say("Combustible de la etapa casi agotado: prepárate para SEPARAR (ESPACIO).", "warn")
        if self.prop[self.cur] <= 0:
            if self.sep_timer is None:
                self.sep_timer = self.SEP_MARGIN
                self.say(f"¡ETAPA VACÍA! Sepárala con ESPACIO en {self.SEP_MARGIN:.0f} s o el cohete explotará.", "bad")
            self.sep_timer -= dt
            if self.sep_timer <= 0:
                self.explode("No separaste la etapa vacía a tiempo: el peso muerto ha destrozado el cohete.")

    def check_end(self, dt):
        self.check_separation(dt)
        if self.status != "flying":
            return
        if self.integrity <= 0:
            self.integrity = 0
            self.explode("La estructura ha cedido: el cohete se ha desintegrado.")
            return
        out_of_fuel = self.cur >= self.n_stages - 1 and self.prop[self.cur] <= 0
        no_power = out_of_fuel or self.engine_cut
        apo, per = self.orbit()
        if self.alt > 100e3 and not self.karman:
            self.karman = True
            self.say("Has cruzado la línea de Kármán: capa atmosférica atravesada.", "good")
        if self.alt > 20000 and self.t > 5:
            thrust0 = self.thrust_now()[0] <= 0
            if per >= TARGET_ORBIT_ALT and apo >= TARGET_APO:
                if thrust0:
                    self.finish("orbita_alta")
                    return
                if not self.orbit_ready:
                    self.orbit_ready = True
                    self.orbit_ready_t = self.AUTO_CUT
                    self.say("¡ÓRBITA ALCANZADA! Apaga los motores (E).", "good")
                self.orbit_ready_t -= dt
                if self.orbit_ready_t <= 0 and not self.engine_cut:
                    self.toggle_engine()
                    self.say("Motores apagados automáticamente: órbita lograda.", "good")
            elif per >= LOW_ORBIT_PER and (no_power or self.throttle == 0):
                self.orbit_ready = False
                self.orbit_hold += dt
                if self.orbit_hold > 25.0:
                    self.finish("orbita_baja")
                    return
            else:
                self.orbit_ready = False
                self.orbit_hold = 0
        if no_power and self.alt > 120e3 and apo == float("inf"):
            self.end_reason = "Trayectoria de escape: el cohete se pierde en el espacio."
            self.status = "crashed"
            self.say(self.end_reason, "bad")
        elif out_of_fuel and self.alt > 100e3 and per < LOW_ORBIT_PER:
            self.fail_hold = getattr(self, "fail_hold", 0.0) + dt
            if self.fail_hold > 20.0:
                self.end_reason = "Sin combustible y sin órbita estable: la reentrada es inevitable. Misión fallida."
                self.status = "crashed"
                self.say(self.end_reason, "bad")

    def finish(self, res):
        self.result = res
        self.status = "orbit"
        if res == "orbita_alta":
            self.end_reason = "¡ÓRBITA ALTA ALCANZADA! Misión cumplida."
        else:
            self.end_reason = "Órbita baja alcanzada, pero no llegaste a la órbita alta."
        self.say(self.end_reason, "good")

    def score(self):
        if self.result == "orbita_alta":
            s = 1000
        elif self.result == "orbita_baja":
            s = 450
        else:
            return int(self.max_alt / 1000)
        s += int(self.integrity * 3) + int(self.total_fuel_frac() * 200)
        s += max(0, int((80 - self.summary["cost"]) * 4))
        if self.cfg["crewed"]:
            s = int(s * 1.5)
        return s
