"""Clima y hora del día."""
import math
import random

CLIMAS = {
    "Despejado": dict(viento=(0, 8),   lluvia=0.0, rayos=0.0,    nubes=0.1, frio=0.0, elec=1.0),
    "Nublado":   dict(viento=(3, 14),  lluvia=0.0, rayos=0.0,    nubes=0.6, frio=0.1, elec=1.1),
    "Ventoso":   dict(viento=(15, 30), lluvia=0.0, rayos=0.0,    nubes=0.3, frio=0.1, elec=1.0),
    "Lluvia":    dict(viento=(5, 18),  lluvia=0.6, rayos=0.002,  nubes=0.85, frio=0.2, elec=1.8),
    "Tormenta":  dict(viento=(12, 34), lluvia=1.0, rayos=0.015,  nubes=1.0, frio=0.3, elec=2.6),
}

HORAS = ["Amanecer", "Mañana", "Mediodía", "Tarde", "Atardecer", "Noche"]

# (cielo arriba, cielo horizonte) por hora
CIELOS = {
    "Amanecer":  ((70, 90, 150),  (250, 170, 120)),
    "Mañana":    ((90, 150, 230), (180, 215, 245)),
    "Mediodía":  ((60, 130, 230), (160, 205, 245)),
    "Tarde":     ((80, 140, 225), (200, 215, 235)),
    "Atardecer": ((60, 60, 130),  (250, 120, 70)),
    "Noche":     ((8, 10, 30),    (25, 30, 60)),
}

FRIO_HORA = {"Amanecer": 0.35, "Noche": 0.4, "Atardecer": 0.1}


class Meteo:
    def __init__(self, rng=None, clima=None, hora=None):
        self.rng = rng or random.Random()
        self.tirar(clima, hora)

    def tirar(self, clima=None, hora=None):
        r = self.rng
        pesos = [0.30, 0.25, 0.15, 0.18, 0.12]
        self.clima = clima or r.choices(list(CLIMAS), weights=pesos)[0]
        self.hora = hora or r.choice(HORAS)
        c = CLIMAS[self.clima]
        self.viento_base = r.uniform(*c["viento"])
        self.dir_viento = r.choice([-1, 1])
        self.temp_suelo = r.uniform(4, 30) - 8 * (self.hora in FRIO_HORA)
        self.t_rafaga = 0.0
        self.rafaga = 0.0

    @property
    def datos(self):
        return CLIMAS[self.clima]

    @property
    def frio(self):
        """0..1: juntas rígidas por frío -> más fugas."""
        f = self.datos["frio"] + FRIO_HORA.get(self.hora, 0)
        if self.temp_suelo < 8:
            f += 0.25
        return min(1.0, f)

    def viento(self, alt, t):
        """Viento lateral (m/s) a una altitud. Corriente en chorro a ~11 km."""
        perfil = min(1.0, alt / 3000.0) * 0.7
        chorro = math.exp(-((alt - 11000) / 3500) ** 2) * 1.0
        f = (perfil + chorro) * (1.0 if alt < 25000 else max(0.0, 1 - (alt - 25000) / 20000))
        return self.dir_viento * (self.viento_base * f + self.rafaga * f)

    def paso(self, dt, t):
        self.t_rafaga -= dt
        if self.t_rafaga <= 0:
            self.t_rafaga = self.rng.uniform(1.5, 5)
            self.rafaga = self.rng.uniform(-1, 1) * self.viento_base * 0.5

    def resumen(self):
        return (f"{self.clima}  |  {self.hora}  |  viento {self.viento_base:4.1f} m/s  |  "
                f"{self.temp_suelo:3.0f} °C en suelo")
