# AutoWorth-AI

**Name:** Ashutosh Singh

**Internship:** MP Online AI & ML Internship

**Batch:** Batch 2

AI-powered used car valuation platform trained on a unified dataset created by combining multiple public datasets.

An AI-powered used car valuation platform trained on a unified dataset created by combining multiple publicly available Kaggle datasets. Built with Flask and a scikit-learn regression model, wrapped in a production-grade architecture: persistent prediction history (SQLite), an analytics dashboard, a REST API, PDF/CSV exports, structured request logging, environment-driven configuration, and health checks — ready for a GitHub portfolio, a resume, a college submission, or a live Render deployment.

> The trained model, its preprocessing, its feature order, and its prediction logic come entirely from the dedicated training notebook (`AutoWorth_AI_Car_Price_Model.ipynb`). Everything documented below the **Machine Learning Pipeline** section is the application layer built around that model.

**Author:** Lakshya Sahu
**Reg No:** 23BAI10250

---

## Project Overview

Given a set of car attributes (present price, kilometers driven, fuel type, seller type, transmission, ownership history, and age), AutoWorth AI returns an instant resale price estimate using a pre-trained scikit-learn regression model, selected automatically by the training notebook from five candidate algorithms based on cross-validated performance. Every prediction is persisted, timestamped, and available for search, export, and PDF reporting — turning a single-purpose ML script into a small, coherent product.

---

## Features

**Machine learning pipeline**

- Multi-source dataset integration
- Automatic dataset download (public Kaggle datasets, no credentials required)
- Data cleaning and preprocessing
- Feature engineering
- Multiple regression model comparison
- Hyperparameter tuning

**Application**

- **Instant price prediction** with client + server-side input validation
- **Rich result card** — Estimated Price, Prediction Time, Price Category, Market Value, Prediction ID, currency formatting, and a success entrance animation
- **Prediction History** — search, date-range filter, sort (latest/oldest/price high/low), pagination (configurable page size), single/bulk delete, and **CSV export**
- **Analytics Dashboard** — total predictions, today's predictions, average/highest/lowest predicted price, average car age, fuel-type distribution and a 7-day trend, rendered with Chart.js
- **Downloadable PDF reports** for any historical prediction (ReportLab)
- **REST API** (`POST /api/predict`) with proper HTTP status codes and JSON error messages
- **Health & version endpoints** (`/health`, `/version`) for uptime monitors and deployment sanity checks
- **Structured logging** — every request logs timestamp, method, path, status code, response time, client IP, and user agent; every prediction logs its own inference time; all errors are logged
- **Environment-variable-driven configuration** — no hardcoded secrets or paths; `.env` supported locally via `python-dotenv`
- **Custom "instrument cluster" UI** — Bootstrap 5 + a hand-built dark dashboard theme (Rajdhani/JetBrains Mono type, amber/teal signal accents, a gauge-style price readout), fully responsive
- **Zero external database dependency** — SQLite file + tables are created automatically on first run
- **Render-ready** — `Procfile`, `runtime.txt`, and `render.yaml` included

---

## Architecture

```
                    ┌────────────────────┐
                    │   Browser / Client  │
                    └─────────┬──────────┘
                              │ HTTP
                    ┌─────────▼──────────┐
                    │      app.py         │  routes, request logging,
                    │  (Flask entrypoint) │  error handlers
                    └───┬─────────┬──────┘
                        │         │
          ┌─────────────▼──┐   ┌─▼───────────────┐
          │  utils.py        │   │ report_generator │
          │ validation,      │   │  .py (PDF via     │
          │ formatting,      │   │  ReportLab)        │
          │ CSV export       │   └────────────────────┘
          └─────────────┬───┘
                        │
          ┌─────────────▼───────────┐        ┌──────────────┐
          │      database.py         │◄──────►│ predictions.db│ (SQLite,
          │  CRUD + statistics        │        │ auto-created) │  instance/)
          └─────────────┬────────────┘        └──────────────┘
                        │
          ┌─────────────▼───────────┐
          │  car_price_model.pkl      │  (trained by the notebook,
          │  loaded once at startup   │   unmodified by the app)
          └───────────────────────────┘

          config.py  ── environment-driven settings (paths, secrets, pagination)
          logger.py  ── rotating file + console logger, used everywhere above
```

