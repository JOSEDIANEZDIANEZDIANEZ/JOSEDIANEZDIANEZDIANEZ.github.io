"""Clima y hora del día."""
import math
import random

CONDITIONS = ["Despejado", "Nublado", "Lluvia", "Tormenta eléctrica"]


class Weather:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.hour = self.rng.uniform(0, 24)
        self.cond = self.rng.choices([0, 1, 2, 3], weights=[35, 25, 22, 18])[0]
        self.wind = self.rng.uniform(0, 12) + self.cond * 3  # m/s
        self.wind_dir = self.rng.choice([-1, 1])
        self.temp = 8 + 14 * math.sin((self.hour - 9) / 24 * 2 * math.pi) + self.rng.uniform(-3, 3)
        self.flash = 0.0        # destello visual de un rayo
        self.bolt_x = 0.5
        self.clock = 0.0

    @property
    def name(self):
        return CONDITIONS[self.cond]

    @property
    def rain(self):
        return self.cond >= 2

    @property
    def is_night(self):
        return self.hour < 6 or self.hour > 20

    def daylight(self):
        """0 = noche cerrada, 1 = pleno día."""
        h = self.hour
        return max(0.0, min(1.0, (math.sin((h - 6) / 12 * math.pi) + 0.25) / 1.0)) if 5 < h < 21 else 0.0

    def update(self, dt):
        """Evoluciona el tiempo despacio. Devuelve True si cae un rayo en la zona."""
        self.clock += dt
        self.hour = (self.hour + dt / 120.0) % 24     # 1 h de juego = 2 min reales
        self.flash = max(0.0, self.flash - dt * 2.5)
        self.wind = max(0.0, self.wind + self.rng.uniform(-0.6, 0.6) * dt)
        if self.rng.random() < dt / 60.0:             # cambio de clima ocasional
            self.cond = max(0, min(3, self.cond + self.rng.choice([-1, 0, 1])))
        bolt = False
        if self.cond == 3 and self.rng.random() < dt / 3.5:
            self.flash = 1.0
            self.bolt_x = self.rng.random()
            bolt = True
        return bolt

    def gust(self, alt):
        """Fuerza lateral de racha (m/s) a una altitud dada."""
        if alt > 25000:
            return 0.0
        k = 1.0 + 1.2 * math.sin(alt / 4000.0)
        return self.wind_dir * self.wind * k * (1.0 if alt < 14000 else (25000 - alt) / 11000)

    def sky_color(self, alt):
        """Color del cielo según hora y altitud (negro en el espacio)."""
        d = self.daylight()
        dawn = max(0.0, 1 - abs(self.hour - 6.5) / 1.3, 1 - abs(self.hour - 19.5) / 1.3)
        day = (90, 150, 235)
        night = (6, 8, 22)
        col = [night[i] + (day[i] - night[i]) * d for i in range(3)]
        col[0] += 140 * dawn
        col[1] += 60 * dawn
        grey = 0.0 if self.cond == 0 else (0.35 if self.cond == 1 else 0.6)
        base = sum(col) / 3 * 0.8
        col = [c * (1 - grey) + base * grey for c in col]
        space = max(0.0, min(1.0, (alt - 15000) / 90000))
        col = [c * (1 - space) + 2 * space for c in col]
        return tuple(int(max(0, min(255, c))) for c in col)

    def star_alpha(self, alt):
        space = max(0.0, min(1.0, (alt - 15000) / 90000))
        night = 1 - self.daylight()
        cloud = 0.0 if self.cond < 2 else 0.5
        return max(space, night * (1 - cloud))
