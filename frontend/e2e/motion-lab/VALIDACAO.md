# Sincronização dos checks — 2026-11-03

Runtime e assets preservados. Checks gerais: 17/17; vídeo: 18/18, executados
isoladamente em Chrome headless. Não se aplicam como prova de Firefox/Safari.

- Intro: watchdog existente em 4,5s e limite de teste de 6s preservados.
  O predicado de conclusão agora usa polling de 100ms, independente de RAF
  atrasado no ambiente headless. O probe anterior observou conclusão sem pageerror.
- Preferência: waits fixos de 250ms observavam estado anterior ou reconstrução
  intermediária do matchMedia (inclusive 0 triggers ao restaurar). Os checks
  aguardam reduced/contagem de triggers esperados; todas as asserções permanecem.
- Capítulo: currentTime/seeked precedem publicação por rVFC e transição HTML
  de 0,4s. Esperar 450ms não garante apresentação sob carga. O check aguarda
  capítulo publicado e elemento visível; preserva testes de tempo, máscara e texto.

Classificação: sincronização inadequada dos testes sob variabilidade de ambiente,
sem regressão funcional demonstrada. Não decorre do scrub universal da HOME:
o Lab preserva intencionalmente seu estudo mobile segmentado e espelho anterior.
Um timeout de seek ocorreu com suítes simultâneas; 18/18 passaram isoladamente.
Executar os dois comandos sequencialmente, sem transformar contenção local em
mudança de timeout/codec/runtime:

```
node frontend/e2e/motion-lab/checks.mjs
node frontend/e2e/motion-lab/video-checks.mjs
```

A aplicação pública importa apenas recursos de frontend/assets. O Lab é ferramenta
experimental, fora do build; probes E2E reutilizam seu servidor e o teste da
Estrelinha usa Three local como fixture. Isso é dependência de desenvolvimento,
não dependência do runtime público. /reference exige HTML externo opcional.
