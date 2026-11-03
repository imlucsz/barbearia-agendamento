# Ritual: diagnóstico Chrome / Edge — 2026-11-02

Atualização de produto — 2026-11-03: o usuário confirmou manualmente a causa
responsiva (zoom/viewport restauram o scrub). A decisão posterior remove os três
stills em **todas** as viewports; somente reduced-motion seleciona apresentação
estática. O relatório abaixo preserva o diagnóstico anterior e suas hipóteses,
incluindo a proposta histórica de preservar stills no mobile, agora superada.
Implementação e evidências atuais: [integração HOME](HOME_MOTION_INTEGRATION.md#ritual-contínuo-universal--2026-11-03).

Etapa exclusivamente diagnóstica. Nenhuma correção na HOME, mudança visual,
recodificação, alteração da Estrelinha, banco ou publicação.

## Conclusão e limite

**Principal suspeita: seleção do modo responsivo segmentado por altura/largura
CSS da viewport.** A reprodução automatizada demonstra exatamente três tempos
de vídeo quando a altura é 640px, nos dois navegadores. Com 1440×900, os dois
apresentam centenas de frames durante o percurso. Confiança alta no mecanismo;
moderada em explicar a sessão manual relatada, cuja viewport/modo ainda faltam.
Não foi reproduzida uma falha exclusiva do Edge com viewport igual.

Zoom, DevTools acoplado, barras e tamanho da janela podem mudar a viewport CSS;
mesma máquina/página/interação não prova que a media query foi igual. Esses
fatores são possibilidades a verificar, não fatos observados na sessão manual.

Plano executado: consultar Graphify e contratos → rastrear fila → medir asset
real → comparar canais instalados com percurso igual → fornecer coleta manual.

## Fluxo exato e arquivos

1. `frontend/pages/index.html`: `#ritual-video`, poster, capítulos HTML, entrada
   `frontend/assets/js/home-experience.mjs`.
2. `home-experience.mjs`, `start()` / `gsap.matchMedia()`: desktop somente com
   `(min-width:1000px) and (min-height:650px)`; reduced-motion tem prioridade.
   `createVideoRitual()` vem de `home-motion/ritual-video.mjs`.
3. `createVideoRitual()`: ScrollTrigger controla uma timeline pausada de 10s.
   Desktop: pin, início `top top`, percurso `innerHeight * 2.1`, `scrub:.16`.
   Modo segmentado: `top top` até `bottom bottom`, `scrub:true`, sem pin GSAP.
4. `synchronize()` recebe `timeline.progress()` em `onUpdate` e após refresh
   (microtask). Desktop envia progresso contínuo a `seeker.seekProgress()`.
   Segmentado converte progresso×duração em **1.25 / 5.25 / 9.25 segundos**,
   usando os cortes narrativos existentes 2.5 e 7.75s. Não é snapping do codec.
5. `home-motion/video-seek.mjs`, `progressToTime()`: clamp de progresso em [0,1],
   arredondamento a 24 FPS; limite superior `duration - 1/24` = 9.958333s.
6. `seekProgress()` guarda somente o destino mais recente; `pump()` calcula
   `desiredTime`. Exige anexo, visibilidade, documento ativo, metadata/duração.
   Com `inFlight || video.seeking`, coalesce e retorna, sem escrever currentTime.
   Se diferença menor que meio frame e readyState≥2, publica currentTime.
7. O único write de `currentTime` neste seeker fica em `pump()`. Antes dele,
   marca inFlight, registra início/contador e agenda callback pontual rVFC.
   Frequência depende dos alvos quantizados e conclusão de seeks, sem taxa fixa.
8. Browser busca/decodifica e emite `seeked`; handler libera inFlight, registra
   latência e imediatamente chama `pump()` para o último destino pendente.
   rVFC publica `metadata.mediaTime` via `onFrame()` → `readTime()` → capítulo.

Não existe `quickTo`, tween direto de currentTime, RAF/ticker próprio do seeker,
debounce de seek ou autoplay. Há ticker/RAF do GSAP, smoothing desktop de .16s,
fila de último alvo, eventos loadedmetadata/durationchange/loadeddata/seeked/error,
IntersectionObservers de preparação (500px) e visibilidade. Refresh global é
debounced em 120ms por ResizeObserver de seções dinâmicas/fontes/metadata.

Cleanup: observers desconectados, trigger/timelines mortos; seeker invalida geração,
cancela rVFC e timers, remove listeners, pausa, remove src e chama load().
Visibilitychange cancela rVFC ao ocultar e tenta pump ao retornar.

### Atribuição de currentTime não comprova apresentação

O caminho principal tenta observar rVFC, mas **há atalhos que publicam currentTime**:
destino já próximo, loadeddata, timeout de 120ms após seeked com rVFC e watchdog
de 1500ms se seeking já terminou. Sem rVFC, seeked publica diretamente.
Portanto `snapshot().presentedTime` e capítulos não comprovam frame apresentado.
Além disso, um novo pump cancela o callback anterior; seeks podem terminar antes
da notificação do compositor. Isso é uma fragilidade de telemetria/sincronização,
sem evidência de explicar três estados exclusivos no Edge.

rVFC observa envio de frame ao compositor, não prova leitura física do monitor.
`presentedFrames` detecta frames sem callback observado, que não equivalem a
frames descartados. Dropped frames são medidos separadamente por playback quality.
Referência: https://wicg.github.io/video-rvfc/

## Asset real (ffprobe, sem recodificação)

`frontend/assets/media/home/ritual-scrub.webm`, resolvido pelo import da HOME;
não o MP4 original nem o asset homônimo do laboratório.

| Propriedade | Medida |
|---|---|
| Container / streams | WebM (matroska,webm), um vídeo, sem áudio |
| Codec | VP9 Profile 0, vp09.00.31.08, yuv420p, progressivo |
| Resolução / proporção | 1280×720 / 16:9 |
| Duração / FPS / frames | 10s / 24/1 / 240 |
| Bytes / bitrate do container | 1.707.525 / 1.366.020 bit/s (~1.366 Mbit/s) |
| Bitrate isolado do stream | Não informado pelo ffprobe |
| GOP / keyframes | 6 frames; 40 keyframes |
| Distribuição | 0, 0.25, 0.50, …, 9.75s; todos intervalos de 250ms |
| B frames declarados | 0 |

Comandos: `ffprobe -v error -show_format -show_streams -of json <asset>` e
`ffprobe -v error -select_streams v:0 -show_frames -show_entries frame=pts_time,key_frame -of json <asset>`.
A contagem usa todos os frames e filtra key_frame=1; skip_frame não foi usado
como garantia de filtragem, pois o decoder retornou também frames não-chave.

## Reprodução e evidência

`rtk proxy node frontend/e2e/ritual-diagnostics.mjs` executou a HOME real,
servidor estático local com Range, API fictícia interceptada, perfis temporários,
headless com canais instalados **Chrome 156.0.8078.48 / Edge 156.0.4314.58**.
Sem flags de desativação de GPU. Não muda configuração/perfil pessoal.
Percurso: 121 posições em cada direção, intervalo nominal 33ms, com mesmo
viewport por par. GSAP ainda pode emitir mais atualizações pelo smoothing.

| Canal / viewport CSS | Modo | Writes / seeking / seeked | Writes durante seeking | Callbacks rVFC | Tempos distintos rVFC | Dropped |
|---|---|---|---|---|---|---|
| Chrome 1440×900 | continuous-scrub | 354 / 354 / 354 | 0 | 347 | 144 | 0 |
| Edge 1440×900 | continuous-scrub | 369 / 369 / 369 | 0 | 364 | 157 | 0 |
| Chrome 1440×640 | segmented | 5 / 5 / 5 | 0 | 5 | 3 | 0 |
| Edge 1440×640 | segmented | 5 / 5 / 5 | 0 | 5 | 3 | 0 |

Cinco seeks no segmentado correspondem à ida/volta pelos mesmos três estados.
Não se deve dividir os totais de frames de playback quality por seeks para
estimar apresentação: a decodificação de dependências também faz trabalho.

Desktop: seek p95 Chrome 13.5ms / Edge 13ms; p95 do callback interno 17.5/17.7ms.
Esses últimos dados são amostragem interna, afetada pelo cancelamento acima.
O observador externo registrou 5/3 frames enviados ao compositor sem callback
intermediário observado em Chrome/Edge desktop; isso não é dropped frames.
Sem waiting/stalled na coleta; buffer final [0,10], readyState final 4; writes
observados com readyState 1 ou 4. Nenhum pageerror.

CDP Media: ambos **D3D11VideoDecoder**, platform decoder true, Intel Iris Xe,
driver 32.0.101.7088; GPU video_decode/compositing enabled. Não se executou A/B
desativando aceleração: não há falha específica reproduzida que justifique isso.
Perf no percurso desktop: 12 layouts em cada browser, duração agregada
5.428ms Chrome / 4.586ms Edge; style recalc agregado 136.908/185.668ms.
O observador de toda a sessão contou 5 long animation frames em cada desktop,
zero longtasks; forced style/layout agregado desses eventos 27.9/21.8ms.
Os dois intervalos de medição diferem (sessão vs percurso); não somar métricas.
Há trabalho de layout, mas não evidência de bloqueio sustentado explicando os
três saltos. Atribuição fina exigiria Performance trace da sessão que falha.

JSON detalhado: `test-results/ritual-diagnostics.json` (gerado, ignorado pelo Git).
Headless/perfil limpo não valida visualmente o perfil normal nem aparelho físico.

## Hipóteses

| Hipótese | Resultado / limite |
|---|---|
| H1 seeks acumulados | Refutada nas quatro execuções: guarda explícita e zero writes enquanto seeking. Alvos são coalescidos, não enfileirados todos. |
| H2 GOP inadequado | GOP longo eliminado: medidos 6 frames/250ms. Sensibilidade específica de decoder/perfil ainda possível, sem evidência favorável local. |
| H3 apresentação irregular | Não explica a execução Edge desktop observada. Continua aberta para sessão manual com modo contínuo confirmado. rVFC e dropped são distintos. |
| H4 loop mais rápido que pipeline | Há múltiplos alvos/coalescência; nenhuma fila crescente de seeks nem RAF próprio. Não explica exatamente três tempos em modo segmentado. Stress de outra velocidade ainda aberto. |
| H5 buffering | Sem evidência no servidor local; buffer completo e sem waiting/stalled. Servidor/cache/rede da sessão manual ainda não inspecionados. |
| H6 GPU | Ambos usaram mesmo decoder e aceleração com bom resultado local. Perfil/configuração normal continuam abertos; não eliminada universalmente. |
| Modo responsivo | Reprodução exata dos três tempos em ambos com altura<650; principal hipótese para a diferença manual. Confirmar mode/viewport no Edge afetado. |

## Menor experimento manual (primeiro, sem instrumentação)

Na HOME afetada, Console: copie o resultado desta expressão nos dois browsers:

```js
JSON.stringify({viewport:[innerWidth,innerHeight],dpr:devicePixelRatio,desktop:matchMedia('(min-width:1000px) and (min-height:650px)').matches,video:window.homeExperience?.snapshot().ritualVideo})
```

Depois: maximize, zoom 100%, feche DevTools e role novamente. Recolha o resultado
com DevTools desacoplado para não mudar a viewport. Devolva **os dois JSONs e
se os três saltos persistem após maximizar**. Se Edge reportar segmented e os
saltos sumirem com continuous-scrub, confirma a seleção de modo como causa.
Se já estava continuous-scrub enquanto falha, essa hipótese não explica a sessão.

### Coleta completa somente se ainda falhar em continuous-scrub

1. DevTools desacoplado → Sources → Snippets: cole e execute o conteúdo de
   `frontend/e2e/ritual-diagnostics.js`.
2. Role o Ritual até o fim e volte uma vez (~10s).
3. Console: `copy(JSON.stringify(ritualDiagnostics.stop()))`. Devolva esse JSON.

O snippet não faz fetch, storage, log por frame nem alteração visual; intercepta
apenas o setter da instância para contar writes, delegando ao setter nativo.
Mantém no máximo 20.000 linhas; informa truncamento. stop restaura descriptor,
cancela callback/timer, remove listeners e desconecta observers; reload também
remove tudo. Instrumentação adiciona overhead; comparar sessões com ela igual.
Não é importado pela HOME nem ativado por query pública.

Se houver falha contínua com muitos seeked e poucos frames: devolver também
somente kVideoDecoderName/kIsPlatformVideoDecoder de `edge://media-internals`
e estado Video Decode de `edge://gpu`; não precisa exportar logs de outras abas.
Referência Microsoft: https://learn.microsoft.com/en-us/troubleshoot/microsoft-edge/development/video-playback-issues
Próximo experimento então: repetir mesmo percurso/viewport com aceleração on/off
e restart, mantendo todas as outras variáveis. Não foi executado nesta etapa.

## Proposta condicionada, NÃO implementada

Se confirmado o breakpoint: separar decisão de layout compacto da decisão de
scrub contínuo, de modo que uma janela desktop curta não receba silenciosamente
a experiência de três stills. Manter a política mobile e coordenadas/cortes.
É uma mudança pequena de seleção de modo, mas exige validar pin/layout em janela
baixa antes de escolher a expressão final; não basta retirar altura cegamente.

Se continuous-scrub falhar: decidir pela evidência. Só experimentar backpressure
até apresentação se seeks concluírem mas frames não acompanharem; só comparar
encoding se latência do decoder apontar para o asset. Nenhum fallback por UA.

| Plataforma | Impacto esperado da proposta de seleção de modo |
|---|---|
| Chrome / Edge | Janela desktop curta deixa de usar stills; desktop alto preserva scrub. Validar altura/zoom e resize. |
| Firefox / Safari | Mesma regra responsiva, sem branch por UA; compatibilidade/performance precisam ser testadas, não medidas nesta rodada. |
| Mobile | Preservar os três estados existentes, sem aumento de decodificação por intenção. Teste físico pendente. |
| prefers-reduced-motion | Preservar poster, textos completos e vídeo sem src, sem scrub/pin. |

## Validação e arquivos

- Dois novos arquivos de debug: `frontend/e2e/ritual-diagnostics.js` e `.mjs`.
- Este relatório e registro de evidência em `docs/REQUISITOS_STATUS.md`.
- `node --check frontend/e2e/ritual-diagnostics.js`: passou.
- Probe Node: quatro cenários Chrome/Edge concluídos; verificações Python do
  JSON confirmaram 4 registros, zero writes durante seeking e 3 tempos no modo
  segmentado. ffprobe confirmou 240 frames e distribuição dos 40 keyframes.
- Playwright HOME: `--project=desktop --grep "scrub|movimento reduzido"`: 2/2;
  mesmo comando com `--project=mobile`: 2/2.
- Testes Python de aplicação/SQLite/PostgreSQL: não executados; nenhum backend
  ou banco foi necessário, iniciado ou alterado. Não se executou Lab completo.
- Pendência: JSON da sessão manual afetada; confirmar causa antes da correção.
- `graphify update .`: concluído, AST local, sem LLM; atualizou artefatos em
  `graphify-out/` (11.363 nós / 23.285 arestas).
- `git diff --check`: código 0; avisos de normalização LF/CRLF em documentação.
