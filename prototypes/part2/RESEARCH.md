# Direção de arte — pesquisa e comparação

Pesquisa realizada em 7 de novembro de 2026. Páginas públicas acessadas via web e Chromium real, com inspeção das capturas. Não houve login em bibliotecas, compra de assets nem acesso ao ambiente publicado da barbearia. Nenhum layout, marca, fotografia ou código dessas referências foi copiado para os protótipos.

## Referências efetivamente acessadas

| Fonte | Observação verificável | Aplicação / limite |
|---|---|---|
| [MotionSites](https://motionsites.ai/) | Hero tipográfica central, navegação compacta, filtros de categoria e galeria em colunas. Vários thumbnails permaneceram cinza na captura. | Reforçou a importância de comparar composição, e não só cores. Não reproduzimos o brilho, o gradiente nem os templates; não afirmamos ter avaliado animações dos exemplos não carregados. |
| [Awwwards](https://www.awwwards.com/) | Título de grande escala, metadados pequenos, projeto destacado em área visual larga; categorias de tipografia e ilustração disponíveis. | Contraste de escala e edição da hierarquia em A/C. Observamos a página da curadoria; não auditamos o site completo do projeto destacado. |
| [Mobbin](https://mobbin.com/) | Landing pública com título curto dominante, poucos CTAs e demonstração da biblioteca. O texto público organiza referências em telas, fluxos e animações. | Critério de clareza e comparação por jornada. Não tivemos acesso autenticado aos fluxos: nenhuma conclusão sobre uma jornada interna específica é apresentada como observação. |
| [Order — portfólio](https://order.design/) | Legendas monoespaçadas discretas, projetos com área visual ampla e estrutura editorial enxuta. O primeiro projeto visível apresentava identidade gráfica em embalagens. | Ritmo entre imagem/composição e legenda; identidade sustentada por um sistema gráfico, sem precisar de uma foto de barbeiro. |
| [Order — Chapter](https://order.design/project/chapter) | Grade assimétrica com texto, créditos e categorias em colunas estreitas. O case descreve a relação entre símbolo, tipografia, voz e transição. | A usa uma relação deliberada entre serifada expressiva, controles objetivos e contornos. O conceito e a arte são próprios; não adotamos as fontes comerciais nem a paleta do case. |
| [Studio Dumbar — NextStep 22](https://studiodumbar.com/work/outsystems) | Texto do case consultado: tipografia dinâmica e motivo angular formam uma identidade conjunta. Home e case abriram no Chromium, mas a área de vídeo permaneceu preta. | Referência conceitual para C: um motivo gráfico com comportamento consistente. Não alegamos ter observado o movimento dos vídeos. |
| [Studio Feixen](https://www.studiofeixen.ch/) | Navegação com símbolos de espaço/superfície/tempo; links de fontes, cartazes e projetos em módulos com desenhos de linha. A lista de trabalhos não concluiu o carregamento. | Vocabulário abstrato e tipográfico como identidade. Inspiração limitada aos elementos visíveis; nenhum projeto não carregado foi usado como evidência. |
| [Cal.com](https://cal.com/) | A demonstração pública da homepage apresenta contexto da reserva, duração/fuso, calendário e área de horários em colunas; botões e estados selecionados são reconhecíveis. | B aproxima a escolha da primeira tela. Nas três opções, serviço → profissional → disponibilidade continua sendo a ordem. A demo foi observada; nenhuma reserva foi feita e não se auditou o backend do serviço. |

## Premissas de identidade

O projeto usa “Barbearia” como nome padrão. Não há neste briefing nome comercial final, pesquisa de público, acervo fotográfico autorizado ou história institucional confirmada. Os conceitos são hipóteses para aprovação, não uma afirmação sobre o público real.

A promessa comum é **cuidado com o visual e respeito pelo tempo do cliente**. “Corte”, “Barba” e “Corte + barba” são amostras explicitamente identificadas, não um catálogo publicado. Não criamos preços, durações, vagas, pessoas, depoimentos, endereço ou avaliações. O calendário inteligente da Parte 1 permanece intacto.

## Três sistemas, três composições

| Decisão | A — Entrelinhas | B — Intervalo | C — Frequência |
|---|---|---|---|
| Conceito | Cuidado como edição do próprio traço | Abrir espaço no dia | Encontrar um ritmo pessoal |
| Composição | Manchete editorial, margem anotada, gravura abstrata lateral, catálogo assimétrico | Título compacto em três linhas, painel de escolha já na hero, sequência de passos | Cartaz em caixa alta, alinhamento deslocado, escultura de linhas, painéis cromáticos |
| Tipografia | Fraunces regular expressiva + Space Grotesk funcional | Space Grotesk média; contraste por tamanho e peso, sem serifada | Space Grotesk semibold em caixa alta; recuos, escala e composição de palavra |
| Paleta | Papel `#f4f1e9`, tinta `#232423`, ultramarino `#2638cc` | Névoa `#f5f6f2`, verde profundo `#153d2d`, ação `#215c3b`, folha `#d5e5ae` | Ameixa `#32233e`, papel `#f4f1e9`, lilás `#d1b9e6`, lima `#ddf89c` |
| Componentes | Bordas retas, links editoriais e cards com pesos diferentes | Painel com raio de 12 px, linhas de seleção com rádio nativo, resumo imediato | Controles retos, estados preenchidos, catálogo como painéis de cartaz |
| Gesto | Seta se desloca para indicar ação; links mantêm legibilidade | Seleção responde imediatamente com borda, marca e resumo | Alternância Aberta/Compacta transforma a escultura sob comando explícito |
| Mobile | Texto e CTA primeiro; a gravura vira faixa compacta | Escolha fica em painel abaixo do título; âncora leva direto ao painel | CTA antes da escultura; controles ao lado da arte; catálogo em pilha |
| Principal trade-off | Precisa preservar a legibilidade da serifada em telas e textos longos | Mais eficiente, porém menos singular na primeira impressão | Maior personalidade; exige disciplina para a expressão não invadir o fluxo transacional |

Espaçamento deriva de 4/8 px, com módulos de 16, 24, 32, 48 e 64 px. Algumas medidas ópticas diferem para compor a tipografia. Números e metadados usam Courier New. Ícones são traços/símbolos simples, com nome acessível quando acionáveis. Nenhuma hero depende de fotografia.

As fontes locais são [Fraunces](https://github.com/google/fonts/tree/main/ofl/fraunces) e [Space Grotesk](https://github.com/google/fonts/tree/main/ofl/spacegrotesk), distribuídas com os arquivos SIL OFL originais em `assets/fonts/`. Não há carregamento de fontes em terceiros durante o uso.

## Movimento e acessibilidade

- Feedback de botões: 160 ms; seleção: 130 ms; leve elevação dos painéis C: 200 ms. Função: confirmar o alvo acionável.
- Transformação da escultura: 550 ms, somente após clique/toque/teclado; não bloqueia CTA nem altera layout.
- Sem autoplay, parallax, vídeo, áudio, scroll hijacking, cursor personalizado, intro obrigatória ou animação de confirmação fictícia.
- `prefers-reduced-motion: reduce` remove transições e scroll suave; os estados continuam funcionais.
- Links de pular conteúdo, headings semânticos, foco visível, navegação com teclado, rádio nativo, modal nomeado com retorno de foco. Alvos acionáveis medidos em pelo menos 44 px de altura.
- Contraste dos textos visíveis das três páginas verificado por cálculo RGB no Chromium. Isso não substitui auditoria WCAG completa nem teste com leitor de tela.

## Recomendação

**A — Entrelinhas** é o melhor equilíbrio para este briefing: tem identidade expressiva sem depender de efeitos, mantém um CTA óbvio e oferece um sistema editorial extensível a serviços e profissionais. A assimetria continua legível no mobile e o catálogo varia a composição sem perder unidade.

B é a alternativa quando a prioridade for reduzir a distância entre chegada e escolha. C é a alternativa de maior impacto autoral; a forma interativa é opcional e não compete com a ação principal. Não há dados de conversão ou teste com usuários que comprovem superioridade de uma proposta.

**A decisão final aguarda aprovação visual.** Após a escolha: consolidar tokens na arquitetura existente, usar dados reais do catálogo, integrar o calendário já validado, tratar dark mode e estados de erro/carregamento do produto, comparar telas e testar a jornada completa. Nada disso foi antecipado nesta etapa.
