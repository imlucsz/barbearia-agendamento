# Estrelinha — assinatura cinematográfica

A fase1 apresenta o personagem existente como elemento decorativo, sem fala,
som, foco, cursor ou controles. A flag `estrelinhaWidget` continua podendo
desativá-lo completamente por instalação.

- `opening`: ponte após o hero, em diálogo com a linha editorial.
- `passage`: margem inferior do capítulo de agendamento, antes do Ritual.
- `finale`: margem superior do CTA, afastada do botão de agendamento.

Cada ponto aparece uma vez por carregamento, ao entrar na viewport. Os dois
primeiros duram2,6s e o encerramento3,6s. Uma única cena Three.js e um canvas
são transferidos entre os pontos; um único frame é renderizado em cada aparição,
sem loop RAF próprio. O brilho e o movimento de entrada/acomodação são CSS.
Ao sair da viewport ou ocultar a aba, a aparição é encerrada. Os nós são
`aria-hidden` e não interceptam cliques. Em reduced-motion, aparece um retrato
estático por1,8s, sem animação ou brilho em movimento.

O canvas e renderer são descartados em pagehide definitivo; em bfcache a cena
é mantida para retorno. Three.js continua usando a mesma origem e modelo 3D já
existentes no projeto. Se o módulo/WebGL não estiver disponível, os elementos
decorativos são removidos e a HOME continua utilizável.

Para futura opção híbrida, `optional-features.mjs` é o ponto de seleção entre
modos e o antigo `widget.js` permanece preservado. O modelo, materiais e
acessórios são compartilháveis. Será necessário definir explicitamente um host,
controle de foco, ciclo de vida e interface de interação para o modo híbrido;
nenhuma interface de assistência foi criada nesta fase.

Validação: 27 testes Node, incluindo flag desativada; 44 testes existentes da
HOME; e2e dedicado com 2 perfis (desktop1440×900 e mobile390×844), incluindo
as três aparições, canvas único, retorno à seção e reduced-motion. Capturas em
`frontend/e2e/motion-lab/artifacts/estrelinha-{opening,passage,finale}.png`
e `estrelinha-mobile-{opening,passage,finale}.png`. Navegação normal observada
sem erros de console. Nenhum commit, push ou deploy.
