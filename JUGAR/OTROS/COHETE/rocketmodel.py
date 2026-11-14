"""Cálculos de masa/Δv del cohete y dibujo del cohete."""
import math
import pygame
from data import *

G0 = 9.80665


def payload_mass(cfg):
    m = PAYLOAD_CREW if cfg["crewed"] else PAYLOAD_SAT
    if cfg["crewed"] and cfg["tower"]:
        m += ESCAPE_TOWER_MASS
    return m


def stage_stats(cfg, i):
    st = cfg["stages"][i]
    eng = ENGINES[st["engine"]]
    fuel = FUELS[st["fuel"]]
    vol = SIZES[cfg["size"]]["vol"]
    prop = st["tanks"] * vol * fuel["dens"]
    dry = st["tanks"] * vol * TANK_DRY_PER_M3 + st["n_eng"] * eng["mass"]
    if i == 0:
        if cfg["fins"]:
            dry += FINS_MASS
        if cfg["shield"]:
            dry += SHIELD_MASS
    thrust = st["n_eng"] * eng["thrust"]
    isp_vac = eng["isp_vac"] * fuel["isp"]
    isp_sl = eng["isp_sl"] * fuel["isp"]
    return {"prop": prop, "dry": dry, "thrust": thrust, "isp_vac": isp_vac,
            "isp_sl": isp_sl, "mdot": thrust / (isp_vac * G0)}


def rocket_summary(cfg):
    """Masa total, Δv total, TWR inicial, coste."""
    n = len(cfg["stages"])
    stats = [stage_stats(cfg, i) for i in range(n)]
    pay = payload_mass(cfg)
    above = pay
    dvs = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = stats[i]
        m0 = above + s["dry"] + s["prop"]
        m1 = above + s["dry"]
        dvs[i] = s["isp_vac"] * G0 * math.log(m0 / m1) if m1 > 0 else 0
        above = m0
    total = above
    twr = stats[0]["thrust"] / (total * G0)
    cost = 0.0
    for i, st in enumerate(cfg["stages"]):
        cost += ENGINES[st["engine"]]["cost"] * st["n_eng"]
        cost += st["tanks"] * SIZES[cfg["size"]]["vol"] * 0.05 * FUELS[st["fuel"]]["cost"]
    cost += 30 if cfg["crewed"] else 10
    cost += 5 if cfg["tower"] and cfg["crewed"] else 0
    return {"mass": total, "dv": dvs, "dv_total": sum(dvs), "twr": twr, "cost": cost, "stats": stats}


# ----------------------------------------------------------------- dibujo
def _shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def rocket_height(cfg, n_stages, scale):
    h = 0
    th = 16 * scale * (1 + cfg["size"] * 0.25)
    for i in range(n_stages):
        h += cfg["stages"][i]["tanks"] * th + 12 * scale
    h += 30 * scale + (18 * scale if cfg["crewed"] else 0)
    if cfg["crewed"] and cfg["tower"]:
        h += 26 * scale
    return h


