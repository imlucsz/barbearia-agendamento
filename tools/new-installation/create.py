#!/usr/bin/env python3
"""Create a clean single-barbershop deployment tree without installation data."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit


CORE_ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "coverage", "test-results", "backups", "exports",
    "archive", "uploads", "data", "storage", "logs", ".aws", ".codex", ".agents", ".vscode",
}
SKIP_EXTENSIONS = {".db", ".sqlite", ".sqlite3", ".dump", ".age", ".csv", ".xlsx", ".xls"}
SAFE_ENV = """# Fresh per-installation environment. Replace every example before production.
APP_ENV=production
INSTALLATION_NAME=Barbearia
DATABASE_URL=postgresql+psycopg://barbearia_app:CHANGE_ME@db.example.invalid:5432/barbearia
CORS_ALLOWED_ORIGINS=https://www.example.invalid
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
TERMS_VERSION=1.0
TRUSTED_PROXY_COUNT=0
RATE_LIMIT_MAX_ATTEMPTS=5
RATE_LIMIT_BLOCK_MINUTES=15
RETENTION_DAYS=365
METRICS_TOKEN=
FORCE_HTTPS=true
SCHEDULING_TIMEZONE=America/Sao_Paulo
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_TIMEOUT_SECONDS=10
PASSWORD_RESET_URL=https://www.example.invalid/pages/reset.html
"""
CHECKLIST = """# Checklist de instalação

- [ ] Definir nome, textos de campanha, marca/símbolo, cores e logotipo em `frontend/assets/js/installation-config.mjs`, `frontend/assets/css/installation.css` e `frontend/assets/branding/`.
- [ ] Definir domínio da aplicação e DNS; publicar o frontend e API sob o mesmo domínio registrável.
- [ ] Instalar certificado TLS e confirmar HTTPS no frontend e API.
- [ ] Criar banco PostgreSQL novo, usuário exclusivo e credencial em secret store/passfile. Nunca reutilizar banco ou dados de outra instalação.
- [ ] Preencher `backend/.env`: `INSTALLATION_NAME`, URL do banco, segredo forte próprio, `CORS_ALLOWED_ORIGINS` com a origem exata, `SCHEDULING_TIMEZONE`, `TERMS_VERSION` e SMTP/reset URL.
- [ ] Sincronizar o texto `content.consentText` com `TERMS_VERSION` e os termos legais aprovados pela instalação.
- [ ] Instalar dependências em `backend/.venv`; executar `python -m alembic upgrade head` no banco novo.
- [ ] Criar o primeiro administrador com `python -m app.initial_admin` no ambiente configurado.
- [ ] Preencher dados institucionais no painel (contatos, endereço, mapa, horários) e criar serviços/equipe.
- [ ] Configurar backup PostgreSQL diário, criptografia, destino fora do servidor e teste trimestral: `docs/PLANO_RECUPERACAO_DESASTRES.md`.
- [ ] Definir política por instalação para rotação de `SECRET_KEY`, SMTP e credenciais do banco.
- [ ] Iniciar API e frontend. Definir `API_URL` e `FRONTEND_URL`; executar `tools/new-installation/smoke.ps1` ou `bash tools/new-installation/smoke.sh`.
- [ ] Confirmar `/health`, `/ready`, catálogo público e carregamento da home; realizar um agendamento fictício antes de liberar tráfego.

O gerador não copia bancos, arquivos `.env`, exports, backups ou arquivos de `assets/branding` da origem. Ele cria um `.env` novo com valores de exemplo para preencher.
"""
BRANDING_README = """# Marca desta instalação

