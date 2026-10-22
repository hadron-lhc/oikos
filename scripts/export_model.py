from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "src" / "models" / "modelo_general.pkl"
ZONA_ENCODER_PATH = ROOT / "src" / "models" / "zona_encoder.pkl"
CIUDAD_ENCODER_PATH = ROOT / "src" / "models" / "ciudad_encoder.pkl"
OUTPUT_DIR = ROOT / "static" / "model"
OUTPUT_BIN = OUTPUT_DIR / "oikos-rf-v1.bin"
OUTPUT_JSON = OUTPUT_DIR / "oikos-rf-v1.json"
FIXTURES_PATH = ROOT / "tests" / "model_fixtures.json"

FEATURE_NAMES = [
    "ambientes",
    "bathrooms",
    "area",
    "ambientes_por_m2",
    "baños_por_ambiente",
    "zona_encoded",
    "ciudad_encoded",
]

FIXTURE_INPUTS = [
    {"ambientes": 3, "bathrooms": 2, "area": 120, "zona": "GBA Norte", "ciudad": "pilar"},
    {"ambientes": 4, "bathrooms": 3, "area": 180, "zona": "Córdoba", "ciudad": "cordoba"},
    {"ambientes": 2, "bathrooms": 1, "area": 65, "zona": "Costa Atlántica", "ciudad": "mar-del-plata"},
    {"ambientes": 5, "bathrooms": 4, "area": 250, "zona": "GBA Sur", "ciudad": "la-plata"},
    {"ambientes": 3, "bathrooms": 2, "area": 140, "zona": "Buenos Aires Interior", "ciudad": "lujan"},
]


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_artifacts():
    model = joblib.load(MODEL_PATH)
    zona_encoder = joblib.load(ZONA_ENCODER_PATH)
    ciudad_encoder = joblib.load(CIUDAD_ENCODER_PATH)
    return model, zona_encoder, ciudad_encoder


def feature_vector(data, zona_encoder, ciudad_encoder) -> list[float]:
    ambientes = float(data["ambientes"])
    bathrooms = float(data["bathrooms"])
    area = float(data["area"])
    zona_encoded = float(zona_encoder.transform([data["zona"]])[0])
    ciudad_encoded = float(ciudad_encoder.transform([data["ciudad"]])[0])
    ambientes_por_m2 = ambientes / area if area > 0 else 0.0
    baños_por_ambiente = bathrooms / ambientes if ambientes > 0 else 0.0
    return [
        ambientes,
        bathrooms,
        area,
        ambientes_por_m2,
        baños_por_ambiente,
        zona_encoded,
        ciudad_encoded,
    ]


def tree_predictions(model, tree_indices, features) -> list[float]:
    row = np.asarray([features], dtype=np.float64)
    return [float(model.estimators_[index].predict(row)[0]) for index in tree_indices]


def choose_trees(model, max_bytes: int):
    counts = [int(tree.tree_.node_count) for tree in model.estimators_]
    total = len(counts)
    byte_per_node = 25

    def indices_for(n: int) -> list[int]:
        if n >= total:
            return list(range(total))
        if n == 1:
            return [0]
        return sorted({round(i * (total - 1) / (n - 1)) for i in range(n)})

    n = total
    indices = indices_for(n)
    while len(indices) > 1 and sum(counts[i] for i in indices) * byte_per_node > max_bytes:
        n -= 1
        indices = indices_for(n)

    size = sum(counts[i] for i in indices) * byte_per_node
    if size > max_bytes:
        raise SystemExit(
            f"No se puede exportar el modelo por debajo de {max_bytes / 1024 / 1024:.1f} MB"
        )
    return indices, counts


