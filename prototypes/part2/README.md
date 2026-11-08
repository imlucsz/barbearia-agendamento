# Parte 2 — protótipos para aprovação visual

Três homepages isoladas, sem integração à API. **Parar aqui e escolher a direção antes do redesign definitivo.**

**Nova variação solicitada:** [A híbrida — identidade tradicional + Entrelinhas](a-hybrid.html), com o Ritual original e Estrelinha. [Decisões, screenshots e validação](HYBRID.md). As três direções anteriores permanecem intactas.

- [Galeria comparativa](index.html)
- [A — Entrelinhas](a-editorial.html): editorial contemporâneo; recomendada.
- [B — Intervalo](b-minimal.html): minimalismo expressivo; seleção direta.
- [C — Frequência](c-experimental.html): digital experimental; composição controlável.
- [Pesquisa, observações e decisões](RESEARCH.md)
- [Validação real e limites](VALIDATION.md)

## Abrir no navegador

No terminal, a partir do worktree `.worktrees/ux-art-direction-part2`:

```powershell
rtk proxy python -u prototypes/part2/serve.py
```

Abra **http://127.0.0.1:4194/**. Encerre com `Ctrl+C`. Não é necessário instalar pacotes, iniciar FastAPI ou configurar banco. O servidor expõe os protótipos e uma lista explícita de assets já existentes, somente no loopback. O suporte a HTTP Range permite o scrub do vídeo. O cameo da Estrelinha usa Three.js local se já disponível; se ausente, o conteúdo principal permanece funcional.

As três opções originais também podem ser abertas diretamente como arquivos HTML. A híbrida precisa do servidor acima para reutilizar os assets do produto sem copiá-los. HTTP local é a forma usada nos testes. Não use esses arquivos como substituição de `frontend/pages/`.

## O que experimentar

1. Em A, explore os três cartões e o CTA principal. Em B, altere o serviço por clique ou pelas setas do teclado e pressione Continuar. Em C, alterne Aberta/Compacta e depois use o CTA.
2. Reduza a janela: o menu mobile abre com Enter/clique, fecha com Escape ou após navegar.
3. O modal explica o próximo passo. Tab/Shift+Tab permanecem dentro dele; Escape e os botões fecham e devolvem o foco ao acionador.
4. Ative a preferência de redução de movimento do sistema: a escultura muda de estado sem transição, mantendo o controle disponível.

“Barbearia” é a marca padrão do projeto. As categorias são amostras declaradas. Não existem reservas, horários, preços, avaliações ou profissionais fictícios apresentados como reais.

## Capturas reais

| Direção | Desktop, viewport 1440 × 1000 | Mobile, viewport 390 × 844 |
|---|---|---|
| A | [Página completa](captures/a-desktop.png) | [Página completa](captures/a-mobile.png) |
| B | [Página completa](captures/b-desktop.png) | [Página completa](captures/b-mobile.png) |
| C | [Página completa](captures/c-desktop.png) | [Página completa](captures/c-mobile.png) |

Capturas são de página inteira; a altura final da imagem excede o viewport. Sem composição posterior ou imagens geradas por IA.

## Verificações reproduzíveis

```powershell
rtk proxy node --check prototypes/part2/assets/prototype.js
rtk proxy node --test prototypes/part2/tests/prototypes.test.mjs
rtk proxy git diff --check
```

Com Playwright MCP já disponível, executar `browser_run_code_unsafe` com `filename` apontando para `tests/qa.browser.js` (três originais, servidor estático em 4192), `tests/hybrid.browser.js` ou `tests/hero-intro.browser.js` (híbrida, servidor acima em 4194). As funções criam contextos Chromium limpos e os encerram. Não dependem de `@playwright/test` nem alteram o navegador usado para pesquisa. Os testes do servidor são executados com `python -m unittest discover -s prototypes/part2/tests -p test_preview_server.py -v`.

Arquivos principais: galeria, três alternativas originais e variação híbrida; folhas de estilo por direção; `assets/prototype.js`, `assets/hybrid.mjs` e `assets/hero-intro.mjs`; duas fontes com licenças; servidor de prévia, testes, documentação e capturas. A híbrida reutiliza os recursos de animação existentes, sem instalação adicional. Seu único armazenamento é a flag original de primeira visita em `sessionStorage`; sem cookie, formulário enviado ou chamada de API. CSP bloqueia conexão de dados e envio de formulário. Estas páginas não integram o build/startup do produto.
