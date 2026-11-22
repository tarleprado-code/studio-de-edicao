# 6. Lições de produção

O que aprendemos editando vídeos de verdade (aula, venda de serviço, imóvel, clientes). São **hábitos de produção**: o que fazer antes de gravar, como não se perder no meio e o que nunca deixar passar. A direção visual (cenas, transições) está em [5-direcao-editorial.md](5-direcao-editorial.md).

---

## 1. Antes de gravar

- **Roteiro por blocos, com pausa de 2 segundos entre eles.** A pessoa lê um bloco, fecha a boca, olha para a câmera e segue. As pausas viram os pontos de corte do ritmo e das trocas de cena.
- **Celular na vertical, parado, na altura dos olhos**, do peito para cima, com o mesmo enquadramento do começo ao fim. Camiseta lisa e fundo simples ajudam o recorte e a IA.
- **Anotações não vão no roteiro lido.** Se a pessoa ler em voz alta as instruções ("pode trocar os números…"), isso entra na transcrição. Dá para cortar com `"fim"` no `ritmo.json`, mas é melhor combinar: *lê só o que está entre aspas*.
- **Sem texto dentro de imagem gerada por IA**, nem logos, nem placas. Todo texto entra na montagem, onde dá para corrigir.

## 2. Os 3 primeiros segundos: título-gancho

Todo vídeo abre com um **título na tela de 0 a 3 s**, para a pessoa entender do que se trata e sentir **curiosidade leve**.

- No máximo uns **8 palavras**, grande, no topo (fora da zona do rosto); entra em ~0,2 s e sai por volta de 3 s.
- Promessa de benefício + um pouco de curiosidade (pergunta ou número), **sem entregar tudo**. Exemplos: *"O que dá pra ter por R$ 410 mil em Uberaba?"*, *"Quanto custaria esse vídeo numa agência?"*.
- **A fala confirma o título**, não o repete palavra por palavra. Nada de promessa que o vídeo não cumpre.
- Todo `plano.md` tem a linha **"Título dos 3 primeiros segundos"**, com 2 ou 3 opções quando não for óbvio.

## 3. Ritmo e sincronia

