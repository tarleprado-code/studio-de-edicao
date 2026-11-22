// Converte tempos do vídeo GRAVADO (os de palavras.json) para o tempo do vídeo com o ritmo aplicado
// (pausas cortadas e fala acelerada por tools/ritmo.py).
//
// Uso numa composição:
//   import {TRECHOS, VELOCIDADE} from './ritmo';           // gerado por tools/ritmo.py
//   import {criarRitmo} from '../../_shared/ritmo';
//   const {M, CORTES_NOVOS, DURACAO_FRAMES} = criarRitmo(TRECHOS, VELOCIDADE);
//   // M(10.4) = em que segundo do vídeo final cai o que foi dito em 10,4 s da gravação
//   // CORTES_NOVOS = segundos do vídeo final onde há uma emenda (bom lugar para um zoom que esconde o corte)
export const criarRitmo = (trechos: [number, number][], velocidade: number, fps = 30) => {
  let acc = 0;
  const INICIO_NOVO = trechos.map(([a, b]) => {
    const s = acc;
    acc += (b - a) / velocidade;
    return s;
  });
  const M = (x: number) => {
    for (let i = 0; i < trechos.length; i++) {
      const [a, b] = trechos[i];
      if (x < a) return INICIO_NOVO[i];
      if (x <= b) return INICIO_NOVO[i] + (x - a) / velocidade;
    }
    const u = trechos.length - 1;
    return INICIO_NOVO[u] + (trechos[u][1] - trechos[u][0]) / velocidade;
  };
  return {
    M,
    INICIO_NOVO,
    CORTES_NOVOS: INICIO_NOVO.slice(1),
    DURACAO_S: acc,
    DURACAO_FRAMES: Math.round(acc * fps) + 1,
  };
};
