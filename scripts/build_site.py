from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "templates" / "index.html"
STATIC_PATH = ROOT / "static"
DIST_PATH = ROOT / "dist"
MODEL_JSON = STATIC_PATH / "model" / "oikos-rf-v2.json"
MODEL_BIN = STATIC_PATH / "model" / "oikos-rf-v2.bin"

STATIC_URL_PATTERN = re.compile(
    r"\{\{\s*url_for\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}"
)
JINJA_PATTERN = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")

HEADERS = """\
/
  Cache-Control: no-cache

/index.html
  Cache-Control: no-cache

/static/model/*
  Cache-Control: public, max-age=31536000, immutable

/static/js/*
  Cache-Control: public, max-age=3600

/static/css/*
  Cache-Control: public, max-age=3600

/static/images/*
  Cache-Control: public, max-age=86400

/*
  X-Content-Type-Options: nosniff
"""


def build() -> None:
    if not TEMPLATE_PATH.exists():
        raise SystemExit(f"No existe {TEMPLATE_PATH}")
    if not STATIC_PATH.exists():
        raise SystemExit(f"No existe {STATIC_PATH}")
    if not MODEL_JSON.exists() or not MODEL_BIN.exists():
        raise SystemExit(
            "Falta el modelo exportado. Ejecutá: .venv/bin/python scripts/export_model_v2.py"
        )

    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = STATIC_URL_PATTERN.sub(lambda match: f"/static/{match.group(1)}", html)

    remaining = JINJA_PATTERN.search(html)
    if remaining:
        raise SystemExit(f"Quedó sintaxis Jinja sin resolver: {remaining.group(0)}")

    if DIST_PATH.exists():
        shutil.rmtree(DIST_PATH)
    DIST_PATH.mkdir(parents=True)

    shutil.copytree(STATIC_PATH, DIST_PATH / "static")
    (DIST_PATH / "index.html").write_text(html, encoding="utf-8")
    (DIST_PATH / "_headers").write_text(HEADERS, encoding="utf-8")

    total_bytes = sum(
        path.stat().st_size for path in DIST_PATH.rglob("*") if path.is_file()
    )
    print(f"Sitio generado en {DIST_PATH}")
    print(f"Archivos: {sum(1 for path in DIST_PATH.rglob('*') if path.is_file())}")
    print(f"Tamaño total: {total_bytes / 1024 / 1024:.2f} MB")
    print(f"Modelo: {MODEL_BIN.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    build()