- **Cortar pausas e acelerar 10%** é opcional e só a pedido da pessoa: `python tools/ritmo.py "projetos/NNN. slug"` (veja o [guia 2](2-nivel-1-remotion.md#ritmo-cortar-pausas-e-acelerar-a-fala-opcional)). O original nunca é alterado.
- **Todo gatilho vem de `palavras.json`**, convertido por `M()` (de `src/_shared/ritmo.ts`). Conteúdo nunca aparece antes de ser dito.
- **A voz toca uma única vez**, de `master-ritmo.mp4`. Nunca some outra cópia do vídeo ao áudio.
- Cada emenda do corte é um pulo na imagem: alterne um leve zoom (1,00 / 1,05) para esconder.
- **Legenda palavra por palavra**, com as palavras-chave em destaque. Valores como "R$ 890 mil" ficam juntos na legenda (a transcrição separa em "R", "$", "890", "mil").

## 4. Trocar roupa e cenário

Duas formas, da mais simples para a mais avançada.

### 4.1 Recorte + cenário (gratuito)

`python tools/recorte_rvm.py "<vídeo>" "<recorte.mov>"` tira o fundo (saída com transparência). Por baixo vai uma foto ou vídeo de cenário (por exemplo, do Pexels, que é gratuito para uso comercial). Veja o [guia 2](2-nivel-1-remotion.md) para o uso no Remotion.

### 4.2 Roupa e cenário por IA (Nível 2, Higgsfield, Seedance video_edit)

1. **Corte a gravação em trechos nas pausas**, de uns 3 a 12 segundos. Trechos curtos dão menos chance de a IA se perder e deixam refazer só um deles.
2. **Use o mesmo prompt em todos os trechos** (mesma roupa, mesma sala), para o visual não mudar de um para o outro. O prompt padrão pede para manter rosto, boca, olhar, gestos e o tempo, quadro a quadro, mudando **só** roupa e fundo. Sem áudio na saída.
3. **Ajuste cada trecho que voltou:** `python tools/ajustar_ia.py <enviado.mp4> <da IA.mp4> <saida.mp4>`. A IA devolve duração diferente (um trecho de 2,5 s voltou com 4 s, em câmera lenta). Sem esse ajuste a boca fica atrasada em relação à voz; a ferramenta corrige e mede a sincronia (acima de 0,85 está bom).
4. **Monte uma versão "com a IA" do vídeo inteiro** do mesmo tamanho do original (os trechos da IA no lugar certo, o resto do original) e aplique o mesmo ritmo nela. As duas versões ficam alinhadas e a composição escolhe qual mostrar a cada momento.
5. **Se a IA inventou emblema, logo ou texto na roupa**, refaça com um prompt que peça tecido liso, sem patches, bandeiras, logos nem texto, ou aproxime a imagem (`--zoom`) até deixar o emblema fora do quadro. Nunca publique com marca de terceiros à mostra.

**Higgsfield pelo Claude Code ou pelo Cowork.** As gerações *ilimitadas* de um teste ou plano só funcionam no Cowork ou no chat do Claude, não na sessão Code, que só usa créditos avulsos. O caminho que funcionou: envie os trechos daqui (`media_upload`), passe os códigos (`media_id`) para o Cowork gerar, e baixe os resultados daqui com os `job_id`.

## 5. Vídeos de imóvel (corretor)

- **Só use um imóvel real com autorização** do corretor ou do dono. Fotos reais chegam melhor se a corretora mandar **como "documento"** no WhatsApp (como foto, o WhatsApp diminui a qualidade).
- **Cenas geradas por IA** levam o selo **"Imagem ilustrativa · gerada por IA"** e, em anúncio, o **número do CRECI** do corretor. Nos vídeos de exemplo vai "CRECI 00000 · exemplo".
- **Sala vazia que vira mobiliada** (virtual staging) é ótima para mostrar o serviço, **sempre avisando** que a mobília é ilustrativa.
- Dados do imóvel (preço, metragem, quartos, vagas, condomínio) vêm **só do anúncio**. Nada inventado.
- O mapa do bairro ("5 min até o metrô") é uma ilustração: não prometa tempos que o corretor não confirmou.

## 6. Cuidados com IA e com clientes

- **Avise que é IA.** Selo discreto "Gerado com IA" nas cenas geradas. Em saúde e em profissões regulamentadas, **selo de simulação** ("Simulação · fulano não é dentista") em cada trecho.
- **Nunca invente depoimento, antes e depois ou resultado de cliente.**
- **Autorização por escrito** para reeditar e repostar o vídeo de um cliente. Imagem de cliente não entra em repositório público, galeria ou portfólio sem permissão.
- **Segredos** (chaves, tokens) ficam em variáveis de ambiente, nunca em arquivos do repositório nem na conversa.
- **Créditos e imagens de terceiros:** mapas do Google Earth Studio levam o crédito visível; imagens do Pexels são gratuitas, mas confira a licença de cada uma; quadros de canais de outras pessoas não são seus.

## 7. Entrega

- **Stills de revisão antes do render final** (início, meio e fim de cada mudança de cena), e uma **prévia** antes do final.
- **Final** com `crf` 17 e volume normalizado para **−14 LUFS** (veja o [guia 5](5-direcao-editorial.md), seção de som). Duração igual à do vídeo com ritmo.
- Se a prévia parecer **sem som**, abra no player do sistema: alguns visualizadores embutidos abrem no mudo.

## 8. Problemas comuns

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| A legenda traz palavras de anotações no fim | A pessoa leu as instruções em voz alta | `"fim"` no `ritmo.json`, ou regravar |
| Nome errado na legenda ("Cláudio") | Erro da transcrição | `"corrigir"` no `ritmo.json` (não mexe nos tempos) |
| A boca fica atrasada no trecho da IA | A IA mudou a duração | `tools/ajustar_ia.py` |
| Logo ou emblema na roupa gerada | A IA decorou o traje | Refazer com "tecido liso" ou `--zoom` |
| Algo cobre o rosto num card | Zona do rosto medida num quadro só | Medir 1 quadro por segundo do vídeo inteiro ([guia 2](2-nivel-1-remotion.md)) |
| Borda do recorte tremendo | Modelo rápido demais para o caso | `--modelo resnet` no `recorte_rvm.py` |
| Skill `watch` não aparece | Sessão antiga | Abra uma sessão **nova** na pasta do Studio |
