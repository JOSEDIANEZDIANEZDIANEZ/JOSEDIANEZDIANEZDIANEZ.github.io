"""Térmica, presión, vibración y fallos aleatorios."""
import math

from datos import MOTORES, COMBUSTIBLES

QMAX_BASE = 48_000.0      # Pa, presión dinámica estructural antes de ajustar por tamaño


def _prob(rng, tasa, dt):
    return rng.random() < 1.0 - math.exp(-tasa * dt)


def _una_vez(v, clave, txt, nivel=1):
    if clave not in v.avisos:
        v.avisos.add(clave)
        v.anota(txt, nivel)


def qmax(v):
    return QMAX_BASE * v.tam["estruct"]


def dano_estructural(v, cantidad, causa):
    if v.estado == "destruido":
        return
    v.integridad -= cantidad
    if v.integridad <= 0:
        v.explotar(f"Fallo estructural: {causa}")


def sellar(v):
    """Intentar sellar una fuga (tecla L)."""
    e = v.et
    if v.estado != "volando" or e is None or v.t_sellar > 0:
        return
    v.t_sellar = 6.0
    if e.fuga <= 0:
        v.anota("No se detecta ninguna fuga", 0)
    elif v.rng.random() < 0.55:
        e.fuga = 0.0
        v.anota("Fuga sellada", 1)
    else:
        e.fuga *= 0.7
        v.anota("El sellado no ha funcionado del todo", 2)


def actualiza_etapa(v, dt):
    """Temperatura del motor, presión del tanque y vibración de la etapa activa."""
    e = v.et
    if e is None:
        return
    mot = MOTORES[e.e.motor]
    com = COMBUSTIBLES[e.e.combustible]
    thr = getattr(v, "thr_efectivo", 0.0)

    # --- temperatura del motor
    if e.encendida and not e.agotada:
        eq = 300 + 600 * thr * mot["calor"] * com["calor"]
        if v.enfriar and v.refrigerante > 0:
            eq -= 250
            v.refrigerante = max(0.0, v.refrigerante - 5.0 * dt)
        tau = 25.0
    else:
        eq = 25.0
        tau = 40.0
    e.temp += (eq - e.temp) * (1 - math.exp(-dt / tau))

    # --- presión del tanque
    if e.encendida and not e.agotada:
        e.presion += 0.045 * com["riesgo"] * (0.6 + 0.8 * thr) * dt
        if e.temp > 900:
            e.presion += 0.02 * dt * (e.temp - 900) / 100
    if v.ventear:
        e.presion -= 0.8 * dt
    e.presion = max(1.0, e.presion)

    # --- vibración (incluye resonancia "pogo" a cierto acelerador)
    obj = 5.0
    if e.encendida and not e.agotada:
        obj = 8 + 25 * thr + 35 * min(1.0, v.q / (0.7 * qmax(v)))
        d = abs(thr - e.res_pogo)
        if d < 0.08:
            obj += 45 * (1 - d / 0.08)
        obj += min(20.0, abs(v.desv) * 1.5)
        if v.amort:
            obj *= 0.55
    e.vib += (obj - e.vib) * (1 - math.exp(-dt / 1.5))

    # --- viento y actitud
    w = abs(v.meteo.viento(v.alt, v.t_vuelo))
    s = (w / 30.0) * (v.q / 30_000.0) * 3.0
    if s > 0:
        v.desv += v.rng.gauss(0, 1) * s * math.sqrt(dt)
    v.desv = max(-30.0, min(30.0, v.desv))


