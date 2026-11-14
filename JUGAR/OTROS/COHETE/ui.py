"""Utilidades de interfaz."""
import pygame

W, H = 1280, 720
BG = (14, 17, 26)
PANEL = (24, 29, 42)
PANEL2 = (34, 41, 58)
TEXT = (225, 230, 240)
DIM = (130, 140, 160)
GOOD = (80, 210, 120)
WARN = (240, 190, 60)
BAD = (240, 70, 60)
ACCENT = (80, 160, 255)

_fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("dejavusans,arial,liberationsans", size, bold=bold)
    return _fonts[key]


def text(surf, s, pos, size=16, color=TEXT, bold=False, anchor="topleft"):
    img = font(size, bold).render(str(s), True, color)
    r = img.get_rect()
    setattr(r, anchor, pos)
    surf.blit(img, r)
    return r


def panel(surf, rect, color=PANEL, border=None, radius=8):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, 2, border_radius=radius)


class Button:
    def __init__(self, rect, label, color=PANEL2, hot=ACCENT, size=16):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.hot = hot
        self.size = size
        self.enabled = True

    def draw(self, surf, mouse):
        over = self.enabled and self.rect.collidepoint(mouse)
        col = self.hot if over else self.color
        if not self.enabled:
            col = (45, 48, 58)
        panel(surf, self.rect, col, radius=6)
        text(surf, self.label, self.rect.center, self.size, TEXT if self.enabled else DIM, True, "center")

    def clicked(self, event):
        return (self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))


def bar(surf, rect, frac, color, back=(45, 50, 66)):
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surf, back, rect, border_radius=3)
    pygame.draw.rect(surf, color, (rect[0], rect[1], rect[2] * frac, rect[3]), border_radius=3)
