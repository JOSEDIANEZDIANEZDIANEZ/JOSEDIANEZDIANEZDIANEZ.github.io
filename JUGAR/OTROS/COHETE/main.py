"""CohetesGame - construye y prueba cohetes. Ejecuta: python main.py"""
import sys
import os
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui import W, H
from data import default_config
from builder import Builder
from flight import FlightScreen
from sound import Sounds


def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("Cohetes: construye, prueba y... reza")
    clock = pygame.time.Clock()
    snd = Sounds()
    cfg = default_config()
    builder = Builder(cfg)
    flight = None
    mode = "builder"
    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        mouse = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT)):
                pygame.display.toggle_fullscreen()
                continue
            if mode == "builder":
                if builder.handle(event) == "launch":
                    flight = FlightScreen(cfg, snd)
                    mode = "flight"
            else:
                if flight.handle(event) == "builder":
                    snd.stop_all()
                    mode = "builder"
        if mode == "builder":
            builder.draw(screen, mouse)
        else:
            flight.update(dt)
            flight.draw(screen, mouse, dt)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
