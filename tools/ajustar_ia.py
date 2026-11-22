"""Ajusta um trecho que voltou da IA (troca de roupa ou de cenário) para entrar na montagem: mesma duração do
trecho que você enviou, 1080×1920 a 30 fps, sem áudio, e confere se a boca continua acompanhando a voz.

Por que: a IA devolve o vídeo com duração diferente do original (um trecho de 2,5 s pode voltar com 4 s, em câmera
lenta). Se você usar assim, a boca fica atrasada em relação à voz, que vem sempre do vídeo gravado.

Uso:
    python tools/ajustar_ia.py <trecho enviado.mp4> <trecho da IA.mp4> <saida.mp4> [--zoom 1.3]

    --zoom   aproxima a imagem (1.3 = 30%) mantendo o centro: serve para deixar emblema ou logo que a IA colocou na roupa fora do quadro
    --vertical / --horizontal   formato de saída (padrão: vertical 1080×1920)

A conferência compara o movimento da região do rosto no trecho enviado e no ajustado (1,00 = igual; acima de 0,85 está bom).
Abaixo disso, olhe o resultado antes de usar: a IA pode ter mudado o gesto ou a fala.
"""
import argparse
import site
import subprocess
import sys

sys.path.append(site.getusersitepackages())

import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

p = argparse.ArgumentParser(description="Retemporiza e confere o trecho devolvido pela IA.")
p.add_argument("enviado")
p.add_argument("ia")
p.add_argument("saida")
p.add_argument("--zoom", type=float, default=1.0)
g = p.add_mutually_exclusive_group()
g.add_argument("--vertical", action="store_true")
g.add_argument("--horizontal", action="store_true")
a = p.parse_args()
LARG, ALT = (1920, 1080) if a.horizontal else (1080, 1920)


def duracao(arq):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq],
                                capture_output=True, text=True, check=True).stdout)


d_env, d_ia = duracao(a.enviado), duracao(a.ia)
fator = d_env / d_ia
filtro = f"setpts=PTS*({d_env}/{d_ia}),scale={int(LARG * a.zoom)}:{int(ALT * a.zoom)}:flags=lanczos"
if a.zoom != 1.0:
    filtro += f",crop={LARG}:{ALT}"
filtro += ",fps=30"
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", a.ia, "-an", "-vf", filtro, "-t", str(d_env), "-c:v", "libx264",
                "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.saida], check=True)


def movimento(arq):
    cap = cv2.VideoCapture(arq)
    prev, serie = None, []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        h, w = f.shape[:2]
        reg = cv2.cvtColor(cv2.resize(f[int(h * 0.3):int(h * 0.6), int(w * 0.3):int(w * 0.7)], (96, 96)), cv2.COLOR_BGR2GRAY).astype(np.float32)
        serie.append(0.0 if prev is None else float(np.abs(reg - prev).mean()))
        prev = reg
    return np.convolve(np.array(serie), np.ones(5) / 5, "same")


x, y = movimento(a.enviado), movimento(a.saida)
m = min(len(x), len(y))
melhor = max((np.corrcoef(x[max(0, -s):m - max(0, s)], y[max(0, s):m - max(0, -s)])[0, 1], s) for s in range(-8, 9))
estado = "bom" if melhor[0] >= 0.85 else "CONFIRA o resultado"
print(f"duração: enviado {d_env:.2f} s, IA {d_ia:.2f} s, fator de ajuste {fator:.3f}")
print(f"sincronia da boca: {melhor[0]:.2f} (deslocamento de {melhor[1]} quadros) → {estado}")
print(f"gravado em {a.saida}")
