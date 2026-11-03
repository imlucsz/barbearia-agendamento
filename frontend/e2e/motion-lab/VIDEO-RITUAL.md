# Ritual cinematográfico — estudo isolado

Escopo: somente `frontend/e2e/motion-lab/`. Intro, hero, CTA, `lab.css` e
`assets.mjs` aprovados preservados. Hashes de texto normalizados para LF em
`video-protected.json`; master sempre verificado em bytes. Nenhuma alteração na
HOME funcional, backend, API, autenticação, banco, dependências ou arquivos fora do Lab.

## Master e análise

- Original: `Barber_cutting_client's_hair_115145ff.mp4`, preservado no local recebido.
- 2.694.499 bytes; 1280×720, 16:9, H.264 High, 24 FPS, 240 frames.
- Vídeo: 10,000s; contêiner: 10,026667s; áudio AAC estéreo, 48kHz.
- Apenas um keyframe, em 0s: GOP de aproximadamente 240 frames, inadequado como
  distribuição principal para busca frequente/reversa.
- SHA-256: `8909ffa1632aa666c351a31d7efc2b7bc5637497315eb721e35f4c0041b3d0f6`.
- Frames de análise 0/20/40/60/80/100% em `artifacts/video-reference/`.
- Câmera fixa, espaço negativo à esquerda, barbeiro e cliente à direita. A mão
  encontra posição nos primeiros segundos; durante o corte surgem mechas; perto
  de 7,75–8s aparece o brilho, seguido pela acomodação/recuo do instrumento.

## Encoding

Na raiz do Lab (aspas duplas preservam o apóstrofo do nome original):

```powershell
ffmpeg -n -i "Barber_cutting_client's_hair_115145ff.mp4" -map 0:v:0 -an -c:v libvpx-vp9 -crf 30 -b:v 0 -g 6 -keyint_min 6 -lag-in-frames 0 -auto-alt-ref 0 -deadline good -cpu-used 2 -row-mt 1 -tile-columns 1 -threads 4 -pix_fmt yuv420p assets/ritual-scrub.webm
```

Reprodução segura, incluindo probe e poster: `python encode-ritual.py`.
O script usa `-n`, não sobrescreve o master nem cria outro MP4. Derivados existentes
não são recodificados silenciosamente. Comandos completos e medições de ffprobe
estão em `assets/ritual-media.json`.

- VP9 em qualidade constante: CRF30, bitrate-alvo zero (CQ), sem CBR artificial.
- Fonte estilizada, câmera fixa e áreas amplas de cor permitem qualidade alta nesse
  perfil. SSIM medido contra o master: 0,993678. Isso complementa a inspeção visual.
- Preservados 720p, 24 FPS e 16:9; nenhum upscale de encoding ou frame interpolado.
- GOP6: 40 keyframes, em intervalos de 250ms; reduz a dependência de frames anteriores.
- Sem alt-ref e lookahead para evitar camadas temporais desnecessárias ao scrub.
- Saída: 1.707.525 bytes; sem áudio. Aproximadamente 36,6% menor que o MP4 completo;
  essa comparação inclui a remoção de áudio e overhead, não apenas ganho de codec.
- Poster WebP de 7,9s: 27.016 bytes, 1280×720, qualidade85, extraído do mesmo master.

## Corte narrativo

| Trecho | Tempo | Motivo |
|---|---|---|
| PREPARO | 0–2,5s | Instrumentos e mãos encontram posição. |
| TÉCNICA | 2,5–7,75s | Corte visível, gesto repetido e mechas em movimento. |
| ACABAMENTO | 7,75–10s | Brilho, último gesto e resolução. |

Texto HTML independente. Mudanças de capítulo seguem o frame buscado/decodificado,
com transição editorial curta que termina mesmo se o visitante parar na fronteira.
Não há texto embutido no vídeo nem divisão arbitrária em três durações iguais.

## Arquitetura

`video-seek.mjs` possui fila event-driven que conserva somente o destino mais
recente. Metadata/duration reais, readyState, seeked e callbacks pontuais de frame
controlam a fila. Há no máximo uma busca em andamento; destinos intermediários são
coalescidos. O alvo é quantizado a 24 FPS e limitado ao último frame válido.

