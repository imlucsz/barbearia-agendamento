# Continuidade editorial — telas do produto

Direção A híbrida já aprovada pelo usuário. Worktree `ux-art-direction-part2`, branch `design/ux-art-direction-part2`. Sem commit ou publicação.

## Escopo

Levar a identidade da home a login, cadastro, recuperação, catálogo, agendamento, área do cliente e gestão. Reutilizar Fraunces/Space Grotesk locais, tokens da instalação e todos os endpoints/controles existentes. Não modificar home, backend, regras de disponibilidade ou autenticação.

## Execução

1. [x] Inspecionar páginas, estilos, calendário, navegação e hooks existentes.
2. [x] Aplicar CSS compartilhado e delimitado; hierarquia dos formulários, seleção, revisão e gestão; navegação e progresso acessíveis.
3. [x] Preservar contexto nas voltas do agendamento e no reagendamento; testar erros e nova tentativa.
4. [x] Validar no Chromium com API fictícia local, desktop/mobile, teclado, conteúdo não confiável, estados de calendário e permissões visuais. Inspecionar screenshots.
5. [x] Executar regressões Node e checks proporcionais; revisão independente; atualizar documentação. Atualização AST do Graphify e Git no fechamento.

Resultado: Chromium 200/200; Node 61/61; Python 7/7 com SQLite temporário. Revisão independente sem achados. Incluídas correções de retry da confirmação, contexto de retorno, layout mobile administrativo e ordem do módulo novo após configuração de mesma origem. Relatório em `docs/PRODUCT_EDITORIAL_INTEGRATION.md`.

## Critérios

Sem dependências novas; sem animação de abertura nas páginas internas; foco visível, alvos de toque de 44px, reduced-motion, ausência de overflow horizontal. Não esconder controles de gestão nem flexibilizar permissões. Distinguir testes visuais com fixtures de validação real do backend/produção. Preservar alterações anteriores e arquivos locais.
