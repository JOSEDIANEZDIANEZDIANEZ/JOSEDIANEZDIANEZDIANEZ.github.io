"""Datos de piezas del juego: motores, combustibles, tamaños, colores."""

# Motores: empuje (N) a nivel del mar, masa (kg), Isp mar / vacío (s),
# riesgo base de fallo por segundo, calor generado, coste (M€)
ENGINES = [
    {"name": "Colibrí S1",   "thrust": 600e3,  "mass": 700,  "isp_sl": 280, "isp_vac": 305, "risk": 0.00004, "heat": 0.7, "cost": 4},
    {"name": "Halcón M7",    "thrust": 1200e3, "mass": 1500, "isp_sl": 290, "isp_vac": 325, "risk": 0.00007, "heat": 1.0, "cost": 9},
    {"name": "Titán H9",     "thrust": 2600e3, "mass": 3300, "isp_sl": 300, "isp_vac": 340, "risk": 0.00012, "heat": 1.4, "cost": 22},
    {"name": "Vacío V-Ion",  "thrust": 250e3,  "mass": 350,  "isp_sl": 190, "isp_vac": 385, "risk": 0.00005, "heat": 0.5, "cost": 7},
    {"name": "Experimental X","thrust": 4200e3, "mass": 4600, "isp_sl": 320, "isp_vac": 365, "risk": 0.00030, "heat": 2.0, "cost": 40},
]

# Combustibles: densidad media del propelente (kg/m3), multiplicador de Isp,
# multiplicador de riesgo, presión (presión que sube sola), coste por m3
FUELS = [
    {"name": "Queroseno/LOX", "dens": 1030, "isp": 1.00, "risk": 1.0, "press": 1.0, "cost": 1.0},
    {"name": "Metano/LOX",    "dens": 830,  "isp": 1.08, "risk": 1.1, "press": 1.2, "cost": 1.3},
    {"name": "Hidrógeno/LOX", "dens": 290,  "isp": 1.28, "risk": 1.4, "press": 1.6, "cost": 2.0},
    {"name": "Hipergólico",   "dens": 1200, "isp": 0.93, "risk": 0.7, "press": 0.8, "cost": 1.6},
]

# Tamaños: (nombre, volumen por tanque en m3, ancho visual en px, resistencia estructural)
SIZES = [
    {"name": "Pequeño", "vol": 20,  "width": 34, "strength": 1.0},
    {"name": "Mediano", "vol": 60,  "width": 50, "strength": 1.5},
    {"name": "Grande",  "vol": 150, "width": 70, "strength": 2.2},
]

NOSES = ["Cónica", "Ojival", "Redondeada", "Plana"]

PALETTE = [
    ("Blanco",   (240, 240, 245)),
    ("Rojo",     (205, 50, 50)),
    ("Azul",     (50, 100, 205)),
    ("Naranja",  (240, 140, 40)),
    ("Verde",    (60, 170, 90)),
    ("Negro",    (40, 40, 48)),
    ("Plata",    (170, 175, 185)),
    ("Amarillo", (235, 210, 60)),
    ("Morado",   (130, 70, 180)),
]

TANK_DRY_PER_M3 = 58      # kg de estructura por m3 de tanque
PAYLOAD_SAT = 1800        # kg
PAYLOAD_CREW = 5200       # kg cápsula tripulada
ESCAPE_TOWER_MASS = 900   # kg
FINS_MASS = 400           # kg por etapa con aletas (solo la 1ª)
SHIELD_MASS = 150         # kg pararrayos/blindaje

MAX_STAGES = 3
MAX_TANKS = 8
MAX_ENGINES = 6

EARTH_R = 6371e3
EARTH_MU = 3.986e14
FUEL_ECON = 1.25  # el combustible dura 1,25 veces más
TARGET_ORBIT_ALT = 120e3  # perigeo mínimo para "órbita alta"
TARGET_APO = 500e3        # y apogeo mínimo (órbita elíptica alta)
LOW_ORBIT_PER = 100e3


def default_config():
    return {
        "name": "ALBA-1",
        "size": 1,
        "nose": 1,
        "color_body": 0,
        "color_accent": 1,
        "crewed": False,
        "tower": False,
        "fins": True,
        "shield": True,
        "stages": [
            {"engine": 1, "n_eng": 5, "fuel": 0, "tanks": 5},
            {"engine": 1, "n_eng": 2, "fuel": 0, "tanks": 2},
        ],
    }