def build_export(model, tree_indices):
    feature_parts = []
    left_parts = []
    right_parts = []
    threshold_parts = []
    value_parts = []
    tree_offsets = [0]

    for tree_index in tree_indices:
        tree = model.estimators_[tree_index].tree_
        base = tree_offsets[-1]
        node_count = int(tree.node_count)

        left = tree.children_left.astype(np.int32, copy=True)
        right = tree.children_right.astype(np.int32, copy=True)
        internal = left != -1
        left[internal] += base
        right[internal] += base

        feature = tree.feature.astype(np.uint8, copy=True)
        feature[~internal] = 255

        threshold = np.where(internal, tree.threshold, 0.0).astype(np.float64)
        value = tree.value[:, 0, 0].astype(np.float64, copy=True)

        feature_parts.append(feature)
        left_parts.append(left)
        right_parts.append(right)
        threshold_parts.append(threshold)
        value_parts.append(value)
        tree_offsets.append(base + node_count)

    features = np.concatenate(feature_parts).astype("<u1", copy=False)
    left = np.concatenate(left_parts).astype("<i4", copy=False)
    right = np.concatenate(right_parts).astype("<i4", copy=False)
    thresholds = np.concatenate(threshold_parts).astype("<f8", copy=False)
    values = np.concatenate(value_parts).astype("<f8", copy=False)

    sections = {}
    offset = 0
    for name, array, dtype in [
        ("feature", features, "uint8"),
        ("left", left, "int32"),
        ("right", right, "int32"),
        ("threshold", thresholds, "float64"),
        ("value", values, "float64"),
    ]:
        payload = array.tobytes()
        sections[name] = {"offset": offset, "length": int(array.size), "dtype": dtype}
        offset += len(payload)

    binary = b"".join(
        [
            features.tobytes(),
            left.tobytes(),
            right.tobytes(),
            thresholds.tobytes(),
            values.tobytes(),
        ]
    )
    return binary, sections, tree_offsets, int(features.size)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-mb", type=float, default=20.0)
    args = parser.parse_args()

    max_mb = min(args.max_mb, 24.0)
    max_bytes = int(max_mb * 1024 * 1024)

    model, zona_encoder, ciudad_encoder = load_artifacts()
    tree_indices, counts = choose_trees(model, max_bytes)
    binary, sections, tree_offsets, n_nodes = build_export(model, tree_indices)

    if len(binary) > max_bytes:
        raise SystemExit(
            f"El binario pesa {len(binary) / 1024 / 1024:.2f} MB y el límite es {max_mb:.1f} MB"
        )

    fixtures = []
    for data in FIXTURE_INPUTS:
        features = feature_vector(data, zona_encoder, ciudad_encoder)
        predictions = tree_predictions(model, tree_indices, features)
        fixtures.append(
            {
                "input": data,
                "features": features,
                "expected_price": float(np.mean(predictions)),
            }
        )

    metadata = {
        "format_version": 1,
        "model_name": "oikos-rf-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_model": "src/models/modelo_general.pkl",
        "source_sha256": fingerprint(MODEL_PATH),
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "model_type": type(model).__name__,
        "target": "precio",
        "currency": "USD",
        "n_features": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
        "n_trees_total": len(model.estimators_),
        "n_trees": len(tree_indices),
        "tree_indices": tree_indices,
        "tree_node_counts": [counts[i] for i in tree_indices],
        "n_nodes": n_nodes,
        "tree_node_offsets": tree_offsets,
        "sections": sections,
        "zona_classes": [str(value) for value in zona_encoder.classes_],
        "ciudad_classes": [str(value) for value in ciudad_encoder.classes_],
        "binary_bytes": len(binary),
        "binary_sha256": hashlib.sha256(binary).hexdigest(),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_BIN.write_bytes(binary)
    OUTPUT_JSON.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    FIXTURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURES_PATH.write_text(
        json.dumps(
            {
                "model_name": metadata["model_name"],
                "n_trees": metadata["n_trees"],
                "feature_names": FEATURE_NAMES,
                "cases": fixtures,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Modelo: {metadata['model_type']}")
    print(f"Árboles: {metadata['n_trees']}/{metadata['n_trees_total']}")
    print(f"Nodos: {n_nodes:,}")
    print(f"Binario: {OUTPUT_BIN} ({len(binary) / 1024 / 1024:.2f} MB)")
    print(f"Metadata: {OUTPUT_JSON}")
    print(f"Fixtures: {FIXTURES_PATH}")


if __name__ == "__main__":
    main()
