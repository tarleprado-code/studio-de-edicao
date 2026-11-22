"""Ritmo: corta as pausas e acelera a fala (por padrão 10%), sem mexer no vídeo original.

Uso:
    python tools/ritmo.py "projetos/NNN. slug"
    python tools/ritmo.py "projetos/NNN. slug" --velocidade 1.15 --fim 36.7 --corrigir "Cláudio=Claude"

Lê:
    <projeto>/video/master.mp4                 (fica intacto)
    <projeto>/transcricao/palavras.json        (de tools/transcrever.py)
    <projeto>/ritmo.json                       (opcional, veja abaixo)
Grava:
    <projeto>/video/master-ritmo.mp4           vídeo e áudio sem as pausas e 10% mais rápidos
    src/videos/<slug>/ritmo.ts                 TRECHOS (o que foi mantido do original, em s) e VELOCIDADE
    src/videos/<slug>/dados.ts                 PALAVRAS [palavra, início, fim] já no tempo original corrigido

No Remotion, use src/_shared/ritmo.ts: `const {M, DURACAO_FRAMES} = criarRitmo(TRECHOS, VELOCIDADE)`.
M(tempo no vídeo gravado) devolve o tempo no vídeo com ritmo. Toda animação continua amarrada à palavra
(palavras.json) e é convertida por M, e a voz toca de master-ritmo.mp4 uma única vez.

ritmo.json (opcional, na pasta do projeto; a linha de comando tem prioridade):
    {
      "velocidade": 1.1,
      "fim": 36.7,                       // ignora tudo depois (ex.: anotações lidas em voz alta no fim da gravação)
      "corrigir": {"Cláudio": "Claude"}, // nomes que a transcrição errou; não mexe nos tempos
      "remover": ["a@34.89"]             // palavras que a transcrição inventou: texto@segundo
    }
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[1]

p = argparse.ArgumentParser(description="Corta pausas e acelera a fala; o vídeo gravado fica intacto.")
p.add_argument("projeto", help='pasta do projeto, por exemplo "projetos/012. quanto-custa"')
p.add_argument("--velocidade", type=float, help="velocidade da fala (padrão 1.1 = 10%% mais rápida)")
p.add_argument("--min-corte", type=float, default=0.30, help="só corta silêncios de pelo menos esse tempo, em s (padrão 0.30)")
p.add_argument("--margem", type=float, default=0.09, help="sobra de cada lado de uma pausa cortada, em s (padrão 0.09)")
p.add_argument("--fim", type=float, help="ignora tudo depois desse segundo do vídeo gravado")
p.add_argument("--corrigir", action="append", default=[], metavar="ERRADO=CERTO", help="corrige um nome na legenda (repita à vontade)")
p.add_argument("--remover", action="append", default=[], metavar="TEXTO@SEGUNDO", help="remove uma palavra que a transcrição inventou")
p.add_argument("--slug", help="pasta em src/videos/ (padrão: nome do projeto sem o número)")
p.add_argument("--saida-video", help="grava o vídeo com ritmo neste arquivo em vez de <projeto>/video/master-ritmo.mp4")
p.add_argument("--saida-ts", help="grava ritmo.ts e dados.ts nesta pasta em vez de src/videos/<slug>")
p.add_argument("--sem-video", action="store_true", help="só calcula e grava os .ts, sem gerar o vídeo")
a = p.parse_args()

projeto = Path(a.projeto)
origem = projeto / "video" / "master.mp4"
destino = Path(a.saida_video) if a.saida_video else projeto / "video" / "master-ritmo.mp4"
if not origem.exists():
    sys.exit(f"Não achei {origem}")
cfg = json.loads((projeto / "ritmo.json").read_text(encoding="utf-8")) if (projeto / "ritmo.json").exists() else {}

VELOCIDADE = a.velocidade or cfg.get("velocidade", 1.1)
corrigir = dict(cfg.get("corrigir", {}))
for par in a.corrigir:
    errado, _, certo = par.partition("=")
    corrigir[errado] = certo
remover = list(cfg.get("remover", [])) + a.remover
slug = a.slug or re.sub(r"^\d+\.\s*", "", projeto.name)
saida_ts = Path(a.saida_ts) if a.saida_ts else RAIZ / "src" / "videos" / slug

duracao = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(origem)],
                               capture_output=True, text=True, check=True).stdout)
FIM = min(a.fim or cfg.get("fim") or duracao, duracao)

# 1) silêncios reais (silencedetect -30 dB, mínimo 0,2 s); os colados viram um só
log = subprocess.run(["ffmpeg", "-v", "info", "-i", str(origem), "-af", "silencedetect=noise=-30dB:d=0.2", "-vn", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
ini = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
fim_s = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
sil = []
for s0, s1 in zip(ini, fim_s):
    if sil and s0 - sil[-1][1] < 0.05:
        sil[-1][1] = s1
    else:
        sil.append([s0, s1])

# 2) início real de cada palavra: se a transcrição o marcou dentro de um silêncio, vale o fim do silêncio
palavras = json.loads((projeto / "transcricao" / "palavras.json").read_text(encoding="utf-8"))
tiradas = [(t.rpartition("@")[0], float(t.rpartition("@")[2])) for t in remover]
linhas = []
for w in palavras:
    s, e = w["s"], w["e"]
    texto = w["w"].strip()
    if s > FIM or any(texto == t and abs(s - seg) <= 0.06 for t, seg in tiradas):
        continue
    for x0, x1 in sil:
        if x0 - 0.05 <= s < x1 - 0.02 and x1 < e + 0.5:
            s = x1
    for errado, certo in corrigir.items():
        texto = texto.replace(errado, certo)
    linhas.append(f"  [{json.dumps(texto, ensure_ascii=False)}, {s:.2f}, {max(e, s + 0.1):.2f}],")

# 3) trechos mantidos
cortes = []
for x0, x1 in sil:
    if x1 - x0 < a.min_corte or x1 >= FIM - 0.3:
        continue
    cortes.append((0.0 if x0 < 0.05 else x0 + a.margem, x1 - a.margem))
trechos, cursor = [], 0.0
for c0, c1 in cortes:
    if c0 > cursor:
        trechos.append((cursor, c0))
    cursor = c1
trechos.append((cursor, FIM))

# 4) vídeo: corta (com fade de 12 ms nas emendas), junta e acelera
if not a.sem_video:
    partes, rotulos = [], []
    for i, (t0, t1) in enumerate(trechos):
        d = t1 - t0
        partes.append(f"[0:v]trim={t0}:{t1},setpts=PTS-STARTPTS[v{i}]")
        partes.append(f"[0:a]atrim={t0}:{t1},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={d - 0.012:.3f}:d=0.012[a{i}]")
        rotulos.append(f"[v{i}][a{i}]")
    partes.append(f"{''.join(rotulos)}concat=n={len(trechos)}:v=1:a=1[vc][ac]")
    partes.append(f"[vc]setpts=PTS/{VELOCIDADE},fps=30,format=yuv420p[vo]")
    partes.append(f"[ac]atempo={VELOCIDADE}[ao]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(origem), "-filter_complex", ";".join(partes), "-map", "[vo]", "-map", "[ao]",
                    "-c:v", "libx264", "-crf", "15", "-preset", "slow", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                    "-movflags", "+faststart", str(destino)], check=True)

# 5) arquivos para o Remotion
saida_ts.mkdir(parents=True, exist_ok=True)
(saida_ts / "ritmo.ts").write_text(
    "// Gerado por tools/ritmo.py: trechos mantidos do vídeo gravado (s) e a velocidade. Use com src/_shared/ritmo.ts.\n"
    f"export const VELOCIDADE = {VELOCIDADE};\n"
    f"export const TRECHOS: [number, number][] = {json.dumps([[round(t0, 3), round(t1, 3)] for t0, t1 in trechos])};\n",
    encoding="utf-8",
)
(saida_ts / "dados.ts").write_text(
    "// Gerado por tools/ritmo.py a partir de palavras.json (início corrigido, nomes corrigidos).\n"
    "export const PALAVRAS: [string, number, number][] = [\n" + "\n".join(linhas) + "\n];\n",
    encoding="utf-8",
)
total = sum(t1 - t0 for t0, t1 in trechos) / VELOCIDADE
print(f"{len(cortes)} pausas cortadas, {len(trechos)} trechos, nova duração {total:.2f} s ({round(total * 30) + 1} quadros a 30 fps)")
print(f"gravado em {saida_ts}" + ("" if a.sem_video else f" e {destino}"))