Sem autoplay, tween direto de currentTime, ticker adicional, Canvas ou WebGL no
Ritual. `requestVideoFrameCallback` é pontual; há fallback para seeked. Callbacks,
timers e listeners são cancelados no teardown; src é removido e load libera a mídia.

`ritual-video.mjs` coordena filme, máscara e capítulos. onRefresh sincroniza o
playhead restaurado em microtask: o ScrollTrigger renderiza temporariamente zero
durante refresh e pode restaurar progresso com callbacks suprimidos. A fila precisa
receber o estado final, especialmente quando metadata chega após a entrada.

O servidor local implementa MIME de vídeo, HEAD e HTTP Range/206/416 com streaming,
evitando reler/enviar o arquivo completo para cada busca. Isso é somente servidor
de desenvolvimento do laboratório, não uma alteração no backend.

## Apresentação

- Desktop: aproximadamente310vh (100vh de cena +210vh de percurso), um pin,
  scrub0,16s, scroll nativo, sem snap nem biblioteca de smooth-scroll.
- Composição revisada: um palco de100svh preenchido pelo filme. PREPARO começa com
  margem de2%; TÉCNICA reduz a margem a0,5%; ACABAMENTO abre até100vw ×100vh.
  O enquadramento muda pela máscara, com scale de apenas1,015→1. O filme mantém
  as cabeças, as mãos e a cadeira como protagonistas à direita.
- Todos os capítulos compartilham a mesma posição à esquerda, sobre o filme. A
  substituição editorial sobrepõe brevemente a saída e a entrada dos textos.
  Heading auxiliar, readout duplicado, porcentagem e link de comparação deixam de
  competir com a cena. Mantêm-se eyebrow, headline, supporting copy e rail discreto.
- Mobile: opçãoB, estados em 1,25/5,25/9,25s associados ao progresso. Cena em CSS
  sticky por185–190svh; sem pin do ScrollTrigger e sem busca por frame contínua.
  Prioriza legibilidade, reversibilidade e menor trabalho de decodificação. O filme
  ocupa o palco inteiro; em portrait, a imagem recebe enquadramento vertical e
  máscara suave no topo para fundir o espaço escuro com o texto sobreposto.
  Landscape usa imagem de altura inteira. Não há mais faixa horizontal separada
  de um bloco de conteúdo abaixo.
- Reduced-motion: poster e três textos em fluxo, sem src de vídeo, pin ou scrub.
- Sem GSAP/JS ou com erro de mídia: o HTML inicial já é estático. Poster mantém
  contexto, todos os textos permanecem em fluxo, sem corredor de scroll reservado.
- Mudança de breakpoint/preferência preserva a posição narrativa quando o visitante
  está na seção. O modo anterior continua em `?ritual=mirror`.

## Abrir e comparar

```powershell
npm --prefix frontend/e2e/motion-lab start
```

- Novo: http://127.0.0.1:4197/frontend/e2e/motion-lab/?nointro=1#ritual
- Antigo: http://127.0.0.1:4197/frontend/e2e/motion-lab/?ritual=mirror&nointro=1#ritual
- Lado a lado: http://127.0.0.1:4197/frontend/e2e/motion-lab/compare-ritual.html

## Validação e limites

```powershell
node frontend/e2e/motion-lab/video-checks.mjs
node frontend/e2e/motion-lab/checks.mjs
```

Relatório do vídeo e screenshots: `artifacts/video-validation/`. Regressão anterior:
`artifacts/legacy-video-round/`. Medições do HUD separam recursos alocados de ativos,
listeners próprios de internos GSAP e RAF compartilhado dos callbacks da biblioteca.
Tempos de seeked e callbacks de frame são diagnósticos distintos, não LCP/INP ou
garantia de desempenho em telefone físico. Chrome local e emulação mobile; teste
físico e Firefox/WebKit permanecem fora da evidência desta rodada.

## Evidência final desta rodada

- `node frontend/e2e/motion-lab/video-checks.mjs`: **18/18 aprovados**, Chrome.
- `node frontend/e2e/motion-lab/checks.mjs`: **17/17 aprovados**, regressão da base
  em modo espelho, sem reconstruir intro/hero/CTA. Total:35 checks de navegador.
