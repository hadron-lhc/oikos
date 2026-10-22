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
| 🔍 Data Exploration | [Streamlit](https://oikos-data-exploration.streamlit.app/)                                                     |

## 📁 Related Repositories

|                     |                                                                                |
| ------------------- | ------------------------------------------------------------------------------ |
| 🕷️ Scraper          | [oikos-scraper](https://github.com/hadron-lhc/Scraper_ML-Inmuebles)                  |
| 🔍 Data Exploration | [oikos-data-exploration](https://github.com/hadron-lhc/oikos-data-exploration) |

---

## What does it do?

A web application that allows you to draw rooms interactively and predicts the housing price using a Random Forest model trained with over 72k real properties scraped from the Argentine real estate market.

---

## Where does it get the data from?

Data was collected using a custom scraper from Mercado Libre Inmuebles, covering 38 locations across Buenos Aires, Córdoba and the Atlantic Coast.

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

| Metric           | Value   |
| ---------------- | ------- |
| R² Score         | 0.72    |
| MAE              | $59,046 |
| RMSE             | $89,477 |
| Training samples | ~68,000 |

**Top features by importance:**

- Area (63.7%)
- City (12.2%)
- Bathrooms (7.6%)
- Rooms (5.5%)
- Zone (4.6%)

---

## 🛠️ Tech Stack

| Layer    | Technology                           |
| -------- | ------------------------------------ |
| Frontend | Vanilla JavaScript, SVG Canvas, CSS3 |
| Backend  | Browser inference; Flask local       |
| ML       | Scikit-learn (Random Forest)         |
| Data     | SQLite, Pandas                       |
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

# Train model
python src/train_model_V2.py

# Run Flask locally (optional)
python src/app.py
```

### Static deployment

The browser model is exported to `static/model/` and the static site is generated in `dist/`.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements-export.txt

python scripts/export_model.py
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
│   ├── train_model_V2.py     # ML Training (v2 — 72k properties)
│   ├── analysis_db.py        # Data analysis
│   └── models/               # Saved model + encoders
├── scripts/                  # Model export and static build
├── static/                   # CSS/JS + browser model
├── templates/                # HTML
├── database/                 # SQLite DB (72k properties)
└── data/                     # Exported CSVs
```

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first.
