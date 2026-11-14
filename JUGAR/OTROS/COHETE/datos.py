"""Catálogo de piezas y diseño del cohete."""
from dataclasses import dataclass, field

# ---------------------------------------------------------------- motores
# empuje en kN (nivel del mar / vacío), masa en kg, fiabilidad base (0-1),
# calor = cuánto se calienta, coste en millones
MOTORES = {
    "Pájaro-1":   dict(emp_sl=420,  emp_vac=470,  masa=320,  fiab=0.9990, calor=0.8, coste=4,  desc="Económico y robusto"),
    "Halcón-9":   dict(emp_sl=850,  emp_vac=940,  masa=480,  fiab=0.9985, calor=1.0, coste=9,  desc="El caballo de batalla"),
    "Titán-X":    dict(emp_sl=1900, emp_vac=2100, masa=1250, fiab=0.9970, calor=1.5, coste=22, desc="Muy potente, caliente"),
    "Fénix-V":    dict(emp_sl=300,  emp_vac=520,  masa=240,  fiab=0.9980, calor=0.7, coste=7,  desc="Optimizado para el vacío"),
    "Cíclope-S":  dict(emp_sl=3200, emp_vac=3400, masa=2100, fiab=0.9950, calor=2.0, coste=35, desc="Brutal. Y temperamental"),
}

# --------------------------------------------------------------- combustible
# isp en segundos (multiplicador sobre el motor), densidad kg/m3,
# riesgo = probabilidad extra de fallo, calor = calentamiento extra
COMBUSTIBLES = {
    "Queroseno/LOX":  dict(isp=282, dens=1030, riesgo=1.0, calor=1.0, desc="Clásico y fiable"),
    "Hidrógeno/LOX":  dict(isp=380, dens=290,  riesgo=1.4, calor=0.9, desc="Eficiente, tanques enormes"),
    "Metano/LOX":     dict(isp=330, dens=830,  riesgo=1.15, calor=1.0, desc="Buen equilibrio"),
    "Hipergólico":    dict(isp=300, dens=1200, riesgo=1.6, calor=1.2, desc="Se enciende solo. Tóxico"),
    "Sólido":         dict(isp=250, dens=1700, riesgo=1.3, calor=1.5, desc="Sin válvulas, sin freno"),
}

# ---------------------------------------------------------------- tanques
TANQUE_MASA_COMB = 9000      # kg de combustible por tanque (se ajusta por densidad)
TANQUE_MASA_VACIO = 650      # kg de estructura por tanque

# ------------------------------------------------------------ tamaños/otros
TAMANOS = {
    "Pequeño": dict(diam=1.0, arrastre=0.85, estruct=0.9, ancho=26),
    "Medio":   dict(diam=1.5, arrastre=1.0,  estruct=1.0, ancho=34),
    "Grande":  dict(diam=2.2, arrastre=1.3,  estruct=1.25, ancho=44),
}

CARGAS = {
    "Satélite":  dict(masa=2500, tripulado=False),
    "Sonda":     dict(masa=1500, tripulado=False),
    "Cápsula":   dict(masa=4500, tripulado=True),
}

NOSES = ["Cónica", "Ojival", "Redonda"]

PALETA = [
    (235, 235, 240), (220, 60, 60), (60, 120, 220), (240, 190, 50),
    (70, 190, 110), (240, 130, 40), (150, 90, 200), (40, 40, 50),
]

G0 = 9.80665
MAX_ETAPAS = 4


@dataclass
class Etapa:
    motor: str = "Halcón-9"
    n_motores: int = 1
    combustible: str = "Queroseno/LOX"
    tanques: int = 2

    def masa_comb(self) -> float:
        c = COMBUSTIBLES[self.combustible]
        return self.tanques * TANQUE_MASA_COMB * (c["dens"] / 1030) ** 0.5

    def masa_seca(self, estruct: float) -> float:
        m = MOTORES[self.motor]
        return (self.tanques * TANQUE_MASA_VACIO * estruct) + self.n_motores * m["masa"]

    def isp(self, vacio: float) -> float:
        """vacio = 0 (nivel del mar) .. 1 (vacío)."""
        m = MOTORES[self.motor]
        c = COMBUSTIBLES[self.combustible]
        mult = (m["emp_sl"] + (m["emp_vac"] - m["emp_sl"]) * vacio) / m["emp_vac"]
        return c["isp"] * (0.8 + 0.2 * mult) * (0.88 + 0.12 * mult)

    def empuje(self, vacio: float) -> float:
        """kN totales."""
        m = MOTORES[self.motor]
        return self.n_motores * (m["emp_sl"] + (m["emp_vac"] - m["emp_sl"]) * vacio)


@dataclass
class Cohete:
    nombre: str = "ESPERANZA"
    etapas: list = field(default_factory=lambda: [
        Etapa("Halcón-9", 3, "Queroseno/LOX", 4),
        Etapa("Fénix-V", 1, "Queroseno/LOX", 2),
    ])
    tamano: str = "Medio"
    carga: str = "Satélite"
    color_cuerpo: tuple = (235, 235, 240)
    color_acento: tuple = (220, 60, 60)
    color_ojiva: tuple = (60, 120, 220)
    ojiva: str = "Ojival"
    torre_escape: bool = False

    @property
    def tripulado(self) -> bool:
        return CARGAS[self.carga]["tripulado"]

    def masa_carga(self) -> float:
        m = CARGAS[self.carga]["masa"]
        if self.torre_escape:
            m += 900
        return m

    def masa_etapa_total(self, i: int) -> float:
        e = self.etapas[i]
        est = TAMANOS[self.tamano]["estruct"]
        return e.masa_comb() + e.masa_seca(est)

    def masa_total(self) -> float:
        return sum(self.masa_etapa_total(i) for i in range(len(self.etapas))) + self.masa_carga()

    def coste(self) -> float:
        c = 0.0
        for e in self.etapas:
            c += MOTORES[e.motor]["coste"] * e.n_motores + e.tanques * 1.5
        c += {"Satélite": 12, "Sonda": 8, "Cápsula": 40}[self.carga]
        if self.torre_escape:
            c += 6
        return round(c, 1)

    def delta_v(self) -> float:
        """Delta-v total aproximado en m/s (ideal, en el vacío)."""
        import math
        est = TAMANOS[self.tamano]["estruct"]
        total = 0.0
        masa_sobre = self.masa_carga()
        for i in range(len(self.etapas) - 1, -1, -1):
            e = self.etapas[i]
            m0 = masa_sobre + e.masa_comb() + e.masa_seca(est)
            m1 = m0 - e.masa_comb()
            total += e.isp(1.0) * G0 * math.log(m0 / m1)
            masa_sobre = m0
        return total

    def twr_inicial(self) -> float:
        e = self.etapas[0]
        return e.empuje(0.0) * 1000 / (self.masa_total() * G0)