def draw_rocket(surf, cfg, cx, base_y, scale=1.0, n_stages=None, flame=0.0,
                font=None, frame=0, damaged=None):
    """Dibuja el cohete con la base en base_y (crece hacia arriba). Devuelve altura."""
    if n_stages is None:
        n_stages = len(cfg["stages"])
    body = PALETTE[cfg["color_body"]][1]
    acc = PALETTE[cfg["color_accent"]][1]
    w = SIZES[cfg["size"]]["width"] * scale
    th = 16 * scale * (1 + cfg["size"] * 0.25)
    y = base_y
    first_rect = None
    for i in range(n_stages):
        st = cfg["stages"][i]
        eng = ENGINES[st["engine"]]
        n = st["n_eng"]
        # motores
        bw = min(w / max(n, 1) * 0.9, 16 * scale)
        for k in range(n):
            ex = cx - w / 2 + w * (k + 0.5) / n
            pygame.draw.polygon(surf, (90, 90, 98), [(ex - bw * 0.3, y), (ex + bw * 0.3, y),
                                                      (ex + bw * 0.5, y + 12 * scale), (ex - bw * 0.5, y + 12 * scale)])
            if i == 0 and flame > 0:
                fl = flame * (30 + 14 * math.sin(frame * 0.7 + k)) * scale
                pygame.draw.polygon(surf, (255, 190, 70), [(ex - bw * 0.5, y + 12 * scale), (ex + bw * 0.5, y + 12 * scale),
                                                            (ex, y + 12 * scale + fl)])
                pygame.draw.polygon(surf, (255, 250, 200), [(ex - bw * 0.25, y + 12 * scale), (ex + bw * 0.25, y + 12 * scale),
                                                             (ex, y + 12 * scale + fl * 0.55)])
        if i == 0 and cfg["fins"]:
            pygame.draw.polygon(surf, acc, [(cx - w / 2, y - 4 * scale), (cx - w / 2 - 14 * scale, y + 10 * scale), (cx - w / 2, y - 30 * scale)])
            pygame.draw.polygon(surf, acc, [(cx + w / 2, y - 4 * scale), (cx + w / 2 + 14 * scale, y + 10 * scale), (cx + w / 2, y - 30 * scale)])
        sh = st["tanks"] * th
        rect = pygame.Rect(cx - w / 2, y - sh, w, sh)
        pygame.draw.rect(surf, body, rect)
        pygame.draw.rect(surf, _shade(body, 0.75), (rect.x + w * 0.72, rect.y, w * 0.28, rect.h))
        for t in range(1, st["tanks"]):
            pygame.draw.line(surf, _shade(body, 0.6), (rect.x, rect.bottom - t * th), (rect.right, rect.bottom - t * th), 1)
        pygame.draw.rect(surf, acc, (rect.x, rect.y, w, max(3, 4 * scale)))
        pygame.draw.rect(surf, acc, (rect.x, rect.bottom - max(3, 4 * scale), w, max(3, 4 * scale)))
        if i == 0:
            first_rect = rect
        y -= sh + 12 * scale
        pygame.draw.rect(surf, (60, 60, 66), (cx - w * 0.4, y + 12 * scale - 3 * scale, w * 0.8, 6 * scale))
    y += 12 * scale - 4 * scale
    top = y
    # cápsula / carga
    if cfg["crewed"]:
        ch = 18 * scale
        pygame.draw.rect(surf, _shade(body, 0.9), (cx - w * 0.4, top - ch, w * 0.8, ch))
        pygame.draw.circle(surf, (120, 190, 235), (int(cx), int(top - ch * 0.5)), max(2, int(4 * scale)))
        top -= ch
    # ojiva
    nh = 30 * scale
    ws = w * (0.4 if cfg["crewed"] else 0.5)
    nose = cfg["nose"]
    if nose == 0:
        pts = [(cx - ws, top), (cx + ws, top), (cx, top - nh)]
    elif nose == 1:
        pts = [(cx - ws, top), (cx - ws * 0.7, top - nh * 0.5), (cx - ws * 0.25, top - nh * 0.85), (cx, top - nh),
               (cx + ws * 0.25, top - nh * 0.85), (cx + ws * 0.7, top - nh * 0.5), (cx + ws, top)]
    elif nose == 2:
        pts = [(cx - ws, top), (cx - ws * 0.9, top - nh * 0.5), (cx - ws * 0.5, top - nh * 0.9), (cx, top - nh),
               (cx + ws * 0.5, top - nh * 0.9), (cx + ws * 0.9, top - nh * 0.5), (cx + ws, top)]
    else:
        pts = [(cx - ws, top), (cx - ws * 0.8, top - nh * 0.5), (cx + ws * 0.8, top - nh * 0.5), (cx + ws, top)]
    pygame.draw.polygon(surf, acc, pts)
    top -= nh * (0.5 if nose == 3 else 1)
    if cfg["crewed"] and cfg["tower"]:
        pygame.draw.line(surf, (200, 200, 205), (cx, top), (cx, top - 22 * scale), max(1, int(2 * scale)))
        pygame.draw.polygon(surf, (230, 90, 40), [(cx - 3 * scale, top - 22 * scale), (cx + 3 * scale, top - 22 * scale), (cx, top - 30 * scale)])
        top -= 26 * scale
    if cfg["shield"]:
        pygame.draw.line(surf, (230, 230, 120), (cx, top), (cx, top - 8 * scale), 1)
    # nombre
    if font and first_rect is not None and cfg["name"]:
        txt = font.render(cfg["name"], True, _shade(body, 0.35) if sum(body) > 380 else (245, 245, 245))
        txt = pygame.transform.rotate(txt, 90)
        if txt.get_height() > first_rect.h - 6:
            f = (first_rect.h - 6) / txt.get_height()
            txt = pygame.transform.smoothscale(txt, (max(1, int(txt.get_width() * f)), max(1, int(txt.get_height() * f))))
        surf.blit(txt, (cx - w * 0.15 - txt.get_width() / 2, first_rect.centery - txt.get_height() / 2))
    return base_y - top
