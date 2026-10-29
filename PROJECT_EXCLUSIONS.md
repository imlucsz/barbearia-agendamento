# Exclusões para inspeção de rotina

Evite incluir estes caminhos em buscas amplas ou no contexto por padrão. Acesse-os somente quando a tarefa exigir e com o cuidado apropriado:

- `backend/.venv/`, `**/__pycache__/`, `*.pyc`: dependências instaladas e arquivos gerados.
- `backend/barbearia.db`, `*.db`, `*.sqlite`, `*.sqlite3`: bancos de dados locais ou de teste.
- `.env`, `.env.*`, `*.log`: configuração local e logs; não leia segredos sem necessidade.
- `node_modules/`, `dist/`, `build/`, `coverage/`: dependências e artefatos gerados, caso apareçam.
- `backups/`, `exports/`, `*.csv`, `*.xlsx`, `*.zip`: dados e arquivos de exportação.

Esta lista orienta o trabalho do agente; não é uma barreira técnica. Nunca a use como substituto de permissões do sistema, isolamento de segredos ou validação do conteúdo antes de compartilhá-lo.
