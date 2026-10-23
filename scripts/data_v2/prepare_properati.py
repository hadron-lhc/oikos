from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "data" / "properati" / "ar_properties.csv"
OUT_PATH = ROOT / "data" / "properati" / "properati_clean.csv"
AUDIT_PATH = ROOT / "data" / "properati" / "audit.json"
LOCATIONS_PATH = ROOT / "data" / "properati" / "location_options.json"
CENTROIDS_PATH = ROOT / "data" / "properati" / "city_centroids.json"
LOCATIONS_JS_PATH = ROOT / "static" / "js" / "locations_v2.js"

SOURCE_URL = (
    "https://www.kaggle.com/datasets/"
    "jluza92/argentina-properati-listings-dataset-20202021"
)
SOURCE_LICENSE = "CC BY-SA 3.0"

ZONE_MAP = {
    "Capital Federal": "CABA",
    "Bs.As. G.B.A. Zona Norte": "GBA Norte",
    "Bs.As. G.B.A. Zona Sur": "GBA Sur",
    "Bs.As. G.B.A. Zona Oeste": "GBA Oeste",
}

PROPERTY_TYPES = ["Casa", "Departamento", "PH"]

USECOLS = [
    "id",
    "ad_type",
    "start_date",
    "end_date",
    "created_on",
    "lat",
    "lon",
    "l2",
    "l3",
    "l4",
    "rooms",
    "bedrooms",
    "bathrooms",
    "surface_total",
    "surface_covered",
    "price",
    "currency",
    "property_type",
    "operation_type",
]


