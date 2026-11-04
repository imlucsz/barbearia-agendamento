# Identidade e unicidade de e-mails — composição independente

## Escopo

Caracterização da política existente de main, sem mudanças funcionais de
e-mail, senha, sessão ou recuperação. Derivado do Lote 2 (f05f537).
Não inclui fd4e55a, cooldown nem migração de limites.

## Cobertura

- Schemas: caixa, espaços, Unicode NFC/NFD, IDNA e entradas inválidas.
- Cadastro/login/atualização: identidade equivalente, duplicatas, omissão/null,
  preservação de credenciais e respostas HTTP de conflito.
- Recuperação: endereços equivalentes como primeiras solicitações em fixtures
  independentes; destinatário e vínculo do token; resposta pública genérica.
  Não exige supressão de envios repetidos.
- PostgreSQL descartável: índice funcional, collation e duas conexões reais
  em cadastro concorrente; respostas 201/409 e uma conta persistida.
- Transporte simulado: SMTPUTF8 e payload Unicode. Aceite não prova entrega.

## Adaptações

Os dois testes que pressupunham cooldown foram isolados. Casos independentes
usam atores fictícios próprios para não esgotar o limitador de main.
Nenhum limite de produção foi alterado ou mockado.

## Limitações

Contas legadas NFD e diferenças entre lower SQL/collation e Python permanecem
caracterizadas; nenhuma correção de dados/política foi aplicada. Recuperação
mantém o comportamento e riscos de main, inclusive diferenças temporais.

## Evidências

A validação desta nova composição será registrada em
INTEGRACAO_QUALIDADE_AUTH_UX_INDEPENDENTE_20261104.md.
As contagens e resultados da branch completa não validam esta composição.
Somente bancos descartáveis e transportes simulados são permitidos.
