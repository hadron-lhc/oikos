from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / "data" / "properati"
DATASET = "jluza92/argentina-properati-listings-dataset-20202021"
DOWNLOAD_URL = f"https://www.kaggle.com/api/v1/datasets/download/{DATASET}"
RAW_NAME = "ar_properties.csv"
LICENSE = "CC BY-SA 3.0"


def credentials() -> tuple[str, str]:
    username = os.environ.get("KAGGLE_USERNAME")
    key = os.environ.get("KAGGLE_KEY")
    if username and key:
        return username, key

    path = Path.home() / ".kaggle" / "kaggle.json"
    if not path.exists():
        raise SystemExit(
            "Faltan credenciales de Kaggle. Configurá ~/.kaggle/kaggle.json "
            "o KAGGLE_USERNAME/KAGGLE_KEY."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["username"], payload["key"]


def download(destination: Path, force: bool) -> None:
    raw_path = destination / RAW_NAME
    zip_path = destination / "properati.zip"

    if raw_path.exists() and not force:
        print(f"Ya existe {raw_path}; no se descarga de nuevo.")
        return

    destination.mkdir(parents=True, exist_ok=True)
    username, key = credentials()
    token = base64.b64encode(f"{username}:{key}".encode()).decode()
    request = urllib.request.Request(
        DOWNLOAD_URL, headers={"Authorization": f"Basic {token}"}
    )

    print(f"Descargando {DATASET} ({LICENSE})...")
    with urllib.request.urlopen(request, timeout=120) as response, zip_path.open(
        "wb"
    ) as handle:
        shutil.copyfileobj(response, handle, length=1024 * 1024)

    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)

    if not raw_path.exists():
        raise SystemExit(f"El ZIP no contiene {RAW_NAME}")

    zip_path.unlink()
    print(f"Listo: {raw_path} ({raw_path.stat().st_size / 1024 / 1024:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    download(args.output_dir, args.force)


if __name__ == "__main__":
    main()