Coloque aqui somente imagens raster próprias deste estabelecimento (PNG, JPEG, WebP ou AVIF) e configure `brand.logoUrl` em `../js/installation-config.mjs`. Esta pasta é separada entre instalações; o gerador nunca copia seus arquivos de origem.
"""


def valid_api_origin(value: str) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ValueError("API URL must be a valid HTTPS origin") from None
    if (
        parsed.scheme != "https" or not parsed.netloc or not parsed.hostname or parsed.username or parsed.password
        or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ValueError("API URL must be a clean HTTPS origin (without credentials, path, query or fragment)")
    return value.rstrip("/")


def make_frontend_config(name: str, api_url: str) -> str:
    if not name.strip() or len(name.strip()) > 80 or any(ord(char) < 32 for char in name):
        raise ValueError("Installation name must contain 1–80 printable characters")
    api_url = valid_api_origin(api_url)
    mark = "".join(part[0] for part in re.split(r"\s+", name.strip())[:3]).upper() + "."
    data = {
        "apiBaseUrl": api_url,
        "brand": {"name": name.strip(), "mark": mark[:8], "tagline": "ESTILO COM ATITUDE", "logoUrl": "", "themeColor": "#15120f"},
        "content": {
            "homeHeroEyebrow": "Seu próximo visual começa aqui",
            "homeHeroTitleLead": "O clássico nunca sai de",
            "homeHeroTitleAccent": "cena.",
            "homeHeroDescription": "Cuidado de verdade, conversa boa e um corte feito para você. Escolha seu serviço e reserve seu horário sem complicação.",
            "homePrimaryAction": "Escolher meu horário",
            "homeSecondaryAction": "Explorar serviços",
            "homeFooterMessage": "Um bom corte muda o dia.",
            "consentText": "Li e aceito o tratamento dos meus dados pessoais para cadastro e gestão dos agendamentos.",
        },
        "features": {"estrelinhaWidget": True},
    }
    return "// Per-installation settings. Keep credentials in backend/.env, never here.\n" \
        f"export const INSTALLATION_CONFIG = Object.freeze({json.dumps(data, ensure_ascii=False, indent=2)});\n"


def is_private_file(relative: Path) -> bool:
    name = relative.name.lower()
    if name == ".env" or name.startswith(".env."):
        return True
    if name.endswith(("-wal", "-shm", ".db-journal")):
        return True
    if relative.suffix.lower() in SKIP_EXTENSIONS or name.endswith((".dump.age", ".tar.gz", ".zip")):
        return True
    if name.endswith((".log", ".bak", ".backup")):
        return True
    return False


def copy_clean_tree(source: Path, target: Path) -> None:
    target.mkdir(parents=False)
    for current, directories, files in os.walk(source, topdown=True, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(source)
        directories[:] = [
            name for name in directories
            if name not in SKIP_DIRS and not (current_path / name).is_symlink()
            and not (name == ".env" or name.startswith(".env."))
            and not (relative_dir / name).as_posix().startswith("frontend/assets/branding")
        ]
        output_dir = target / relative_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        for filename in files:
            source_file = current_path / filename
            relative = source_file.relative_to(source)
            if source_file.is_symlink() or is_private_file(relative):
                continue
            if relative.as_posix().startswith("frontend/assets/branding/"):
                continue
            if filename == ".env.example":
                continue
            output_file = target / relative
            output_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, output_file)


def create_installation(target_arg: str, name: str, api_url: str, source: Path = CORE_ROOT) -> Path:
    source = source.resolve(strict=True)
    target = Path(target_arg).expanduser().resolve(strict=False)
    if not source.is_dir() or not (source / "backend" / "app" / "main.py").is_file():
        raise ValueError("Source must be the project core directory")
    if target.exists():
        raise ValueError("Target must not exist; choose a new, empty destination path")
    if target == source or source in target.parents or target in source.parents:
        raise ValueError("Target must be separate from the core source directory")
    make_frontend_config(name, api_url)  # Validate before creating the target.
    copy_clean_tree(source, target)

    backend = target / "backend"
    backend.mkdir(exist_ok=True)
    (backend / ".env.example").write_text(SAFE_ENV, encoding="utf-8", newline="\n")
    env_name = name.strip().replace("\\", "\\\\").replace('"', '\\"')
    instance_env = SAFE_ENV.replace("INSTALLATION_NAME=Barbearia", f'INSTALLATION_NAME="{env_name}"')
    (backend / ".env").write_text(instance_env, encoding="utf-8", newline="\n")
    config_path = target / "frontend" / "assets" / "js" / "installation-config.mjs"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(make_frontend_config(name, api_url), encoding="utf-8", newline="\n")
    brand_dir = target / "frontend" / "assets" / "branding"
    brand_dir.mkdir(parents=True, exist_ok=True)
    (brand_dir / ".gitkeep").touch()
    (brand_dir / "README.md").write_text(BRANDING_README, encoding="utf-8", newline="\n")
    (target / "INSTALLATION_CHECKLIST.md").write_text(CHECKLIST, encoding="utf-8", newline="\n")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="new destination directory; must not already exist")
    parser.add_argument("--name", required=True, help="barbershop display name")
    parser.add_argument("--api-url", required=True, help="public HTTPS API origin")
    args = parser.parse_args()
    try:
        destination = create_installation(args.target, args.name, args.api_url)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Clean installation scaffold created: {destination}")
    print("Review INSTALLATION_CHECKLIST.md and fill backend/.env before starting services.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