- `python encode-ritual.py`: probe validou 240 frames/40 keyframes/sem áudio e
  preservação do SHA do master; reutilizou os derivados existentes sem recodificar.
- Primeira metadata no teste:23,8ms. Stress desktop: seeked mediana44,5ms/p9599,4ms;
  mobile emulado: mediana24,5ms/p9544,6ms. São tempos de conclusão da busca, não
  latência completa de input até a tela.
- Callbacks pontuais de frame no headless tiveram p95 de aproximadamente455–775ms
  em alguns cenários pausados. Não foram ocultados do relatório JSON nem usados
  como equivalentes à latência de seeked; medição de apresentação requer aparelho
  e compositor reais. Uma inspeção separada com callbacks de frames visíveis,
  seis saltos, encontrou o frame-alvo (±1frame) em95–156ms, incluindo scrub.
- Durante o Ritual: cinco triggers globais (um da cena), nenhum Canvas/WebGL ativo,
  zero RAF novo, 24 listeners próprios desktop/22 mobile. O decoder HTML de vídeo
  é separado desses contadores. Offscreen não emite novas buscas; buffer pode
  permanecer carregado. Teardown: listeners/triggers/callbacks de frame zerados,
  src removido e nenhum RAF pendente.
- Comparação executada lado a lado com o espelho: vídeo VP9 decodificado em5,25s,
  câmera fixa e ação reconhecível. Screenshot `artifacts/video-validation/comparison.png`.
  O novo comunica o serviço e o gesto com mais clareza e profundidade; o espelho
  continua mais leve. Recomendação: adotar o novo conceito em futura integração,
  após aprovação visual e validação de dispositivos; nenhuma integração executada.
- Correções verificadas: sincronização pós-refresh/metadata, scroll cache e
  ancoragem após resize/preferência, texto legível ao parar em transição, layout
  estático em falha de GSAP/sem JS e fallback de erro no meio do Ritual. Revisão
  independente encontrou o problema de fallback estático, agora coberto por teste.
- Nenhum backend/banco/API, commit, staging, push ou deploy. Documentação atualizada
  somente neste Lab; o grafo foi consultado sem escrita fora do escopo autorizado.

Referências técnicas consultadas: [FFmpeg/libvpx](https://ffmpeg.org/ffmpeg-codecs.html#libvpx),
[HTMLMediaElement.currentTime](https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/currentTime)
e [requestVideoFrameCallback](https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/requestVideoFrameCallback).

## Evidência da revisão de composição

- Alterações desta rodada: apenas `ritual-video.css`, apresentação das máscaras e
  textos em `ritual-video.mjs` e este documento. O seeker, configuração de scrub,
  pontos narrativos, WebM, master, HTML, intro, hero e CTA permanecem preservados.
- `node frontend/e2e/motion-lab/video-checks.mjs`:18/18 na execução final.
  Uma execução anterior, durante capturas paralelas, encontrou1 RAF agendado no
  teardown aos250ms. Não se reproduziu no teste isolado (0 RAF/listeners/triggers
  entre100ms e1050ms) nem na execução final. Observação mantida como variação de
  timing do harness; não foi alterada a engenharia para mascarar o contador.
- Inspeção de100svh, limites do texto e overflow em320×568,390×844,768×1024,
  820×1180,844×390,1000×1400,1440×640 e1920×1080. Mantém-se o modo segmentado
  existente para alturas menores que650px. Mobile é emulado, sem teste em aparelho.
- Capturas dos cinco momentos desktop, mobile, tablet e comparação com Temaki em
  `artifacts/ritual-composition/`. As duas transições foram capturadas com apenas
  a timeline editorial mantida em160ms para mostrar sua máscara intermediária;
  essa pausa é da captura, não do comportamento normal da página.
- `artifacts/ritual-composition/report.json`: geometria, mídia e estados capturados.
  `artifacts/video-validation/report.json`: regressão final. Hashes confirmam os
  arquivos protegidos intactos. Nenhuma dependência nova e nenhuma recodificação.
