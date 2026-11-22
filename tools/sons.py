"""Gera os efeitos sonoros e a trilha ambiente dos vídeos, tudo sintetizado aqui (sem arquivos de terceiros,
sem problema de direitos autorais).

Uso:
    python tools/sons.py "projetos/NNN. slug/audio"                  # todos os efeitos
    python tools/sons.py "projetos/NNN. slug/audio" --ambiente 36    # + trilha ambiente de 36 s (use a duração do vídeo)

Efeitos gerados (WAV mono, 48 kHz):
    pop        blip curto: etiqueta ou item que aparece
    tick       clique mínimo: contador, digitação
    whoosh     varredura de ar: troca de cena, card entrando
    brilho     cintilação: revelação, "mágica"
    ding       sino: chamada final, conclusão
    impacto    batida grave: carimbo, palavra de peso
    warp       subida longa: mergulho, transição grande
    caixa      caixa registradora: preço caindo
    rasgo      papel rasgando
    teclado    8 s de digitação (use em loop com volume baixo)
    ambiente   trilha suave (acordes Am-F-C-G em pad, baixo leve e pulso discreto); só com --ambiente

No Remotion: <Audio src={staticFile('NNN. slug/audio/pop.wav')} volume={0.3} /> dentro de um <Sequence from={frame}>.
Volumes que funcionam: efeitos 0.25 a 0.5; ambiente 0.07 sob a voz.
"""
import argparse
import site
import sys
import wave
from pathlib import Path

sys.path.append(site.getusersitepackages())  # numpy instalado no usuário (python -I não o enxerga)

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def tempo(dur):
    return np.arange(int(SR * dur)) / SR


def passa_baixa(x, corte):
    """Filtro de um polo; `corte` pode ser um número ou um vetor (Hz por amostra)."""
    corte = np.broadcast_to(np.asarray(corte, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * corte / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(x.size):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def passa_altas(x, corte):
    return x - passa_baixa(x, corte)


def normaliza(x, pico=0.9):
    return x / (np.abs(x).max() + 1e-9) * pico


def grava(pasta, nome, x, canais=1):
    x = np.clip(x, -1, 1)
    with wave.open(str(pasta / nome), "wb") as w:
        w.setnchannels(canais)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def pop():
    t = tempo(0.18)
    f = 300 + 700 * np.exp(-t / 0.03)
    return normaliza(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05))


def tick():
    t = tempo(0.05)
    return normaliza(passa_altas(rng.standard_normal(t.size), 2500) * np.exp(-t / 0.006))


def whoosh():
    t = tempo(0.6)
    env = np.sin(np.pi * np.clip(t / 0.6, 0, 1)) ** 2
    corte = 300 * (2800 / 300) ** np.clip(t / 0.45, 0, 1)
    ar = passa_baixa(passa_baixa(rng.standard_normal(t.size), corte), corte)  # duas passadas: queda mais suave nos agudos
    return normaliza(ar * env, 0.4)


def brilho():
    x = np.zeros(int(SR * 1.4))
    for _ in range(14):
        ini = int(rng.uniform(0, 0.9) * SR)
        f = rng.uniform(2200, 6500)
        n = int(0.35 * SR)
        tt = np.arange(n) / SR
        bip = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.07) * rng.uniform(0.3, 1)
        x[ini:ini + n] += bip[: x.size - ini]
    return normaliza(x, 0.4)


def ding():
    t = tempo(0.9)
    x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in [(1318, 1.0, 0.28), (2637, 0.5, 0.18), (3951, 0.25, 0.1), (1318 * 2.76, 0.3, 0.08)])
    return normaliza(x * np.minimum(1, t / 0.004))


def impacto():
    t = tempo(0.9)
    f = 48 + 90 * np.exp(-t / 0.08)
    corpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.28)
    ruido = passa_baixa(rng.standard_normal(t.size), 600) * np.exp(-t / 0.05) * 1.5
    return normaliza(corpo + ruido)


def warp():
    t = tempo(1.6)
    f = 90 * (2200 / 90) ** np.clip(t / 1.35, 0, 1)
    tom = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sin(2 * np.pi * 14 * t)) * 0.6
    ar = passa_baixa(passa_baixa(rng.standard_normal(t.size), f * 0.9), f * 0.9) * 0.5
    env = np.minimum(1, t / 0.2) * np.exp(-np.maximum(t - 1.35, 0) / 0.08)
    return normaliza((tom + ar) * env, 0.28)


