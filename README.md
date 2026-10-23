# 🏠 Oikos — House Price Predictor

Design your house floor plan and get an instant price prediction using Machine Learning.

---

## ![principal](./images/oikos-principal.png)

---

## 🔗 Links

|                     |                                                                                                                |
| ------------------- | -------------------------------------------------------------------------------------------------------------- |
| 🌐 Web App          | [oikos.valentingonzalezdaumes.workers.dev](https://oikos.valentingonzalezdaumes.workers.dev/)                  |
| 📊 Market Dashboard | [Looker Studio](https://lookerstudio.google.com/u/0/reporting/aac5fa4f-ba3a-443a-85f6-aade78be0318/page/78DsF) |

---

## What does it do?

A web application that allows you to draw rooms interactively and predicts the housing price using a Random Forest model trained on historical Argentine real estate market data.

---

## Data & limitations

Version 2 was trained on historical Argentine real estate market data ([Properati Listings Dataset](https://www.kaggle.com/datasets/jluza92/argentina-properati-listings-dataset-20202021), 2020–2021), licensed under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Predictions are indicative estimates, not appraisals, and should not be used as the sole basis for a real estate decision.

The model covers CABA and GBA (North, West and South) for houses, apartments and PH properties.

---

## How to use

1. **Draw rooms** on the interactive canvas
2. **Label each space** (bedroom, kitchen, bathroom, etc.)
3. **Move, scale or delete** rooms as needed

![blueprint](./images/blueprint.png)

1. **Complete the form** — total area, zone and city

![additional](./images/additional-information.png)

1. **Get the price** — click "Calculate Value"

![show-price](./images/show_results.png)

The production site runs inference directly in the browser, so the prediction does not depend on a Python server.

---

## 🤖 Model Performance

| Metric        | Value    |
| ------------- | -------- |
| R² Score      | 0.82     |
| MAE           | $50,379  |
| RMSE          | $104,982 |
| Training rows | 119,461  |
| Test rows     | 16,981   |

**Top features by importance:**

- Area (52.7%)
- Location (9.9%)
- Longitude (9.6%)
- Latitude (9.2%)
- Bathrooms (9.1%)

---

## 🛠️ Tech Stack

| Layer    | Technology                           |
| -------- | ------------------------------------ |
| Frontend | Vanilla JavaScript, SVG Canvas, CSS3 |
| Backend  | Browser inference; Flask local       |
| ML       | Scikit-learn (Random Forest)         |
| Data     | CSV, Pandas                          |
| Deploy   | Cloudflare Workers (static assets)   |

---

## Local Installation

```bash
# Clone
git clone https://github.com/hadron-lhc/oikos.git
cd oikos

# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r src/requirements.txt

# Download, prepare data and train model
python scripts/data_v2/download_properati.py
python scripts/data_v2/prepare_properati.py
python src/train_model_v3.py

# Run Flask locally (optional)
python src/app.py
```

### Static deployment

The browser model is exported to `static/model/` and the static site is generated in `dist/`.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements-export.txt

python scripts/export_model_v2.py
python scripts/build_site.py
python -m http.server 8000 -d dist
```

Open `http://localhost:8000`. The deploy build only needs Python's standard library:

```bash
python scripts/build_site.py
```

---

## 📁 Structure

```
├── src/
│   ├── app.py                # Flask API (local)
│   ├── train_model_v3.py     # ML Training (v2 — Properati 2020–2021)
│   ├── analysis_db.py        # Data analysis
│   └── models/               # Saved model + encoders
├── scripts/                  # Model export, static build and data pipeline
├── static/                   # CSS/JS + browser model
├── templates/                # HTML
└── data/                     # Local datasets and model artifacts (ignored)
```

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first.
