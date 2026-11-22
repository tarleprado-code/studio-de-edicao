"""Tira o fundo de um vídeo com o Robust Video Matting (RVM), rodando local no processador.

Gera um .mov ProRes 4444 com transparência, pronto para o Remotion (<OffthreadVideo transparent>).
O RVM é feito para vídeo: guarda memória entre os quadros, então a borda treme bem menos que um
recorte quadro a quadro, e é muito mais rápido.

Modelos (licença GPL-3.0, de https://github.com/PeterL1n/RobustVideoMatting/releases/tag/v1.0.0),
salvos em ~/.rvm/ (baixados sozinhos na primeira vez):  rvm_mobilenetv3_fp32.onnx (rápido)  ·  rvm_resnet50_fp32.onnx (mais fino, mais lento)
Dependências: pip install onnxruntime opencv-python-headless numpy (o npm run instalar já faz isso)

Uso:
    python tools/recorte_rvm.py "projetos/NNN. slug/video/master-ritmo.mp4" "projetos/NNN. slug/assets/recorte.mov"
    opções: --inicio 0 --duracao 0 (0 = até o fim) --modelo mobilenet|resnet --ratio 0.375
            --teste quadro.png  (gera só uma imagem de conferência sobre fundo escuro, no meio do trecho)
"""
import argparse
import site
import subprocess
import sys
import time
from pathlib import Path

sys.path.append(site.getusersitepackages())  # onnxruntime e cv2 instalados no usuário

import numpy as np
import onnxruntime as ort

RELEASE = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/"
MODELOS = {
    "mobilenet": Path.home() / ".rvm" / "rvm_mobilenetv3_fp32.onnx",
    "resnet": Path.home() / ".rvm" / "rvm_resnet50_fp32.onnx",
}


def garantir_modelo(nome):
    """Baixa o modelo oficial na primeira vez (urllib, porque o curl do Windows falha em alguns computadores)."""
    caminho = MODELOS[nome]
    if not caminho.exists():
        import urllib.request
        caminho.parent.mkdir(parents=True, exist_ok=True)
        print(f"Baixando {caminho.name} de {RELEASE} ...")
        dados = urllib.request.urlopen(urllib.request.Request(RELEASE + caminho.name, headers={"User-Agent": "studio"}), timeout=600).read()
        caminho.write_bytes(dados)
    return caminho

p = argparse.ArgumentParser()
p.add_argument("entrada", nargs="?")
p.add_argument("saida", nargs="?")
p.add_argument("--baixar", action="store_true", help="só baixa o modelo rápido e sai (usado pelo npm run instalar)")
p.add_argument("--inicio", type=float, default=0.0)
p.add_argument("--duracao", type=float, default=0.0)
p.add_argument("--modelo", choices=MODELOS, default="mobilenet")
p.add_argument("--ratio", type=float, default=0.375, help="0.25 a 0.5; maior = borda mais fina e mais lento")
p.add_argument("--teste", default=None)
a = p.parse_args()
if a.baixar:
    print("Modelo pronto:", garantir_modelo("mobilenet"))
    sys.exit(0)
if not a.entrada or not a.saida:
    p.error("informe a entrada e a saída (ou use --baixar)")

info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                       "-of", "csv=p=0", a.entrada], capture_output=True, text=True, check=True).stdout.strip().split(",")
W, H = int(info[0]), int(info[1])
num, den = info[2].split("/")
FPS = float(num) / float(den)

so = ort.SessionOptions()
so.intra_op_num_threads = 0  # usa todos os núcleos
sess = ort.InferenceSession(str(garantir_modelo(a.modelo)), so, providers=["CPUExecutionProvider"])

ler = ["ffmpeg", "-v", "error", "-ss", str(a.inicio), "-i", a.entrada]
if a.duracao > 0:
    ler += ["-t", str(a.duracao)]
leitor = subprocess.Popen(ler + ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

gravador = None
if not a.teste:
    gravador = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", f"{FPS}",
                                 "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", a.saida],
                                stdin=subprocess.PIPE)

rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
ratio = np.array([a.ratio], np.float32)
alvo_teste = int(FPS * (a.duracao / 2 if a.duracao > 0 else 1.0))
n, t0 = 0, time.time()
tam = W * H * 3
while True:
    buf = leitor.stdout.read(tam)
    if len(buf) < tam:
        break
    rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    src = (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
    fgr, pha, *rec = sess.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3], "downsample_ratio": ratio})
    cor = (np.clip(fgr[0].transpose(1, 2, 0), 0, 1) * 255).astype(np.uint8)
    alfa = (np.clip(pha[0, 0], 0, 1) * 255).astype(np.uint8)
    if a.teste:
        if n == alvo_teste:
            import cv2
            fundo = np.zeros_like(cor)
            fundo[:] = (30, 25, 50)
            k = alfa[..., None].astype(np.float32) / 255.0
            comp = (cor * k + fundo * (1 - k)).astype(np.uint8)
            cv2.imwrite(a.teste, cv2.cvtColor(comp, cv2.COLOR_RGB2BGR))
            break
    else:
        gravador.stdin.write(np.dstack([cor, alfa]).tobytes())
    n += 1

leitor.stdout.close()
leitor.terminate()
if gravador:
    gravador.stdin.close()
    gravador.wait()
dt = time.time() - t0
print(f"quadros: {n}  tempo: {dt:.1f}s  ({n / dt if dt else 0:.2f} quadros/s, modelo {a.modelo}, ratio {a.ratio})")
