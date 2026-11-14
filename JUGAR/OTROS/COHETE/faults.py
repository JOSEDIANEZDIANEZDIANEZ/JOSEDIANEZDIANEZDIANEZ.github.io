"""Fallos, temperaturas, presión y suerte."""
import math
from data import *

FAULT_INFO = {
    "pressure": ("Pico de presión en tanques", "Pulsa V (ventear)"),
    "vibration": ("Vibración / sobrecalentamiento del motor", "Pulsa C (refrigerar) o baja el acelerador <50%"),
    "avionics": ("Fallo de aviónica / guiado", "Pulsa R (reiniciar sistemas)"),
    "pogo": ("Oscilación POGO en el motor", "Mantén el acelerador entre 35% y 65%"),
}


class Faults:
    def __init__(self, sim):
        self.sim = sim
        self.active = {}          # kind -> severidad 0..1
        self.reset_timer = 0.0
        self.reset_cool = 0.0
        self.leak = 0.0
        self.warned = set()

    # --- consultas desde la simulación
    def thrust_factor(self):
        f = 0.0 if self.reset_timer > 0 else 1.0
        if self.sim.integrity < 40:
            f *= 0.9
        return f

    def pitch_noise(self):
        s = self.sim
        return s.rng.gauss(0, 0.25 if s.weather.cond < 3 else 0.6)

    def pitch_noise_space(self):
        sev = self.active.get("avionics", 0.0)
        return self.sim.rng.uniform(-1, 1) * sev * 9

    def fuel_leak(self, dt):
        if self.leak > 0:
            s = self.sim
            s.prop[s.cur] = max(0.0, s.prop[s.cur] - s.stats[s.cur]["prop"] * self.leak * dt)

    # --- eventos
    def add(self, kind, sev=0.0):
        if kind not in self.active and len(self.active) < 3:
            self.active[kind] = sev
            self.sim.say(f"ALERTA: {FAULT_INFO[kind][0]}. {FAULT_INFO[kind][1]}", "bad")

    def lightning(self):
        s = self.sim
        if s.status != "flying" or s.alt > 15000:
            return
        if s.rng.random() > 0.05:      # no todos los rayos caen sobre el cohete
            return
        s.weather.bolt_x = 0.5         # el rayo cae justo sobre el cohete
        s.weather.flash = 1.0
        if s.cfg["shield"]:
            s.say("¡Un rayo ha impactado, pero el pararrayos lo ha desviado!", "good")
            s.integrity -= 2
            return
        s.say("¡UN RAYO HA IMPACTADO EN EL COHETE!", "bad")
        if s.rng.random() < 0.9:
            s.explode("Un rayo ha impactado en el cohete (sin pararrayos) y lo ha hecho estallar.")
        else:
            s.integrity -= 20
            self.add("avionics", 0.5)

    # --- bucle
    def update(self, dt, ctl):
        s = self.sim
        w = s.weather
        if s.cur >= s.n_stages:
            return
        st = s.cfg["stages"][s.cur]
        eng = ENGINES[st["engine"]]
        fuel = FUELS[st["fuel"]]
        burning = s.thrust_now()[0] > 0
        thr = s.throttle if burning else 0.0
        self.reset_timer = max(0.0, self.reset_timer - dt)
        self.reset_cool = max(0.0, self.reset_cool - dt)

        # temperatura del motor
        teq = 20 + 520 * eng["heat"] * thr ** 1.3
        if "vibration" in self.active:
            teq += 380 * (0.5 + self.active["vibration"])
        s.temp_eng += (teq - s.temp_eng) * dt / 25
        if ctl.get("coolant") and s.coolant > 0:
            s.temp_eng = max(20.0, s.temp_eng - 45 * dt)
            s.coolant -= 14 * dt
            if "vibration" in self.active:
                self.active["vibration"] -= 0.2 * dt
        s.coolant = max(0.0, min(100.0, s.coolant + 0.4 * dt))
        if s.temp_eng > 1000:
            s.integrity -= (s.temp_eng - 1000) * 0.06 * dt
            if "temp" not in self.warned:
                s.say("¡Motor a temperatura crítica!", "bad")
                self.warned.add("temp")
        elif s.temp_eng < 900:
            self.warned.discard("temp")
        if s.temp_eng > 1350:
            s.explode("El motor se ha fundido por sobrecalentamiento.")
            return

        # presión de tanques
        dp = 0.0035 * fuel["press"] * thr - (s.pressure - 1.0) * 0.015
        if "pressure" in self.active:
            dp += 0.02 + 0.05 * self.active["pressure"]
        if ctl.get("vent"):
            dp -= 0.2
            s.prop[s.cur] = max(0.0, s.prop[s.cur] - s.stats[s.cur]["prop"] * 0.003 * dt * 30)
            if "pressure" in self.active:
                self.active["pressure"] -= 0.25 * dt
        s.pressure = max(0.3, s.pressure + dp * dt)
        if s.pressure > 1.6 and "pres" not in self.warned:
            s.say("Presión de tanques peligrosa.", "bad")
            self.warned.add("pres")
        elif s.pressure < 1.4:
            self.warned.discard("pres")
        if s.pressure > 2.1:
            s.explode("Rotura de un tanque por sobrepresión.")
            return

        # reinicio de sistemas
        if ctl.get("reset") and self.reset_cool <= 0:
            self.reset_cool = 8.0
            self.reset_timer = 2.0
            s.say("Reiniciando sistemas (motor apagado 2 s)...", "warn")
            if "avionics" in self.active:
                self.active["avionics"] = 0.0
        # pogo
        if "pogo" in self.active:
            if 0.35 <= s.throttle <= 0.65:
                self.active["pogo"] -= 0.2 * dt
            s.integrity -= 1.5 * self.active["pogo"] * dt
            s.stress += 0.3

        # gravedad de cada fallo
        for k in list(self.active):
            if k == "vibration" and s.throttle < 0.5:
                self.active[k] -= 0.12 * dt
            self.active[k] += (0.075 * dt) if self.active[k] < 1 else 0
            if self.active[k] <= 0:
                del self.active[k]
                s.say(f"Resuelto: {FAULT_INFO[k][0]}.", "good")
            elif self.active[k] >= 1.0:
                del self.active[k]
                self.catastrophe(k)
                if s.status == "exploded":
                    return

        # aparición de nuevos fallos
        if s.t > 3:
            rate = 0.004 + eng["risk"] * st["n_eng"] * 60 * thr
            rate += 0.003 if w.rain and s.alt < 15000 else 0
            rate += 0.006 if w.cond == 3 and s.alt < 15000 else 0
            rate += 0.01 * max(0.0, s.stress - 0.7)
            rate += 0.003 if w.temp < 2 and s.alt < 5000 else 0
            rate *= fuel["risk"]
            if s.rng.random() < rate * dt:
                kind = s.rng.choice(list(FAULT_INFO))
                if kind == "vibration" and not burning:
                    kind = "avionics"
                self.add(kind, 0.05)
            # suerte: explosión espontánea
            p = eng["risk"] * st["n_eng"] * thr * fuel["risk"] * (1.8 if w.cond == 3 and s.alt < 15000 else 1.0) + 2e-5
            if s.rng.random() < p * dt * 1.5:
                s.explode("Fallo catastrófico inesperado: el cohete ha explotado.")

    def catastrophe(self, kind):
        s = self.sim
        if s.rng.random() < 0.65:
            s.explode(f"No se resolvió a tiempo: {FAULT_INFO[kind][0].lower()}. El cohete ha explotado.")
        else:
            s.integrity -= 25
            s.say("¡Por los pelos! El fallo ha causado daños graves, pero el cohete sigue entero.", "warn")
            if s.rng.random() < 0.5 and self.leak == 0:
                self.leak = 0.002
                s.say("Se ha abierto una fuga de combustible.", "bad")
