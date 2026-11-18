# Conformidade legal, privacidade e acessibilidade — auditoria 2026-11-18

Referência técnica para o controlador de cada instalação. **Não substitui parecer jurídico**: revise os textos de `frontend/pages/privacidade.html`, `termos.html` e `cookies.html` com assessoria antes de publicar.

## Achados e correções

| Tema | Achado | Correção |
| --- | --- | --- |
| Documentos legais | Não havia Política de Privacidade, Termos de Uso nem Política de Cookies públicos. | Páginas `privacidade.html`, `termos.html` e `cookies.html`, com links no rodapé de todas as páginas públicas e do cliente. |
| Dados legais da empresa | Rodapé sem razão social, CNPJ e endereço (Decreto nº 7.962/2013, art. 2º; CDC). | Bloco `legal` em `installation-config.mjs`. Rodapé e documentos exibem os dados configurados; CNPJ só aparece com dígitos verificadores válidos. Nenhum dado é inventado: campos vazios aparecem como "Não informado". |
| Copyright | Titular fixo "Barbearia Agendamento", diferente da marca da instalação. | `© ano` + razão social configurada (ou nome da marca, se ainda não preenchida). |
| Tracking | Nenhum Google Analytics, Tag Manager, pixel, Hotjar ou Clarity no código. | Mantido sem tracking. Teste Node impede inclusão acidental nas páginas principais. |
| Scripts de terceiros | A home baixava Three.js de `cdn.jsdelivr.net` em toda visita (envio de IP a terceiro sem necessidade). | Three.js `0.186.0` servido localmente em `frontend/assets/js/vendor/three/` com a licença MIT. |
| Cookies | Somente `refresh_token` (HttpOnly, essencial) e armazenamento local essencial. | Sem banner automático (não há cookie opcional). Preferências de cookies no rodapé e escolha salva por 12 meses em `barbearia.consent.v1`. |
| Google Maps | Iframe carregado sem consentimento, com `no-referrer-when-downgrade`. | Mapa só carrega após "Carregar mapa do Google" ou permissão nas preferências; `referrerpolicy=strict-origin-when-cross-origin`. |
| Formulário de cadastro | Pedia "nome completo"; aceite misturava consentimento com execução de contrato. | Pede apenas "Nome", e-mail e senha; aceite dos Termos e ciência da Política, com links e aviso de finalidade. |
| Avaliações | Média pública calculada só com avaliações visíveis: ocultar críticas aumentaria a nota (risco de prática enganosa, CDC art. 37). | `GET /appointments/avaliacoes/resumo` calcula média e total com todas as avaliações. Formulário avisa publicação sem nome; admin recebe critério de moderação. Avaliações continuam restritas ao dono de atendimento concluído, uma por atendimento. |
| Contraste | axe-core: `.service-index` 2,55:1 e 3,88:1; `.service-details`/`.service-duration` 4,41:1. | Tokens dos cards de serviço ajustados para ≥ 4,5:1. |
| Teclado | Menu móvel não fechava com Escape quando o foco estava no botão do menu. | Escape fecha o menu com foco no botão ou nos links e devolve o foco ao botão. |

## Pendências do controlador

- Preencher `legal` (razão social, CNPJ, endereço, e-mail, telefone, encarregado ou canal LGPD, data e versão) e manter `versaoDocumentos` igual a `TERMS_VERSION` do backend.
- Validar bases legais, prazos de retenção e o texto dos documentos com assessoria jurídica.
- Indicar encarregado (art. 41) ou confirmar a dispensa de agente de pequeno porte (Resolução CD/ANPD nº 2/2022), mantendo canal de atendimento ao titular.
- Listar operadores (hospedagem, banco, e-mail) e confirmar o mecanismo do art. 33 para transferências internacionais.
- Revisar direitos de imagem de fotos e vídeos publicados e a licença dos arquivos GSAP em `frontend/assets/js/vendor/gsap/`.
- Ao incluir qualquer ferramenta de análise ou publicidade: exigir consentimento prévio, atualizar a Política de Cookies e o teste que impede tracking.