**Design principle:** the ML model is loaded once at startup and called through a single `run_prediction()` function in `app.py` that preserves the exact feature order and `np.array` shape the notebook trained it with. No retraining, no changed preprocessing, no changed inference logic inside the app — the surrounding modules only handle validation, persistence, presentation, analytics, and reporting.

---

## Machine Learning Pipeline

The notebook `AutoWorth_AI_Car_Price_Model.ipynb` handles everything needed to produce `car_price_model.pkl`, and runs end-to-end in Google Colab with no manual downloads:

1. **Dataset download** — all four datasets (CarDekho plus three additional Kaggle datasets) via `kagglehub.dataset_download()`; since every dataset is public, no Kaggle login or API token is required
2. **Schema comparison** — every raw column is matched against a canonical feature schema using an explicit alias dictionary; datasets that don't expose the required fields are excluded and the reason is reported (never force-merged)
3. **Cleaning** — duplicate removal, missing-value handling, whitespace/case normalization, dtype correction, and removal of impossible values
4. **Standardization** — consistent categorical vocabularies across all sources (fuel type, transmission, seller type, etc.)
5. **Merging** — compatible datasets combined into a single master dataframe
6. **Feature engineering** — `Car_Age` and other candidate features
7. **Outlier detection** — IQR + Z-score combined with logical sanity limits
8. **Exploratory data analysis** — correlation heatmap, distributions, boxplots, and scatterplots with observations
9. **Model training & comparison** — Linear Regression, Decision Tree, Random Forest, Extra Trees, and Gradient Boosting, evaluated with MAE / MSE / RMSE / R² / Adjusted R² and 5-fold cross-validation
10. **Hyperparameter tuning** — `RandomizedSearchCV` on the best tree-based model
11. **Feature importance** — ranked contribution of each input to price
12. **Model export** — the final estimator is saved with plain `pickle` as `car_price_model.pkl` (no joblib, no sklearn `Pipeline`)

**Running the notebook**

1. Open `AutoWorth_AI_Car_Price_Model.ipynb` in Colab
2. Run all cells top to bottom — all four datasets are public, so `kagglehub` downloads them automatically with no Kaggle login or API token needed
3. The final cell writes `car_price_model.pkl` — copy it into the project root next to `app.py`

### Model Input Contract

The Flask application always sends features to the model in this exact order — the notebook preserves it end-to-end and the app never reorders it:

```
[Present_Price, Kms_Driven, Fuel_Type, Seller_Type, Transmission, Owner, Car_Age]
```

---

## Folder Structure

```
├── AutoWorth_AI_Car_Price_Model.ipynb  # End-to-end ML pipeline notebook
├── app.py                    # Flask routes, request/response logging, error handlers
├── config.py                 # Environment-variable-driven configuration
├── database.py                # SQLite connection handling, CRUD, statistics
├── logger.py                   # Rotating file + console logger setup
├── report_generator.py         # PDF report builder (ReportLab)
├── utils.py                     # Validation, formatting, price categorization, CSV export
├── car_price_model.pkl           # Trained model produced by the notebook
├── requirements.txt
├── Procfile                       # Render/Heroku start command
├── runtime.txt                     # Pinned Python version for Render
├── render.yaml                      # Render Blueprint config
├── .env.example                      # Documented environment variables
├── .gitignore
├── templates/
│   ├── base.html                      # Shared layout, navbar, footer
│   ├── index.html                      # Prediction form + result panel
│   ├── history.html                     # Prediction history: filter/sort/export
│   ├── dashboard.html                    # Analytics dashboard (Chart.js)
│   ├── 404.html / 500.html                # Error pages
├── static/
│   ├── css/style.css                       # Design system (CSS variables, dashboard theme)
│   └── js/main.js
├── instance/                                 # Auto-created: predictions.db, reports/
└── logs/                                       # Auto-created: app.log
```

---

## Screenshots

_Add screenshots here before publishing to your portfolio/resume:_

```
docs/screenshot-predict.png      # Prediction form + result gauge
docs/screenshot-history.png      # History table with filters
docs/screenshot-dashboard.png    # Analytics dashboard with charts
```

