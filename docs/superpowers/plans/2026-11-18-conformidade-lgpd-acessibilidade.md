# Objetivo e limites
Adequar o site à LGPD e reduzir riscos jurídicos e de acessibilidade sem mudar rotas existentes, schema do banco ou fluxo de autenticação.

## Aceite
- Política de Privacidade, Termos de Uso e Política de Cookies públicas e linkadas no rodapé.
- Dados legais configuráveis, sem dados inventados; copyright com o titular configurado.
- Nenhum tracking; nenhum script de CDN; mapa do Google somente com consentimento.
- Média pública de avaliações inclui avaliações ocultas.
- axe-core sem violações nas páginas auditadas; Escape fecha o menu móvel.

## Áreas e etapas
- [x] `installation-config.mjs`, `legal.mjs`, `cookie-consent.mjs`, `legal-page.mjs`, `api.js`.
- [x] Páginas legais, rodapés, cadastro, avaliação, admin (texto de moderação).
- [x] `home.js` (mapa, menu, avaliações) e CSS de contraste.
- [x] Endpoint aditivo `GET /appointments/avaliacoes/resumo`.
- [x] Three.js local em `frontend/assets/js/vendor/three/`.
- [x] Testes Node, Python e Playwright; documentação.

## Riscos e recuperação
Mudança aditiva, sem migração. O texto jurídico depende de validação do controlador. Reverter apenas os arquivos listados acima.

## Validação
Node, testes Python de avaliações e matriz de rotas, Playwright essencial e responsivo, axe-core, `git diff --check`.

## Progresso e evidências
Ver `docs/CONFORMIDADE_LEGAL.md` e `docs/REQUISITOS_STATUS.md`.
