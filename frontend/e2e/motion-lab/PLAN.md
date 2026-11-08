# Precisão que transforma — laboratório visual

Escopo aprovado: prova visual isolada, sem integração com index.html, backend,
API, banco ou autenticação. Sem commit, push ou deploy. A área e2e já é excluída
pelo build estático existente. Dependências e lockfile exclusivos deste laboratório.

- [x] A: intro com tesoura articulada, reação Canvas e continuidade no hero.
- [x] B: espelho transformável PREPARO → TÉCNICA → ACABAMENTO; um pin reversível.
- [x] C: encerramento editorial com reflexo recorrente e CTA estável.
- [x] Comparação pole SVG/CSS versus Three.js procedural independente.
- [x] Mobile, reduced-motion, pause, skip, Escape, replay e teardown.
- [x] Instrumentação: ticker único compartilhado, consumidores ativos, canvases,
      contextos WebGL, partículas, triggers, listeners próprios e bytes transferidos.
- [x] Validação executada, screenshots e comparação lado a lado com Temaki.

Escolhas: GSAP + ScrollTrigger locais via import map; wrappers acessíveis manuais;
Three apenas na comparação. Sem bundler nesta prova removível. Materiais construídos
com SVG/CSS/Canvas/geometria; sem fotos, downloads de stock ou pessoas fictícias.
img2threejs não é necessário para o pole genérico.

Evidência: 17/17 checks Chrome (checks.mjs), 26/26 testes Node existentes.
Revisão independente: cleanup parcial Three e recuperação após perda de contexto
cobertos e corrigidos. Console normal sem erros; zero acesso a backend/banco.
Ruling: pausa se refere ao ambiente automático, mantendo scroll do Ritual manual;
nome e tooltip explicitam isso. Bytes no HUD são subrecursos descomprimidos, não
uma estimativa de transferência comprimida. Pendência: aprovação visual do estudo
antes de qualquer integração com a HOME real.
