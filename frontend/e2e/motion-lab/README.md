# Precisão que transforma — laboratório visual

## Rodada atual: Ritual em vídeo

O Ritual principal agora usa o master fornecido pelo usuário, com WebM VP9/GOP curto,
scroll-scrub desktop, estados leves no mobile e poster em reduced-motion. Intro,
hero e CTA aprovados permanecem preservados. [Relatório, encoding e limites](VIDEO-RITUAL.md).
O estudo anterior não foi apagado: [comparar espelho × vídeo](http://127.0.0.1:4197/frontend/e2e/motion-lab/compare-ritual.html).
Validação específica: `node frontend/e2e/motion-lab/video-checks.mjs` na raiz.

O restante deste documento registra a base visual anterior; o espelho descrito
abaixo continua disponível em `?ritual=mirror`, sem substituir a nova cena principal.

Prova visual isolada da fase 1. Nenhum catálogo, autenticação, API ou banco é
carregado pelo laboratório. Os links Agendar mantêm o destino existente da HOME;
os testes não os seguem. `frontend/pages/index.html` não foi integrado nem editado.
A pasta `e2e` já é excluída pelo build estático. Para remover o estudo, remova apenas
esta pasta e suas duas referências na documentação; não há dependências novas na raiz.

## Abrir

Na raiz do projeto:

```powershell
npm --prefix frontend/e2e/motion-lab ci --ignore-scripts
npm --prefix frontend/e2e/motion-lab start
```

- Laboratório: http://127.0.0.1:4197/frontend/e2e/motion-lab/
- Comparação executável: http://127.0.0.1:4197/frontend/e2e/motion-lab/compare.html
- A referência é o arquivo original `Temaki House Corte.html` da raiz, servido em
  `/reference`. O servidor escuta somente em 127.0.0.1 e não serve backend ou dados.
- GSAP 3.15.0 e Three.js 0.187.0 são dependências locais, fixadas no lockfile deste
  estudo e resolvidas por import map. Não há CDN, imagens externas ou fontes remotas.

## Experimentar

- **Rever intro:** reinicia a cena de 3,5s (2,3s mobile).
- **Pular / Escape / Tab:** encerra no mesmo estado final. Rolagem e toque também
  liberam a navegação; nenhuma captura de foco ou smooth-scroll artificial.
- Conclusão e skip ficam registrados na aba por sessionStorage. Replay ignora essa
  memória. `?nointro=1` abre direto no hero.
- **Pausar ambiente:** suspende Canvas, rotação dos poles e intro automática; mantém
  o Ritual controlado pelo scroll do visitante.
- **Ritual:** um único palco e pin desktop, scrub .55, progressão reversível. Mobile
  usa o mesmo espelho em fluxo, transformado durante sua passagem pela tela, seguido
  pelos três textos sem sobreposição. Reduced-motion não usa pin/scrub/parallax.
- **Métricas:** mostra os consumidores, recursos e uma ação de desmontagem completa.
- **Lado a lado:** cada experiência tem scroll independente. Uma janela larga
  permite observar ambas no breakpoint desktop; telas menores empilham os painéis.
- `?no3d=1` força o fallback SVG da comparação sem afetar as demais cenas.

## Gesto e materiais

Tesoura original em SVG: duas metades giram em torno do mesmo pivô, com lâminas,
anéis vazados, parafuso, contrafios e reflexo móvel. O fechamento causa o brilho,
a reação determinística das partículas e a abertura dos painéis. Os mesmos nós da
tesoura e do pole assentam no hero, em vez de desaparecerem e serem recriados.

Canvas 2D usa 62 partículas desktop/23 mobile, movimento ambiente lento e reação
curta de impacto; sem confete. O ponto de emissão é obtido da lâmina transformada.
O pool continua no hero e sua renderização para quando sai da tela.

O espelho usa moldura com gradientes materiais, vidro em camadas, silhueta gráfica
original, névoa/obscurecimento, reflexo móvel, guias que convergem e contorno final.
Nenhuma foto ou pessoa real/fictícia foi usada como prova de resultado.

Pole A: SVG com helicoides e reflexos preparados. Pole B: cilindro, fitas helicoidais
procedurais, terminais, materiais PBR e ambiente de estúdio procedural. Three é
carregado somente perto da comparação. Falhas, inclusive perda de contexto, revelam
o SVG; retry cria um canvas novo. A recomendação inicial é integrar A: B não mostrou
superioridade visual suficiente para justificar o custo adicional nesta direção.

img2threejs foi avaliado e dispensado para o pole genérico; modelagem procedural
simples atende ao objeto. As skills GSAP, LottieFiles e UI UX Pro Max orientaram
timeline, causalidade, hierarquia, adaptação e controle do scroll.

## Timeline desktop

| Tempo | Ação |
|---|---|
| 0–180ms | Escuridão; hero montado atrás. |
| 120–620ms | Feixe quente revela atmosfera. |
| 380–1000ms | Marca ganha presença. |
| 760–1300ms | Pole e tesoura emergem. |
| 1060–1520ms | Antecipação e fechamento articulado. |
| 1490–1800ms | Reflexo e poeira respondem. |
| 1660–2580ms | Painéis se abrem em etapas sobre o hero. |
| 2040–2920ms | Headline por linhas e composição editorial. |
| 2460–3300ms | Mesmos elementos encontram posição no hero. |
| 2940–3500ms | Acomodação e transferência completa. |

## Validação

```powershell
node frontend/e2e/motion-lab/checks.mjs
node --test "frontend/tests/*.test.mjs"
```

O runner usa o Playwright já instalado na raiz e Google Chrome local. Cria servidor
efêmero, não usa backend/banco e salva screenshots e relatório em `artifacts/`
(ignorado pelo Git). Cobre os fluxos, viewports 320/390/768/820/1000/1440,
reduced-motion inicial/em sessão, falhas de imports, inicialização parcial Three,
perda/recuperação de contexto e teardown. Falhas de rede induzidas são avaliadas
em contextos separados do check de console limpo da navegação normal.

## Como ler as métricas

- **RAF lab:** no máximo um consumidor do ticker GSAP, compartilhado por Canvas,
  faixas SVG e Three. Não há RAF próprio por componente.
- **RAF totais:** solicitações realmente pendentes, instrumentadas antes dos imports.
  Incluem o ticker `_tick` e o RAF interno `_rafBugFix` do ScrollTrigger; não confundir
  consumidores do laboratório com loops internos da biblioteca.
- **Canvas ativos:** renderização ativa, separada do número de contextos alocados.
  Fora da tela não há renderização; recursos GPU são liberados na desmontagem.
- **Listeners:** apenas registros gerenciados pelo laboratório, sem alegar contar
  listeners internos do navegador/GSAP.
- **Partículas pool:** limite de partículas, não uma contagem de pixels visíveis.
- **Subrecursos raw:** soma de decodedBodySize dos subrecursos locais observados,
  sem HTML principal e sem gzip; este servidor de estudo usa no-store, sem compressão.
- **Desmontar:** remove triggers, ticker compartilhado, observers, listeners próprios,
  renderers/geometrias/materiais, contexto WebGL e timers. Mantém leitura e links.

Não é bundle de produção nem benchmark de dispositivo físico. Nesta prova, os
módulos de desenvolvimento são servidos diretamente; a otimização de distribuição
pertence à fase posterior, se a direção visual for aceita.