---

## Installation

```bash
git clone <repository-url>
cd AutoWorth AI
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env             # optional, for local overrides
python app.py
```

The app runs at `http://127.0.0.1:5000`. On first launch, `instance/predictions.db` and `logs/app.log` are created automatically.

---

## SQLite

No external database service is required. `database.py` creates `instance/predictions.db` and the `prediction_history` table automatically on startup.

**Schema:**

| Column          | Type    |
|-----------------|---------|
| id              | INTEGER (PK, autoincrement) |
| timestamp       | TEXT    |
| present_price   | REAL    |
| kms_driven      | INTEGER |
| fuel_type       | INTEGER |
| seller_type     | INTEGER |
| transmission    | INTEGER |
| owner           | INTEGER |
| car_age         | INTEGER |
| predicted_price | REAL    |

Visit `/history` to search, filter by date range, sort, paginate, delete individual/all records, export to CSV, or download a PDF report for any entry. Visit `/dashboard` for aggregate statistics and charts.

---

## REST API

### `POST /api/predict`

**Request body (JSON):**

```json
{
  "present_price": 6.5,
  "kms_driven": 45000,
  "fuel_type": 0,
  "seller_type": 0,
  "transmission": 0,
  "owner": 0,
  "car_age": 5
}
```

| Field         | Type  | Notes                                   |
|---------------|-------|------------------------------------------|
| present_price | float | Original price in Lakhs, > 0             |
| kms_driven    | int   | ≥ 0                                       |
| fuel_type     | int   | 0 = Petrol, 1 = Diesel, 2 = CNG           |
| seller_type   | int   | 0 = Dealer, 1 = Individual                |
| transmission  | int   | 0 = Manual, 1 = Automatic                 |
| owner         | int   | Number of previous owners, ≥ 0            |
| car_age       | int   | Years, 0–60                                |

**Success response — `201 Created`:**

```json
{
  "success": true,
  "id": 12,
  "predicted_price": 4.42,
  "formatted_price": "₹ 4.42 Lakhs",
  "price_category": "Mid-Range",
  "market_value": "Good Resale Value",
  "timestamp": "05 Jul 2026, 08:50 AM"
}
```

**Error responses:**

| Status | Meaning                          |
|--------|----------------------------------|
| 400    | Request body is not valid JSON   |
| 422    | JSON was valid but failed field validation (with a human-readable message) |
| 500    | Internal error during prediction |

### `GET /health`

```json
{ "status": "healthy" }
```

### `GET /version`

```json
{ "app": "AutoWorth AI", "version": "1.0.0", "python": "3.12.4", "model": "best cross-validated regressor (see notebook)" }
```

---

## Deployment on Render

**Option A — Blueprint (recommended):**

1. Push this repository to GitHub.
2. On [Render](https://render.com), choose **New +** → **Blueprint**, and point it at this repo. Render will read `render.yaml` and provision the web service automatically, generating a random `SECRET_KEY`.

**Option B — Manual Web Service:**

1. Create a **New Web Service**, connect the repo.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app` (also defined in `Procfile`)
4. Set environment variables (`SECRET_KEY`, `FLASK_ENV=production`, `FLASK_DEBUG=False`, etc. — see `.env.example`).

> Render's free-tier filesystem is ephemeral across deploys/restarts. For prediction history to persist across deploys, attach a Render Disk mounted at the project's `instance/` directory.

---

## Technologies Used

- Python 3.12, Flask 3
- scikit-learn, NumPy, pandas
- SQLite (via the standard library `sqlite3` module)
- ReportLab (PDF generation), Chart.js (dashboard charts)
- python-dotenv (environment configuration)
- Bootstrap 5 + Bootstrap Icons, custom CSS design system
- Gunicorn (production WSGI server)

---

## Future Improvements

- User authentication so history is scoped per user
- Model versioning / A-B testing of different regressors
- Chart of price-vs-age/kms scatter trends
- Persistent disk-backed storage on Render for cross-deploy history retention
- Dockerfile for containerized deployment
- Automated test suite (pytest) and CI pipeline

---

## License

This project is released under the MIT License. See `LICENSE` for details (add one before publishing publicly).

---

## Author

Lakshya Sahu
