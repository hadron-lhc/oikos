from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import joblib
import numpy as np
import os
import sys

# Agregar directorio src al path
sys.path.insert(0, os.path.dirname(__file__))

app = Flask(__name__, template_folder="../templates", static_folder="../static")
CORS(app)


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store"
    return response


# Usar ruta absoluta para el modelo y encoders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "modelo_general.pkl")
ZONE_ENCODER_PATH = os.path.join(BASE_DIR, "models", "zona_encoder.pkl")
CITY_ENCODER_PATH = os.path.join(BASE_DIR, "models", "ciudad_encoder.pkl")

model = None
le_zona = None
le_ciudad = None


def load_model():
    global model, le_zona, le_ciudad
    print("\n=== DEBUG INFO ===")
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"MODEL_PATH: {MODEL_PATH}")
    print(f"ZONE_ENCODER_PATH: {ZONE_ENCODER_PATH}")
    print(f"CITY_ENCODER_PATH: {CITY_ENCODER_PATH}")

    # Listar archivos en la carpeta models
    models_dir = os.path.join(BASE_DIR, "models")
    if os.path.exists(models_dir):
        print(f"\nArchivos en {models_dir}:")
        print(os.listdir(models_dir))
    else:
        print(f"¡La carpeta {models_dir} NO EXISTE!")
        return

    # Cargar modelo
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            print("✓ Modelo cargado correctamente")
        except Exception as e:
            print(f"✗ ERROR al cargar modelo: {e}")
    else:
        print(f"✗ ERROR: No se encontró el modelo en {MODEL_PATH}")

    # Cargar encoders
    if os.path.exists(ZONE_ENCODER_PATH):
        try:
            le_zona = joblib.load(ZONE_ENCODER_PATH)
            print(
                f"✓ Zone encoder cargado. Zonas disponibles: {list(le_zona.classes_)}"
            )
        except Exception as e:
            print(f"✗ ERROR al cargar zona encoder: {e}")
    else:
        print(f"✗ ERROR: No se encontró zona_encoder en {ZONE_ENCODER_PATH}")

    if os.path.exists(CITY_ENCODER_PATH):
        try:
            le_ciudad = joblib.load(CITY_ENCODER_PATH)
            print(
                f"✓ City encoder cargado. Ciudades disponibles: {list(le_ciudad.classes_)}"
            )
        except Exception as e:
            print(f"✗ ERROR al cargar ciudad encoder: {e}")
    else:
        print(f"✗ ERROR: No se encontró ciudad_encoder en {CITY_ENCODER_PATH}")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/status")
def status():
    return jsonify(
        {
            "status": "ok",
            "model_loaded": model is not None,
            "encoders_loaded": le_zona is not None and le_ciudad is not None,
            "model_path": MODEL_PATH,
            "model_exists": os.path.exists(MODEL_PATH),
            "zonas_available": list(le_zona.classes_) if le_zona else [],
            "cities_available": list(le_ciudad.classes_) if le_ciudad else [],
        }
    )


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        print("\n--- Nueva predicción ---")
        print(f"Datos recibidos: {data}")

        if model is None or le_zona is None or le_ciudad is None:
            return jsonify({"error": "Modelo no cargado. Ver logs del servidor."}), 500

        # Extraer datos
        ambientes = data.get("ambientes", 0)
        bathrooms = data.get("bathrooms", 0)
        area = data.get("area", 0)
        zona = data.get("zona", "")
        ciudad = data.get("ciudad", "")

        # Validar datos obligatorios
        if not all([ambientes, area, zona, ciudad]):
            return jsonify(
                {"error": "Faltan datos obligatorios: ambientes, area, zona, ciudad"}
            ), 400

        print(f"Ambientes: {ambientes}, Bathrooms: {bathrooms}, Area: {area}")
        print(f"Zona: {zona}, Ciudad: {ciudad}")

        # Codificar zona y ciudad
        try:
            zona_encoded = le_zona.transform([zona])[0]
            ciudad_encoded = le_ciudad.transform([ciudad])[0]
        except ValueError as e:
            available_zonas = list(le_zona.classes_)
            available_ciudades = list(le_ciudad.classes_)
            error_msg = f"Zona o ciudad no reconocida.\nZonas: {available_zonas}\nCiudades: {available_ciudades}"
            return jsonify({"error": error_msg}), 400

        # Features en el orden correcto
        ambientes_por_m2 = ambientes / area
        baños_por_ambiente = bathrooms / ambientes if ambientes > 0 else 0

        features = np.array(
            [
                [
                    ambientes,
                    bathrooms,
                    area,
                    ambientes_por_m2,
                    baños_por_ambiente,
                    zona_encoded,
                    ciudad_encoded,
                ]
            ]
        )
        print(f"Features para predicción: {features[0]}")

        prediction = model.predict(features)[0]
        formatted_price = f"${prediction:,.2f}"

        return jsonify(
            {
                "predicted_price": float(prediction),
                "formatted_price": formatted_price,
                "input_data": {
                    "ambientes": ambientes,
                    "bathrooms": bathrooms,
                    "area": area,
                    "zona": zona,
                    "ciudad": ciudad,
                },
            }
        )

    except Exception as e:
        print(f"Error en predicción: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    load_model()
    print("\n" + "=" * 50)
    print("Servidor Flask iniciado")
    print("Estado del modelo:", "✓ OK" if model else "✗ Error")
    print("Estado de encoders:", "✓ OK" if (le_zona and le_ciudad) else "✗ Error")
    print("=" * 50)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
else:
    # Cuando Gunicorn importa la app
    load_model()
