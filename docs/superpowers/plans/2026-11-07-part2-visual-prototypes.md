# Parte 2 — três direções para aprovação visual

Base: `19cfa2738fb30f81339f1dfc472b99b139a6b7bb` (Parte 1). Branch isolada: `design/ux-art-direction-part2`.

## Escopo autorizado

Pesquisa de referências públicas e três homepages em `prototypes/part2/`. Nenhuma alteração no frontend funcional, calendário, backend, contratos, banco ou implantação. Marca provisória já existente: “Barbearia”. Categorias de serviço são amostras explicitamente identificadas; sem preço, disponibilidade, endereço ou avaliações inventadas.

## Hipóteses

- A / Entrelinhas: composição editorial assimétrica, serifada expressiva, papel e azul ultramarino; navegação por capítulos e catálogo com pesos distintos.
- B / Intervalo: produto claro, tipografia sem serifa, escolha do serviço no primeiro plano, verde e neutros; estado de seleção e resumo imediato.
- C / Frequência: cartaz digital, composição tipográfica em camadas, forma abstrata controlável, ameixa e lima; movimento opt-in independente do agendamento.

## Sequência e verificação

1. Registrar fontes realmente acessadas, observações e limitações de carregamento.
2. Criar páginas independentes com assets locais e sem dependências de execução externas.
3. Exercitar navegação, CTA, seleção, teclado, modal, responsividade e movimento reduzido em Chromium real.
4. Capturar desktop 1440 × 1000 e mobile 390 × 844; inspecionar os seis resultados e corrigir problemas visuais.
5. Documentar comparação, testes e instruções. Atualizar Graphify somente neste worktree.
6. Parar para escolha visual. Sem integração definitiva nem commit nesta etapa.

## Critérios

Três composições perceptivelmente diferentes; hero sem fotografia genérica; CTA acessível; nenhum dado fictício apresentado como real; ausência de rolagem horizontal a 320 px; foco visível e retorno de foco; controles com alvo mínimo de 44 px; respeito a redução de movimento; nenhuma requisição de API ou armazenamento de dados.

## Estado

Pesquisa, três protótipos e inspeção de seis capturas concluídas. Chromium: 109 verificações aprovadas; Node: 5 testes aprovados. Revisão independente somente leitura sem achados concretos. Aprovação da direção pendente; redesign definitivo não iniciado.
