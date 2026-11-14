"""Ciudades bajo la trayectoria (distancia en metros desde la plataforma, nombre, edificios)."""
CITIES = [
    (-9000, "Puerto Alba", 7),
    (3000, "Villa Roca", 5),
    (14000, "Monte Claro", 6),
    (30000, "San Cohete", 8),
    (52000, "Bahía Sol", 7),
    (80000, "Nueva Esperanza", 9),
    (120000, "Ciudad Hierro", 10),
]


def hit_cities(downrange, alt):
    """Índices de ciudades alcanzadas por los restos de una explosión accidental."""
    if alt > 120e3:
        return []
    radius = 6000 + alt * 0.5
    return [i for i, c in enumerate(CITIES) if abs(c[0] - downrange) <= radius]