def caixa():
    t = tempo(1.1)
    x = rng.standard_normal(t.size) * np.exp(-t / 0.008) * 0.6
    gaveta = np.convolve(rng.standard_normal(t.size), np.ones(40) / 40, "same") * 2.5
    x += np.exp(-np.maximum(t - 0.05, 0) / 0.06) * (t > 0.05) * gaveta
    for ini, f0, a in [(0.12, 2093, 0.8), (0.24, 2637, 1.0)]:
        tt = np.maximum(t - ini, 0)
        env = (t > ini) * np.exp(-tt / 0.35)
        x += a * env * (np.sin(2 * np.pi * f0 * tt) + 0.5 * np.sin(2 * np.pi * f0 * 2.76 * tt) + 0.25 * np.sin(2 * np.pi * f0 * 5.4 * tt))
    return normaliza(x)


def rasgo():
    t = tempo(0.7)
    n = rng.standard_normal(t.size)
    n = n - np.convolve(n, np.ones(6) / 6, "same")
    raj = np.clip(np.convolve((rng.random(t.size) < 0.004).astype(float), np.hanning(600), "same"), 0, 1)
    return normaliza(n * (0.35 + raj) * np.minimum(1, t / 0.02) * np.exp(-t / 0.35))


def teclado(dur=8.0):
    x = np.zeros(int(SR * dur))
    pos = 0.1
    while pos < dur - 0.1:
        n = int(0.03 * SR)
        tt = np.arange(n) / SR
        clique = passa_altas(rng.standard_normal(n), rng.uniform(1500, 3500)) * np.exp(-tt / 0.005)
        corpo = np.sin(2 * np.pi * rng.uniform(140, 220) * tt) * np.exp(-tt / 0.012) * 0.5
        i = int(pos * SR)
        x[i:i + n] += (clique + corpo) * rng.uniform(0.5, 1.0)
        pos += rng.uniform(0.07, 0.2)
    return normaliza(x, 0.6)


def ambiente(dur, bpm=96):
    """Pad macio em Am-F-C-G, baixo leve e um pulso de 'tique' bem baixo. Estéreo, com entrada e saída suaves."""
    t = tempo(dur)
    nota = lambda n: 440.0 * 2 ** ((n - 69) / 12)
    acordes = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]]
    baixos = [45, 41, 36, 43]
    compasso = 4 * 60 / bpm
    pad = np.zeros_like(t)
    baixo = np.zeros_like(t)
    for c in range(int(np.ceil(dur / compasso))):
        a, b = c * compasso, (c + 1) * compasso + 0.6
        m = (t >= a) & (t < b)
        tt = t[m] - a
        env = np.minimum(1, tt / 0.6) * np.minimum(1, np.maximum(0, (b - a - tt)) / 0.6)
        i = c % 4
        for n in acordes[i]:
            for det in (-0.12, 0.12):  # leve desafinação = efeito de coro
                fase = 2 * np.pi * nota(n) * (1 + det / 100) * tt + rng.random() * 6.28
                pad[m] += env * (np.sin(fase) + 0.25 * np.sin(2 * fase)) / 8
        baixo[m] += env * np.sin(2 * np.pi * nota(baixos[i]) * tt) * 0.35
    tique = np.zeros_like(t)
    passo = 60 / bpm / 2
    for k in range(int(dur / passo)):
        i0, n = int(k * passo * SR), int(0.03 * SR)
        if i0 + n >= t.size:
            break
        r = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.006 * SR))
        tique[i0:i0 + n] += (r - np.convolve(r, np.ones(4) / 4, "same")) * (0.10 if k % 2 == 0 else 0.06)
    x = np.convolve(pad + baixo + tique, np.ones(6) / 6, "same")
    x *= np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 2.0)
    x = normaliza(x, 0.8)
    return np.stack([x, np.roll(x, int(0.012 * SR))], 1).reshape(-1)  # estéreo entrelaçado


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Gera efeitos sonoros e trilha ambiente sintetizados.")
    p.add_argument("pasta", help="pasta de saída, por exemplo 'projetos/012. slug/audio'")
    p.add_argument("--ambiente", type=float, default=0, help="gera também ambiente.wav com essa duração (s)")
    a = p.parse_args()
    pasta = Path(a.pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, f in [("pop", pop), ("tick", tick), ("whoosh", whoosh), ("brilho", brilho), ("ding", ding), ("impacto", impacto),
                    ("warp", warp), ("caixa", caixa), ("rasgo", rasgo), ("teclado", teclado)]:
        grava(pasta, f"{nome}.wav", f())
    if a.ambiente > 0:
        grava(pasta, "ambiente.wav", ambiente(a.ambiente), canais=2)
    print("ok:", ", ".join(sorted(x.name for x in pasta.glob("*.wav"))))
