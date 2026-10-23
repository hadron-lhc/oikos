from __future__ import annotations

import json
import os
import sys

import joblib
import pandas as pd
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(__file__))

app = Flask(__name__, template_folder="../templates", static_folder="../static")
CORS(app)


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store"
    return response


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "modelo_general_v2.pkl")
PROPERTY_ENCODER_PATH = os.path.join(
    BASE_DIR, "models", "property_type_encoder_v2.pkl"
)
LOCATION_ENCODER_PATH = os.path.join(BASE_DIR, "models", "location_encoder_v2.pkl")
CENTROIDS_PATH = os.path.join(BASE_DIR, "models", "city_centroids_v2.json")

model = None
le_property_type = None
le_location = None
city_centroids = None

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


def load_model():
    global model, le_property_type, le_location, city_centroids

    print("\n=== DEBUG INFO ===")
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"MODEL_PATH: {MODEL_PATH}")

    if not os.path.exists(MODEL_PATH):
        print(f"✗ ERROR: No se encontró el modelo en {MODEL_PATH}")
        return

    model = joblib.load(MODEL_PATH)
    le_property_type = joblib.load(PROPERTY_ENCODER_PATH)
    le_location = joblib.load(LOCATION_ENCODER_PATH)
    with open(CENTROIDS_PATH, encoding="utf-8") as handle:
        city_centroids = json.load(handle)

    print("✓ Modelo v2 cargado correctamente")
    print(f"✓ Tipos: {list(le_property_type.classes_)}")
    print(f"✓ Ubicaciones: {len(le_location.classes_)}")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/status")
def status():
    return jsonify(
        {
            "status": "ok",
            "model_loaded": model is not None,
            "encoders_loaded": le_property_type is not None
            and le_location is not None
            and city_centroids is not None,
            "model_path": MODEL_PATH,
            "model_exists": os.path.exists(MODEL_PATH),
            "property_types": (
                list(le_property_type.classes_) if le_property_type else []
            ),
            "locations": list(le_location.classes_) if le_location else [],
        }
    )


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json() or {}

        if (
            model is None
            or le_property_type is None
            or le_location is None
            or city_centroids is None
        ):
            return jsonify({"error": "Modelo no cargado. Ver logs del servidor."}), 500

        property_type = data.get("property_type", "")
        zona = data.get("zona", "")
        ciudad = data.get("ciudad", "")
        rooms = float(data.get("rooms", data.get("ambientes", 0)))
        bedrooms = float(data.get("bedrooms", 0))
        bathrooms = float(data.get("bathrooms", 0))
        area = float(data.get("area", 0))

        if not all([property_type, zona, ciudad, rooms > 0, area > 0]):
            return (
                jsonify(
                    {
                        "error": (
                            "Faltan datos obligatorios: property_type, zona, "
                            "ciudad, rooms, area"
                        )
                    }
                ),
                400,
            )

        location = f"{zona}|{ciudad}"
        if location not in city_centroids:
            return jsonify({"error": f"Ubicación desconocida: {location}"}), 400

        try:
            property_type_encoded = le_property_type.transform([property_type])[0]
            location_encoded = le_location.transform([location])[0]
        except ValueError:
            return (
                jsonify(
                    {
                        "error": "Tipo de propiedad o ubicación no reconocida",
                        "property_types": list(le_property_type.classes_),
                        "locations": list(le_location.classes_),
                    }
                ),
                400,
            )

        lat, lon = city_centroids[location]
        features = pd.DataFrame(
            [
                [
                    property_type_encoded,
                    location_encoded,
                    rooms,
                    bedrooms,
                    bathrooms,
                    area,
                    lat,
                    lon,
                    rooms / area,
                    bathrooms / rooms,
                    area / rooms,
                ]
            ],
            columns=FEATURE_NAMES,
        )

        prediction = float(model.predict(features)[0])

        return jsonify(
            {
                "predicted_price": prediction,
                "formatted_price": f"${prediction:,.2f}",
                "input_data": {
                    "property_type": property_type,
                    "zona": zona,
                    "ciudad": ciudad,
                    "rooms": rooms,
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "area": area,
                },
            }
        )

    except Exception as exc:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    load_model()
    print("\n" + "=" * 50)
    print("Servidor Flask iniciado")
    print("Estado del modelo:", "✓ OK" if model else "✗ Error")
    print("=" * 50)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
else:
    load_model()
