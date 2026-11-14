"""Sonido generado por código (sin archivos externos). Si no hay audio, el juego sigue en silencio."""
import math
import random
from array import array
import pygame

RATE = 22050


def _snd(samples, vol=1.0):
    peak = max(1e-9, max(abs(s) for s in samples))
    buf = array("h", [int(max(-1, min(1, s / peak * vol)) * 32000) for s in samples])
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _noise_lp(n, k, rng):
    y, out = 0.0, []
    for _ in range(n):
        y += (rng.uniform(-1, 1) - y) * k
        out.append(y)
    return out


def _tone(freq, dur, decay=4.0, vol=1.0, shape=0):
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        s = math.sin(2 * math.pi * freq * t)
        if shape:
            s = 1.0 if s > 0 else -1.0
        out.append(s * math.exp(-decay * t) * vol)
    return out


class Sounds:
    def __init__(self):
        self.ok = False
        self.muted = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 1, 512)
            pygame.mixer.set_num_channels(12)
            self.build()
            self.ok = True
        except Exception:
            self.ok = False
        self.last_countdown = None
        self.last_status = None
        self.last_log = 0
        self.last_flash = 0.0
        self.alarm_t = 0.0
        self.eng_ch = None
        self.hiss_ch = None

    def build(self):
        r = random.Random(7)
        n = RATE * 2
        low = _noise_lp(n, 0.06, r)
        mid = _noise_lp(n, 0.25, r)
        eng = []
        for i in range(n):
            t = i / RATE
            tone = (math.sin(2 * math.pi * 44 * t) + 0.6 * math.sin(2 * math.pi * 88 * t) + 0.3 * math.sin(2 * math.pi * 132 * t))
            eng.append(low[i] * 2.2 + mid[i] * 0.9 + tone * 0.25)
        self.engine = _snd(eng, 0.9)
        # explosión
        n = int(RATE * 2.8)
        a = _noise_lp(n, 0.5, r)
        b = _noise_lp(n, 0.04, r)
        ex = [(a[i] * 0.6 + b[i] * 2.5) * math.exp(-i / RATE * 1.6) * (1 if i > 40 else i / 40) for i in range(n)]
        self.boom = _snd(ex, 1.0)
        # trueno
        n = int(RATE * 3.0)
        b = _noise_lp(n, 0.03, r)
        th = [b[i] * (math.exp(-i / RATE * 0.9) * (0.6 + 0.4 * math.sin(i / RATE * 17))) for i in range(n)]
        self.thunder = _snd(th, 0.9)
        # ignición
        n = int(RATE * 1.4)
        a = _noise_lp(n, 0.1, r)
        ig = [a[i] * min(1.0, i / (RATE * 0.8)) * (1 - 0.3 * (i / n)) for i in range(n)]
        self.ignite = _snd(ig, 0.8)
        self.beep = _snd(_tone(880, 0.16, 6.0), 0.5)
        self.beep_go = _snd(_tone(1320, 0.5, 3.0), 0.6)
        self.alarm = _snd(_tone(660, 0.18, 2.0, shape=1) + _tone(520, 0.18, 2.0, shape=1), 0.4)
        # separación
        n = int(RATE * 0.5)
        a = _noise_lp(n, 0.2, r)
        sep = [(a[i] * 1.2 + math.sin(2 * math.pi * 70 * i / RATE)) * math.exp(-i / RATE * 9) for i in range(n)]
        self.sep = _snd(sep, 0.9)
        self.click = _snd(_tone(1500, 0.04, 60.0), 0.35)
        n = int(RATE * 0.5)
        h = [(r.uniform(-1, 1) - 0.0) * (0.5 + 0.5 * math.sin(i / n * math.pi)) for i in range(n)]
        hp = []
        prev = 0.0
        for x in h:
            hp.append(x - prev * 0.9)
            prev = x
        self.hiss = _snd(hp, 0.5)
        self.zap = _snd([r.uniform(-1, 1) * math.exp(-i / RATE * 25) for i in range(int(RATE * 0.25))], 0.9)
        notes = [523, 659, 784, 1047]
        win = []
        for k, f in enumerate(notes):
            win += [0.0] * 0 + _tone(f, 0.28, 3.0)
        win += _tone(1047, 0.8, 2.0) + [0.0]
        self.win = _snd(win, 0.6)
        self.lose = _snd(_tone(220, 0.5, 2.5, shape=1) + _tone(165, 0.9, 2.0, shape=1), 0.4)

    # ---------------------------------------------------------------- uso
    def play(self, name, vol=1.0):
        if self.ok and not self.muted:
            s = getattr(self, name)
            s.set_volume(vol)
            s.play()

    def toggle_mute(self):
        self.muted = not self.muted
        if self.ok and self.muted:
            pygame.mixer.stop()
            self.eng_ch = self.hiss_ch = None

    def stop_all(self):
        if self.ok:
            pygame.mixer.stop()
            self.eng_ch = self.hiss_ch = None

    def hold_hiss(self, on):
        if not self.ok or self.muted:
            return
        if on:
            if self.hiss_ch is None or not self.hiss_ch.get_busy():
                self.hiss_ch = self.hiss.play(loops=-1)
                self.hiss.set_volume(0.5)
        elif self.hiss_ch is not None:
            self.hiss_ch.stop()
            self.hiss_ch = None

    def process(self, sim, dt):
        """Llamar cada fotograma: reacciona al estado de la simulación."""
        if not self.ok or self.muted:
            return
        # cuenta atrás
        if sim.status == "countdown":
            n = max(0, math.ceil(sim.countdown))
            if n != self.last_countdown:
                self.play("beep" if n > 0 else "beep_go", 0.8)
                self.last_countdown = n
        # cambio de estado
        if sim.status != self.last_status:
            if sim.status == "orbit":
                self.play("win")
            elif sim.status == "crashed":
                self.play("lose")
            self.last_status = sim.status
        # eventos
        for ev in sim.events:
            if ev[0] == "ignite":
                self.play("ignite", 1.0)
            elif ev[0] == "explosion":
                self.play("boom", 1.0)
            elif ev[0] == "sep":
                self.play("sep", 0.9)
        # avisos nuevos
        for t, msg, lvl in sim.log[-4:]:
            key = (round(t, 2), msg)
            if key != getattr(self, "_seen", None) and lvl == "bad" and t >= self.last_log:
                self.last_log = t
                self._seen = key
                self.play("alarm", 0.7)
        if sim.status == "flying" and (sim.faults.active or sim.sep_timer is not None):
            self.alarm_t -= dt
            if self.alarm_t <= 0:
                self.alarm_t = 1.4
                self.play("alarm", 0.35)
        # rayos
        fl = sim.weather.flash
        if fl > 0.95 and self.last_flash <= 0.95:
            self.play("zap", 0.7)
            self.play("thunder", 0.8)
        self.last_flash = fl
        # motor
        thrust = sim.status == "flying" and sim.thrust_now()[0] > 0
        if thrust:
            vol = (0.15 + 0.85 * sim.throttle) * (0.35 + 0.65 * math.exp(-max(sim.alt, 0) / 25000.0))
            if self.eng_ch is None or not self.eng_ch.get_busy():
                self.eng_ch = self.engine.play(loops=-1)
            if self.eng_ch is not None:
                self.eng_ch.set_volume(vol)
        elif self.eng_ch is not None:
            self.eng_ch.stop()
            self.eng_ch = None
