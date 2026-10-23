from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "properati" / "properati_clean.csv"
MODELS_PATH = ROOT / "src" / "models"
CENTROIDS_PATH = ROOT / "data" / "properati" / "city_centroids.json"
LOCATIONS_PATH = ROOT / "data" / "properati" / "location_options.json"

FEATURE_NAMES = [
    "property_type_encoded",
    "location_encoded",
    "rooms",
    "bedrooms",
    "bathrooms",
    "area",
    "lat",
    "lon",
    "rooms_per_m2",
    "bathrooms_per_room",
    "area_per_room",
]


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["rooms_per_m2"] = frame["rooms"] / frame["area"]
    frame["bathrooms_per_room"] = frame["bathrooms"] / frame["rooms"]
    frame["area_per_room"] = frame["area"] / frame["rooms"]
    return frame


def metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float | int]:
    return {
        "n": int(len(y_true)),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 2),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "mape": round(float(mean_absolute_percentage_error(y_true, y_pred)), 4),
        "medae": round(float(median_absolute_error(y_true, y_pred)), 2),
    }


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(
            f"No existe {DATA_PATH}. Ejecutá scripts/data_v2/prepare_properati.py"
        )

    frame = pd.read_csv(DATA_PATH, parse_dates=["start_date"])
    frame = add_features(frame)

    property_type_encoder = LabelEncoder()
    location_encoder = LabelEncoder()
    frame["property_type_encoded"] = property_type_encoder.fit_transform(
        frame["property_type"]
    )
    frame["location_encoded"] = location_encoder.fit_transform(frame["location"])

    train_mask = frame["start_date"] < "2021-02-01"
    val_mask = (frame["start_date"] >= "2021-02-01") & (
        frame["start_date"] < "2021-03-15"
    )
    test_mask = frame["start_date"] >= "2021-03-15"

    if train_mask.sum() == 0 or val_mask.sum() == 0 or test_mask.sum() == 0:
        raise SystemExit("El split temporal quedó vacío; revisar las fechas")

    X = frame[FEATURE_NAMES]
    y = frame["price"]

    model = RandomForestRegressor(
        n_estimators=50,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X[train_mask], y[train_mask])

    results = {
        "train": metrics(y[train_mask], model.predict(X[train_mask])),
        "validation": metrics(y[val_mask], model.predict(X[val_mask])),
        "test": metrics(y[test_mask], model.predict(X[test_mask])),
    }

    importances = sorted(
        zip(FEATURE_NAMES, model.feature_importances_),
        key=lambda item: item[1],
        reverse=True,
    )

    MODELS_PATH.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODELS_PATH / "modelo_general_v2.pkl")
    joblib.dump(property_type_encoder, MODELS_PATH / "property_type_encoder_v2.pkl")
    joblib.dump(location_encoder, MODELS_PATH / "location_encoder_v2.pkl")

    centroids = json.loads(CENTROIDS_PATH.read_text(encoding="utf-8"))
    locations = json.loads(LOCATIONS_PATH.read_text(encoding="utf-8"))
    (MODELS_PATH / "city_centroids_v2.json").write_text(
        json.dumps(centroids, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (MODELS_PATH / "location_options_v2.json").write_text(
        json.dumps(locations, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    metadata = {
        "model_name": "oikos-rf-v2",
        "created_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "source": "Properati Data 2020-2021",
        "source_url": (
            "https://www.kaggle.com/datasets/"
            "jluza92/argentina-properati-listings-dataset-20202021"
        ),
        "source_license": "CC BY-SA 3.0",
        "training_rows": int(train_mask.sum()),
        "validation_rows": int(val_mask.sum()),
        "test_rows": int(test_mask.sum()),
        "date_min": frame["start_date"].min().date().isoformat(),
        "date_max": frame["start_date"].max().date().isoformat(),
        "feature_names": FEATURE_NAMES,
        "metrics": results,
        "feature_importances": {
            name: round(float(value), 4) for name, value in importances
        },
        "property_type_classes": [
            str(value) for value in property_type_encoder.classes_
        ],
        "location_classes": [str(value) for value in location_encoder.classes_],
    }
    (MODELS_PATH / "metrics_v2.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Filas: {len(frame):,}")
    print(f"Train/Val/Test: {train_mask.sum():,}/{val_mask.sum():,}/{test_mask.sum():,}")
    for split, values in results.items():
        print(
            f"{split:10s} MAE ${values['mae']:,.0f} | "
            f"RMSE ${values['rmse']:,.0f} | R² {values['r2']:.4f} | "
            f"MAPE {values['mape']:.2%}"
        )
    print("Importancias:")
    for name, value in importances:
        print(f"  {name}: {value:.3f}")
    print(f"Modelo: {MODELS_PATH / 'modelo_general_v2.pkl'}")
    print(f"Métricas: {MODELS_PATH / 'metrics_v2.json'}")


if __name__ == "__main__":
    main()
