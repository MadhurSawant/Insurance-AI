# Explainable & Reliable Insurance Premium Prediction (UI Demo)

This version is a frontend/UI prototype built with Flask and Jinja templates. It demonstrates the intended user experience, transparent explainability flows, prediction reliability visualization, and interactive scenario testing prior to integration of the machine-learning backend.

---

## 🌟 Features

- **Customer Profile Form (`/predict`)**: Clean input interface for Age, Sex, BMI, Dependents, Smoking status, and Region with live profile preview.
- **Premium Prediction Result (`/result`)**: Display estimated premium, point estimates, and bounded uncertainty intervals `[Lower, Upper]`.
- **Explainability Demo (`/explain`)**: SHAP-style visual feature attribution demonstrating exact factor contribution weights.
- **What-If Scenario Simulator (`/whatif`)**: Interactive scenario controls comparing original customer baseline against modified health targets.
- **About Platform (`/about`)**: Architectural and conceptual overview of prediction, explainability, reliability, and What-If analysis.

---

## 🎨 Color Palette & Design System

- **Navy Blue (`#0b306b`)**: Primary brand elements, headings, primary buttons.
- **Cornflower (`#4f81b7`)**: Secondary accents, sliders, icons.
- **Freesia Accent (`#fdd8a5`)**: Highlights, demo badges, estimate focus.
- **Blue-Green / Emerald (`#16796f`)**: Success badges, savings indicators, positive impact.

---

## 🚀 Quickstart Guide

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Launch Application

```bash
python app.py
```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 📁 Project Structure

```
insurance_ui_demo/
│
├── app.py                  # Flask application & 6 core routes
├── requirements.txt        # Flask dependency
├── README.md               # Project documentation
│
├── templates/              # Jinja2 templates
│   ├── base.html           # Main layout & sidebar navigation
│   ├── landing.html        # Landing page
│   ├── predict.html        # Customer profile form
│   ├── result.html         # Premium prediction result
│   ├── explain.html        # SHAP-style explainability demo
│   ├── whatif.html         # What-If scenario simulator
│   └── about.html          # System overview
│
└── static/                 # Static assets
    ├── css/
    │   └── style.css       # Custom design system CSS
    │
    └── js/
        ├── main.js         # Navigation, toasts, loading overlay
        └── demo.js         # Demo calculations & chart initializations
```