def riesgos(v, dt):
    """Todos los modos de fallo. El orden importa poco; cualquier cosa puede pasar."""
    if v.estado != "volando":
        return
    rng = v.rng
    e = v.et
    meteo = v.meteo
    qm = qmax(v)

    # ================= estructura =================
    if v.q > 0.85 * qm:
        dano_estructural(v, 0.05 * dt * (v.q / qm - 0.7) * 10, "presión dinámica excesiva (Max-Q)")
        _una_vez(v, "maxq", "¡PRESIÓN DINÁMICA CRÍTICA! Reduce el acelerador", 2)
    if abs(v.desv) > 10 and v.q > 10_000:
        dano_estructural(v, 0.03 * dt * (abs(v.desv) - 10), "ángulo de ataque excesivo")
        _una_vez(v, "aoa", "Ángulo de ataque excesivo", 2)
    if v.temp_casco > 900:
        dano_estructural(v, 0.04 * dt * (v.temp_casco - 900) / 100, "sobrecalentamiento del casco")
        _una_vez(v, "casco", "Casco sobrecalentándose", 2)
    if v.temp_casco > 1300:
        v.explotar("Fusión del casco por rozamiento")
        return

    if e and e.encendida:
        # ================= vibración =================
        if e.vib > 85:
            dano_estructural(v, 0.025 * dt * (e.vib - 80) / 20, "vibraciones (efecto pogo)")
            _una_vez(v, f"vib{v.i}", f"Vibración peligrosa en etapa {v.i + 1}: cambia el acelerador", 2)

        # ================= temperatura del motor =================
        if e.temp > 950:
            _una_vez(v, f"temp{v.i}", f"Motor de etapa {v.i + 1} muy caliente", 1)
        if e.temp > 1150 and _prob(rng, 0.05 * ((e.temp - 1150) / 100 + 1), dt):
            _fallo_motor(v, e, "sobrecalentamiento")
            if v.estado == "destruido":
                return
        if e.temp > 1400:
            v.explotar("Fusión del motor por sobrecalentamiento")
            return

        # ================= presión del tanque =================
        if e.presion > 5.5:
            _una_vez(v, f"pres{v.i}", f"Presión alta en el tanque {v.i + 1}: ventea", 1)
        if e.presion > 6.2 and _prob(rng, 0.08 * (e.presion - 6.0), dt):
            v.explotar(f"Rotura del tanque {v.i + 1} por sobrepresión")
            return
        if e.presion > 8.0:
            v.explotar(f"Explosión del tanque {v.i + 1} por sobrepresión")
            return

        # ================= fallo de motor (la suerte) =================
        com = COMBUSTIBLES[e.e.combustible]
        mot = MOTORES[e.e.motor]
        estres = com["riesgo"]
        estres *= 1 + 3 * max(0.0, (e.temp - 900) / 200)
        estres *= 1 + max(0.0, (e.vib - 50) / 40)
        estres *= 1 + max(0.0, v.q / qm - 0.5)
        tasa = (1 - mot["fiab"]) * 6.0 / 100.0 * estres * e.motores
        if tasa > 0 and _prob(rng, tasa, dt):
            _fallo_motor(v, e, "fallo mecánico")
            if v.estado == "destruido":
                return

        # ================= fugas =================
        tasa_fuga = 0.0008 * com["riesgo"] * (1 + 3 * meteo.frio) * (1.0 if v.alt < 25_000 else 0.4)
        if e.fuga <= 0 and _prob(rng, tasa_fuga, dt):
            e.fuga = rng.uniform(15, 60) * (e.comb0 / 9000.0)
            v.anota(f"FUGA DE COMBUSTIBLE en etapa {v.i + 1} - pulsa L para sellar", 2)
        if e.fuga > 0 and e.temp > 800 and _prob(rng, 0.01 * (e.temp - 700) / 100, dt):
            v.explotar("Incendio por fuga de combustible")
            return

    # ================= eléctrico y rayos =================
    if v.alt < 18_000 and meteo.datos["rayos"] > 0 and _prob(rng, meteo.datos["rayos"], dt):
        v.rayo_t = v.t_vuelo
        v.anota("¡IMPACTO DE RAYO!", 3)
        r = rng.random()
        if r < 0.18:
            v.explotar("Impacto directo de un rayo")
            return
        elif r < 0.70:
            v.giro_fallo = max(v.giro_fallo, 10.0)
            v.energia = max(0.0, v.energia - 20)
            v.anota("Aviónica dañada: sin control de actitud unos segundos", 2)
        else:
            dano_estructural(v, 0.12, "daños por rayo")
    if _prob(rng, 0.0006 * meteo.datos["elec"], dt) and v.giro_fallo <= 0:
        v.giro_fallo = 8.0
        v.anota("FALLO DE GUIADO: sin control de actitud", 2)

    # ================= pura mala suerte =================
    if _prob(rng, 0.00012, dt):
        v.explotar("Fallo catastrófico inesperado")


def _fallo_motor(v, e, causa):
    """Un motor falla: lo habitual es perder empuje; a veces explota todo."""
    if v.rng.random() < 0.30:
        v.explotar(f"Explosión de motor en etapa {v.i + 1} ({causa})")
        return
    if e.e.n_motores > 1 and e.motores > 1:
        e.motores -= 1
        v.anota(f"MOTOR APAGADO en etapa {v.i + 1} ({causa}) - quedan {e.motores}", 2)
    else:
        e.motores = 0
        e.encendida = False
        v.anota(f"APAGADO DEL MOTOR en etapa {v.i + 1} ({causa})", 3)
