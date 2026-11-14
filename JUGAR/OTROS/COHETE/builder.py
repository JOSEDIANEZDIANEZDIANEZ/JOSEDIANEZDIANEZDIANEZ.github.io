"""Etapa 1: construcción del cohete."""
import pygame
from data import *
from ui import *
from rocketmodel import draw_rocket, rocket_summary, rocket_height


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Builder:
    ROW_H = 30
    LIST_RECT = pygame.Rect(20, 70, 520, 560)

    def __init__(self, cfg):
        self.cfg = cfg
        self.sel = 0
        self.scroll = 0
        self.editing = False
        self.btn_launch = Button((20, 650, 330, 50), "LLEVAR A LA PLATAFORMA (Enter)", (40, 120, 70), (60, 170, 100), 17)
        self.btn_reset = Button((365, 650, 175, 50), "Reiniciar diseño", PANEL2)
        self.tick = 0
        self.rows = []

    # ---------------------------------------------------------- filas
    def build_rows(self):
        c = self.cfg
        rows = []

        def choice(label, get, setter, n, fmt):
            rows.append({"label": label, "value": fmt(get()), "change": lambda d, g=get, s=setter, n=n: s((g() + d) % n)})

        def number(label, get, setter, lo, hi, fmt=str):
            rows.append({"label": label, "value": fmt(get()), "change": lambda d, g=get, s=setter, lo=lo, hi=hi: s(_clamp(g() + d, lo, hi))})

        def toggle(label, key, enabled=True):
            rows.append({"label": label, "value": "SÍ" if c[key] else "NO",
                         "change": (lambda d, k=key: c.__setitem__(k, not c[k])) if enabled else (lambda d: None)})

        rows.append({"label": "Nombre del cohete", "value": c["name"] + ("_" if self.editing and self.tick % 40 < 20 else ""),
                     "change": lambda d: None, "edit": True})
        choice("Tamaño del cuerpo", lambda: c["size"], lambda v: c.__setitem__("size", v), len(SIZES), lambda v: SIZES[v]["name"])
        choice("Forma de la ojiva", lambda: c["nose"], lambda v: c.__setitem__("nose", v), len(NOSES), lambda v: NOSES[v])
        choice("Color del cuerpo", lambda: c["color_body"], lambda v: c.__setitem__("color_body", v), len(PALETTE), lambda v: PALETTE[v][0])
        choice("Color de detalles", lambda: c["color_accent"], lambda v: c.__setitem__("color_accent", v), len(PALETTE), lambda v: PALETTE[v][0])
        toggle("Aletas estabilizadoras", "fins")
        toggle("Pararrayos / blindaje", "shield")
        toggle("Tripulado", "crewed")
        toggle("Torre de escape (solo tripulado)", "tower", c["crewed"])

        def set_stages(v):
            while len(c["stages"]) < v:
                c["stages"].append({"engine": 3, "n_eng": 1, "fuel": 0, "tanks": 2})
            while len(c["stages"]) > v:
                c["stages"].pop()
        number("Número de etapas", lambda: len(c["stages"]), set_stages, 1, MAX_STAGES)

        for i, st in enumerate(c["stages"]):
            rows.append({"header": f"— ETAPA {i + 1}" + (" (inferior)" if i == 0 else "") + " —"})
            choice("  Motor", lambda st=st: st["engine"], lambda v, st=st: st.__setitem__("engine", v), len(ENGINES), lambda v: ENGINES[v]["name"])
            number("  Nº de motores", lambda st=st: st["n_eng"], lambda v, st=st: st.__setitem__("n_eng", v), 1, MAX_ENGINES)
            choice("  Combustible", lambda st=st: st["fuel"], lambda v, st=st: st.__setitem__("fuel", v), len(FUELS), lambda v: FUELS[v]["name"])
            number("  Tanques", lambda st=st: st["tanks"], lambda v, st=st: st.__setitem__("tanks", v), 1, MAX_TANKS)
        return rows

    def selectable(self):
        return [i for i, r in enumerate(self.rows) if "header" not in r]

    def move(self, d):
        sel = self.selectable()
        if self.sel not in sel:
            self.sel = sel[0]
        k = sel.index(self.sel)
        self.sel = sel[(k + d) % len(sel)]

    # ---------------------------------------------------------- eventos
    def handle(self, event):
        """Devuelve 'launch' cuando el jugador quiere ir a la plataforma."""
        self.rows = self.build_rows()
        if self.editing:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.editing = False
                elif event.key == pygame.K_BACKSPACE:
                    self.cfg["name"] = self.cfg["name"][:-1]
                elif event.unicode and event.unicode.isprintable() and len(self.cfg["name"]) < 14:
                    self.cfg["name"] += event.unicode.upper()
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.move(-1)
            elif event.key == pygame.K_DOWN:
                self.move(1)
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.rows[self.sel]["change"](-1 if event.key == pygame.K_LEFT else 1)
            elif event.key == pygame.K_RETURN:
                if self.rows[self.sel].get("edit"):
                    self.editing = True
                else:
                    return "launch"
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_launch.clicked(event):
                return "launch"
            if self.btn_reset.clicked(event):
                self.cfg.update(default_config())
                return None
            if self.LIST_RECT.collidepoint(event.pos):
                idx = (event.pos[1] - self.LIST_RECT.y) // self.ROW_H + self.scroll
                if 0 <= idx < len(self.rows) and "header" not in self.rows[idx]:
                    self.sel = idx
                    x = event.pos[0] - self.LIST_RECT.x
                    if self.rows[idx].get("edit"):
                        self.editing = True
                    elif x > 250:
                        self.rows[idx]["change"](-1 if x < 385 else 1)
        return None

    # ---------------------------------------------------------- dibujo
    def draw(self, surf, mouse):
        self.tick += 1
        self.rows = self.build_rows()
        if self.sel >= len(self.rows) or "header" in self.rows[self.sel]:
            self.move(1)
        surf.fill(BG)
        text(surf, "FASE 1 · CONSTRUCCIÓN DEL COHETE", (20, 20), 26, ACCENT, True)
        text(surf, "↑↓ elegir · ←→ cambiar (o clic) · Enter en el nombre para escribir", (20, 50), 13, DIM)
        panel(surf, self.LIST_RECT.inflate(10, 10))
        vis = self.LIST_RECT.h // self.ROW_H
        if self.sel < self.scroll:
            self.scroll = self.sel
        if self.sel >= self.scroll + vis:
            self.scroll = self.sel - vis + 1
        for k in range(vis):
            i = self.scroll + k
            if i >= len(self.rows):
                break
            r = self.rows[i]
            y = self.LIST_RECT.y + k * self.ROW_H
            if "header" in r:
                text(surf, r["header"], (self.LIST_RECT.x + 8, y + 6), 15, WARN, True)
                continue
            row = pygame.Rect(self.LIST_RECT.x, y, self.LIST_RECT.w, self.ROW_H - 2)
            if i == self.sel:
                panel(surf, row, PANEL2, ACCENT, 5)
            text(surf, r["label"], (row.x + 10, row.y + 5), 16, TEXT)
            if r.get("edit"):
                text(surf, r["value"], (row.x + 260, row.y + 5), 16, ACCENT, True)
            else:
                text(surf, "◄", (row.x + 262, row.y + 5), 16, DIM)
                text(surf, r["value"], (row.x + 320, row.y + 5), 16, ACCENT, True, "midtop")
                text(surf, "►", (row.x + 486, row.y + 5), 16, DIM)
        self.btn_launch.draw(surf, mouse)
        self.btn_reset.draw(surf, mouse)
        self.draw_preview(surf)

    def draw_preview(self, surf):
        area = pygame.Rect(570, 70, 690, 630)
        panel(surf, area)
        s = rocket_summary(self.cfg)
        # rejilla
        for gx in range(area.x, area.right, 40):
            pygame.draw.line(surf, (30, 36, 52), (gx, area.y), (gx, area.bottom))
        for gy in range(area.y, area.bottom, 40):
            pygame.draw.line(surf, (30, 36, 52), (area.x, gy), (area.right, gy))
        h = rocket_height(self.cfg, len(self.cfg["stages"]), 1.0)
        scale = min(1.5, (area.h - 110) / max(h, 1))
        draw_rocket(surf, self.cfg, area.x + 170, area.bottom - 60, scale, font=font(14, True))
        pygame.draw.rect(surf, (60, 66, 82), (area.x + 20, area.bottom - 48, 300, 8))
        # estadísticas
        x = area.x + 360
        text(surf, "ESPECIFICACIONES", (x, area.y + 18), 18, ACCENT, True)
        lines = [("Masa total", f"{s['mass'] / 1000:,.0f} t"),
                 ("Empuje / peso inicial", f"{s['twr']:.2f}"),
                 ("Δv total (vacío)", f"{s['dv_total']:,.0f} m/s"),
                 ("Coste estimado", f"{s['cost']:,.0f} M€"),
                 ("Carga", "Tripulación" if self.cfg["crewed"] else "Satélite")]
        for k, (a, b) in enumerate(lines):
            text(surf, a, (x, area.y + 55 + k * 26), 15, DIM)
            text(surf, b, (x + 320, area.y + 55 + k * 26), 15, TEXT, True, "topright")
        y = area.y + 200
        for i, dv in enumerate(s["dv"]):
            text(surf, f"Δv etapa {i + 1}", (x, y), 14, DIM)
            bar(surf, (x + 100, y + 3, 120, 12), dv / 8000, ACCENT)
            text(surf, f"{dv:,.0f} m/s", (x + 320, y), 14, TEXT, False, "topright")
            y += 24
        # consejos
        tips = []
        if s["twr"] < 1.05:
            tips.append(("⚠ Empuje insuficiente: el cohete apenas despegará.", BAD))
        elif s["twr"] < 1.2:
            tips.append(("Empuje justo: añade motores o quita peso.", WARN))
        if s["dv_total"] < 9000:
            tips.append(("Δv bajo: para órbita alta necesitas ~9500–11000 m/s.", WARN))
        elif s["dv_total"] > 9300:
            tips.append(("Δv suficiente para alcanzar órbita. ¡Buena base!", GOOD))
        if self.cfg["crewed"]:
            tips.append(("Tripulado: más peso, más puntos… y más responsabilidad.", DIM))
        yy = area.y + 290
        text(surf, "ANÁLISIS", (x, yy), 18, ACCENT, True)
        for k, (t, c) in enumerate(tips):
            text(surf, t, (x, yy + 34 + k * 24), 14, c)