def slugify(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "desconocido"


def quantiles(series: pd.Series) -> dict[str, float]:
    clean = series.dropna()
    if clean.empty:
        return {}
    values = clean.quantile([0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1])
    return {str(index): round(float(value), 2) for index, value in values.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--audit", type=Path, default=AUDIT_PATH)
    args = parser.parse_args()

    if not args.raw.exists():
        raise SystemExit(f"No existe el CSV crudo: {args.raw}")

    raw = pd.read_csv(args.raw, usecols=USECOLS, low_memory=False)
    audit: dict[str, object] = {
        "source_url": SOURCE_URL,
        "source_license": SOURCE_LICENSE,
        "raw_rows": int(len(raw)),
    }

    frame = raw[raw["ad_type"].eq("Propiedad")].copy()
    audit["after_ad_type"] = int(len(frame))

    frame = frame[
        frame["operation_type"].eq("Venta")
        & frame["currency"].eq("USD")
        & frame["property_type"].isin(PROPERTY_TYPES)
        & frame["l2"].isin(ZONE_MAP)
    ].copy()
    audit["after_sale_usd_caba_gba"] = int(len(frame))

    frame["zona"] = frame["l2"].map(ZONE_MAP)
    frame["ciudad_label"] = frame["l3"].fillna(frame["l4"]).astype("string").str.strip()
    frame["ciudad_label"] = frame["ciudad_label"].replace({"": pd.NA})
    frame = frame[frame["ciudad_label"].notna()].copy()
    frame["ciudad"] = frame["ciudad_label"].map(slugify)
    frame["location"] = frame["zona"] + "|" + frame["ciudad"]

    frame["area"] = frame["surface_covered"].where(
        frame["surface_covered"].gt(0), frame["surface_total"]
    )
    frame["area_source"] = np.where(
        frame["surface_covered"].gt(0), "covered", "total"
    )

    for column in ["rooms", "bedrooms", "bathrooms", "price", "lat", "lon"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame.loc[frame["rooms"] <= 0, "rooms"] = np.nan
    frame.loc[frame["bedrooms"] < 0, "bedrooms"] = np.nan
    frame.loc[frame["bathrooms"] < 0, "bathrooms"] = np.nan

    inferred_bedrooms = (frame["rooms"] - 1).clip(lower=0)
    frame["bedrooms"] = frame["bedrooms"].fillna(inferred_bedrooms)
    inferred_rooms = frame["bedrooms"] + 1
    frame["rooms"] = frame["rooms"].fillna(inferred_rooms)

    for column in ["rooms", "bedrooms", "bathrooms"]:
        medians = frame.groupby("property_type")[column].transform("median")
        frame[column] = frame[column].fillna(medians)

    frame = frame[
        frame["price"].between(20_000, 3_000_000)
        & frame["area"].between(10, 2_000)
        & frame["rooms"].between(1, 20)
        & frame["bedrooms"].between(0, 20)
        & frame["bathrooms"].between(0, 20)
        & frame["bedrooms"].le(frame["rooms"])
        & frame["bathrooms"].le(frame["rooms"] + 2)
    ].copy()

    frame["price_per_m2"] = frame["price"] / frame["area"]
    frame = frame[frame["price_per_m2"].between(100, 15_000)].copy()
    audit["after_price_area_filters"] = int(len(frame))

    frame["lat_r"] = frame["lat"].round(4)
    frame["lon_r"] = frame["lon"].round(4)
    frame = frame.drop_duplicates(subset=["id"])
    frame = frame.drop_duplicates(
        subset=["lat_r", "lon_r", "area", "price", "property_type"]
    )
    audit["after_deduplication"] = int(len(frame))

    centroids = (
        frame.dropna(subset=["lat", "lon"])
        .groupby("location")[["lat", "lon"]]
        .median()
    )
    frame["lat"] = frame["lat"].fillna(frame["location"].map(centroids["lat"]))
    frame["lon"] = frame["lon"].fillna(frame["location"].map(centroids["lon"]))
    frame = frame.dropna(subset=["lat", "lon", "area", "price"]).copy()

    frame["start_date"] = pd.to_datetime(
        frame["start_date"], format="%Y-%m-%d", errors="coerce"
    )
    frame["created_on"] = pd.to_datetime(
        frame["created_on"], format="%Y-%m-%d", errors="coerce"
    )
    frame = frame[frame["start_date"].notna()].copy()

    frame = frame.sort_values("start_date").reset_index(drop=True)
    audit["final_rows"] = int(len(frame))
    audit["date_min"] = frame["start_date"].min().date().isoformat()
    audit["date_max"] = frame["start_date"].max().date().isoformat()
    audit["zones"] = frame["zona"].value_counts().to_dict()
    audit["property_types"] = frame["property_type"].value_counts().to_dict()
    audit["cities"] = int(frame["location"].nunique())
    audit["price"] = quantiles(frame["price"])
    audit["price_per_m2"] = quantiles(frame["price_per_m2"])
    audit["area"] = quantiles(frame["area"])
    audit["rooms"] = quantiles(frame["rooms"])
    audit["bedrooms"] = quantiles(frame["bedrooms"])
    audit["bathrooms"] = quantiles(frame["bathrooms"])
    audit["area_source"] = frame["area_source"].value_counts().to_dict()

    options: dict[str, list[dict[str, str]]] = {}
    for zona, group in (
        frame.groupby("zona")["ciudad_label"]
        .agg(lambda values: sorted(set(values)))
        .items()
    ):
        options[zona] = [
            {"value": slugify(label), "label": label} for label in group
        ]

    centroid_map = {
        location: [round(float(row.lat), 6), round(float(row.lon), 6)]
        for location, row in centroids.iterrows()
    }

    output_columns = [
        "id",
        "start_date",
        "end_date",
        "created_on",
        "lat",
        "lon",
        "zona",
        "ciudad",
        "ciudad_label",
        "location",
        "property_type",
        "rooms",
        "bedrooms",
        "bathrooms",
        "area",
        "area_source",
        "price",
        "price_per_m2",
    ]
    frame[output_columns].to_csv(args.out, index=False)
    args.audit.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    LOCATIONS_PATH.write_text(
        json.dumps(options, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    CENTROIDS_PATH.write_text(
        json.dumps(centroid_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    LOCATIONS_JS_PATH.write_text(
        "const UBICACIONES = "
        + json.dumps(options, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )

    print(f"Dataset limpio: {args.out} ({len(frame):,} filas)")
    print(f"Auditoría: {args.audit}")
    print(f"Ubicaciones: {LOCATIONS_PATH}")
    print(f"Centroides: {CENTROIDS_PATH}")
    print(f"Opciones UI: {LOCATIONS_JS_PATH}")
    print(f"Zonas: {audit['zones']}")
    print(f"Tipos: {audit['property_types']}")
    print(f"Fechas: {audit['date_min']} -> {audit['date_max']}")


if __name__ == "__main__":
    main()
