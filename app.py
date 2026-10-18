import os
import hashlib

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session

from whatifanalysis import InsuranceWhatIfAnalyzer
from ExplainAI import InsuranceExplainAI


# ============================================================
# APPLICATION SETUP
# ============================================================

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "insurance-ai-secret-key"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "artifacts", "model.pkl")

SHAP_DIR = os.path.join(BASE_DIR, "static", "images", "shap")
os.makedirs(SHAP_DIR, exist_ok=True)


# ============================================================
# LOAD MODEL AND EXPLAINAI
# ============================================================

MODEL_LOAD_ERROR = None
SHAP_LOAD_ERROR = None

try:
    analyzer = InsuranceWhatIfAnalyzer(MODEL_PATH)
except Exception as exc:
    analyzer = None
    MODEL_LOAD_ERROR = f"{type(exc).__name__}: {exc}"
    app.logger.exception("Failed to load InsuranceWhatIfAnalyzer: %s", exc)

try:
    explain_ai = InsuranceExplainAI(MODEL_PATH)
except Exception as exc:
    explain_ai = None
    SHAP_LOAD_ERROR = f"{type(exc).__name__}: {exc}"
    app.logger.exception("Failed to load InsuranceExplainAI: %s", exc)


# ============================================================
# PATIENT SETTINGS
# ============================================================

DEFAULT_PATIENT = {
    "age": 35,
    "sex": "male",
    "bmi": 27.0,
    "children": 2,
    "smoker": "no",
    "region": "southeast",
}

VALID_SEX = {"male", "female"}
VALID_SMOKER = {"yes", "no"}
VALID_REGIONS = {
    "southwest",
    "southeast",
    "northwest",
    "northeast",
}


# ============================================================
# HELPERS
# ============================================================

def parse_patient_form(source, allow_defaults=False):
    """
    Read, normalize, and validate patient data from request.form/request.args/dict.
    Supports common frontend aliases (smoking/smoker, gender/sex, child/children, BMI/bmi),
    normalizes case and presentation strings, and validates data types and ranges.
    """
    if source is None:
        source = {}

    def get_first(keys, default=None):
        if hasattr(source, "get"):
            for k in keys:
                val = source.get(k)
                if val is not None and str(val).strip() != "":
                    return val
        elif isinstance(source, dict):
            for k in keys:
                if k in source and source[k] is not None and str(source[k]).strip() != "":
                    return source[k]
        return default

    # 1. Age
    raw_age = get_first(["age"], DEFAULT_PATIENT["age"] if allow_defaults else None)
    if raw_age is None:
        raise ValueError("Age is required.")
    try:
        age = int(raw_age)
    except (TypeError, ValueError) as exc:
        raise ValueError("Age must be a valid integer.") from exc

    if not 18 <= age <= 100:
        raise ValueError("Age must be between 18 and 100.")

    # 2. BMI
    raw_bmi = get_first(["bmi", "BMI"], DEFAULT_PATIENT["bmi"] if allow_defaults else None)
    if raw_bmi is None:
        raise ValueError("BMI is required.")
    try:
        bmi = float(raw_bmi)
    except (TypeError, ValueError) as exc:
        raise ValueError("BMI must be a valid numeric value.") from exc

    if not 10.0 <= bmi <= 80.0:
        raise ValueError("BMI must be between 10 and 80.")

    # 3. Children
    raw_children = get_first(["children", "child", "dependents"], DEFAULT_PATIENT["children"] if allow_defaults else None)
    if raw_children is None:
        raise ValueError("Number of children is required.")
    try:
        children = int(raw_children)
    except (TypeError, ValueError) as exc:
        raise ValueError("Children must be a valid integer.") from exc

    if not 0 <= children <= 20:
        raise ValueError("Children must be between 0 and 20.")

    # 4. Sex / Gender
    raw_sex = get_first(["sex", "gender"], DEFAULT_PATIENT["sex"] if allow_defaults else None)
    if raw_sex is None:
        raise ValueError("Sex is required.")
    sex_str = str(raw_sex).strip().lower()
    if sex_str in ("male", "m"):
        sex = "male"
    elif sex_str in ("female", "f"):
        sex = "female"
    else:
        raise ValueError("Sex must be male or female.")

    # 5. Smoker / Smoking
    raw_smoker = get_first(["smoker", "smoking", "smoker_status"], DEFAULT_PATIENT["smoker"] if allow_defaults else None)
    if raw_smoker is None:
        raise ValueError("Smoking status is required.")
    smoker_str = str(raw_smoker).strip().lower()
    if smoker_str in ("yes", "y", "true", "1", "smoker"):
        smoker = "yes"
    elif smoker_str in ("no", "n", "false", "0", "non-smoker", "non smoker", "nonsmoker"):
        smoker = "no"
    else:
        raise ValueError("Smoker must be yes or no.")

    # 6. Region
    raw_region = get_first(["region"], DEFAULT_PATIENT["region"] if allow_defaults else None)
    if raw_region is None:
        raise ValueError("Region is required.")
    region = str(raw_region).strip().lower()
    if region not in VALID_REGIONS:
        raise ValueError("Invalid region. Must be northeast, northwest, southeast, or southwest.")

    return {
        "age": age,
        "sex": sex,
        "bmi": round(bmi, 2),
        "children": children,
        "smoker": smoker,
        "region": region,
    }


def format_prediction(result):
    """Make model output easy to use in Jinja templates."""

    prediction = float(result["prediction"])
    uncertainty = float(result.get("uncertainty", 0.0))

    lower_value = result.get("lower_95", result.get("lower"))
    upper_value = result.get("upper_95", result.get("upper"))

    lower = max(0.0, float(
        lower_value
        if lower_value is not None
        else prediction - 1.96 * uncertainty
    ))

    upper = float(
        upper_value
        if upper_value is not None
        else prediction + 1.96 * uncertainty
    )

    return {
        "prediction": prediction,
        "premium": prediction,
        "uncertainty": uncertainty,
        "lower_95": lower,
        "upper_95": upper,
        "lower": lower,
        "upper": upper,
        "confidence": 95,
        "range_width": max(0.0, upper - lower),
        "interval": f"₹{lower:,.2f} - ₹{upper:,.2f}",
    }


def patient_hash(patient):
    raw = "|".join(
        f"{key}={patient[key]}"
        for key in sorted(patient)
    )
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def get_shap_explanation(patient):
    if explain_ai is None:
        return None

    try:
        return explain_ai.explain_patient(patient)
    except Exception:
        app.logger.exception("SHAP explanation failed")
        return None


def generate_shap_waterfall(patient):
    if explain_ai is None:
        return None

    filename = f"waterfall_{patient_hash(patient)}.png"
    output_path = os.path.join(SHAP_DIR, filename)

    try:
        if not os.path.exists(output_path):
            explain_ai.save_waterfall_plot(
                patient,
                output_path
            )

        return url_for(
            "static",
            filename=f"images/shap/{filename}"
        )

    except Exception:
        app.logger.exception("SHAP waterfall generation failed")
        return None


def render_home():
    """
    Render the home page.

    Your project contains both index.html and landing.html.
    landing.html is preferred because it exists in the current
    templates folder shown in the uploaded project.
    """

    landing_path = os.path.join(
        BASE_DIR,
        "templates",
        "landing.html"
    )

    if os.path.exists(landing_path):
        template = "landing.html"
    else:
        template = "index.html"

    return render_template(
        template,
        model_loaded=(analyzer is not None),
        shap_loaded=(explain_ai is not None),
        model_error=MODEL_LOAD_ERROR,
        shap_error=SHAP_LOAD_ERROR,
    )


# ============================================================
# HOME / LANDING
# ============================================================

@app.route("/", endpoint="home")
@app.route("/index", endpoint="index")
@app.route("/landing", endpoint="landing")
def home():
    return render_home()


# ============================================================
# PREDICTION
# ============================================================

@app.route("/predict", methods=["GET", "POST"], endpoint="predict")
def predict():

    if analyzer is None:
        flash(
            "The XGBoost model could not be loaded. "
            "Please check artifacts/model.pkl.",
            "danger"
        )

        return render_template(
            "predict.html",
            patient=DEFAULT_PATIENT,
            model_loaded=False,
            model_error=MODEL_LOAD_ERROR,
        )

    if request.method == "GET":
        patient_data = None
        if request.args:
            try:
                patient_data = parse_patient_form(request.args, allow_defaults=True)
            except Exception:
                patient_data = None
        if not patient_data:
            patient_data = session.get("patient", DEFAULT_PATIENT)

        return render_template(
            "predict.html",
            patient=patient_data,
            model_loaded=True,
            model_error=None,
        )

    try:
        patient = parse_patient_form(request.form)

        # Real XGBoost prediction
        raw_prediction = analyzer.predict(patient)
        prediction = format_prediction(raw_prediction)

        # Save to session so other pages synchronize with this customer profile
        session["patient"] = patient
        session["prediction"] = prediction

        # Real SHAP explanation
        shap_explanation = get_shap_explanation(patient)

        if shap_explanation and shap_explanation.get("top_factors"):
            factors = shap_explanation.get("top_factors", [])
            base_value = shap_explanation.get("base_value")
        elif analyzer:
            factors = analyzer.explain_prediction(patient)
            base_value = None
        else:
            factors = []
            base_value = None

        prediction["factors"] = factors
        shap_plot = generate_shap_waterfall(patient)

        return render_template(
            "result.html",
            patient=patient,
            prediction=prediction,
            factors=factors,
            shap_explanation=shap_explanation,
            shap_plot=shap_plot,
            base_value=base_value,
            model_loaded=True,
            shap_loaded=(explain_ai is not None),
            shap_error=SHAP_LOAD_ERROR,
        )

    except ValueError as exc:
        flash(str(exc), "warning")

        return render_template(
            "predict.html",
            patient=request.form.to_dict(),
            model_loaded=True,
            model_error=None,
        )

    except Exception as exc:
        app.logger.exception("Prediction failed")

        flash(
            f"Prediction failed: {exc}",
            "danger"
        )

        return render_template(
            "predict.html",
            patient=request.form.to_dict(),
            model_loaded=True,
            model_error=str(exc),
        )


@app.route("/result", endpoint="result")
def result():
    if analyzer is None:
        flash("The XGBoost model could not be loaded.", "danger")
        return redirect(url_for("predict"))

    patient = session.get("patient", DEFAULT_PATIENT)

    try:
        raw_prediction = analyzer.predict(patient)
        prediction = format_prediction(raw_prediction)

        session["patient"] = patient
        session["prediction"] = prediction

        shap_explanation = get_shap_explanation(patient)
        if shap_explanation and shap_explanation.get("top_factors"):
            factors = shap_explanation.get("top_factors", [])
            base_value = shap_explanation.get("base_value")
        elif analyzer:
            factors = analyzer.explain_prediction(patient)
            base_value = None
        else:
            factors = []
            base_value = None

        prediction["factors"] = factors
        shap_plot = generate_shap_waterfall(patient)

        return render_template(
            "result.html",
            patient=patient,
            prediction=prediction,
            factors=factors,
            shap_explanation=shap_explanation,
            shap_plot=shap_plot,
            base_value=base_value,
            model_loaded=True,
            shap_loaded=(explain_ai is not None),
            shap_error=SHAP_LOAD_ERROR,
        )
    except Exception as exc:
        app.logger.exception("Error rendering result")
        flash(f"Could not render prediction result: {exc}", "danger")
        return redirect(url_for("predict"))


# ============================================================
# EXPLAINAI / SHAP
# ============================================================

@app.route("/explain", methods=["GET", "POST"], endpoint="explain")
def explain():

    if explain_ai is None and analyzer is None:
        flash(
            "ExplainAI/SHAP could not be loaded. "
            "Please check SHAP installation and model.pkl.",
            "danger"
        )

        return render_template(
            "explain.html",
            patient=session.get("patient", DEFAULT_PATIENT),
            prediction=session.get("prediction"),
            factors=[],
            shap_explanation=None,
            shap_plot=None,
            shap_error=SHAP_LOAD_ERROR,
        )

    source = request.form if request.method == "POST" else request.args

    try:
        if source:
            patient = parse_patient_form(source, allow_defaults=True)
        else:
            patient = session.get("patient", DEFAULT_PATIENT)

        session["patient"] = patient

        # Real model prediction for consistency
        prediction = None
        if analyzer:
            raw_prediction = analyzer.predict(patient)
            prediction = format_prediction(raw_prediction)
            session["prediction"] = prediction

        shap_explanation = get_shap_explanation(patient)

        if shap_explanation and shap_explanation.get("top_factors"):
            factors = shap_explanation.get("top_factors", [])
        elif analyzer:
            factors = analyzer.explain_prediction(patient)
        else:
            factors = []

        shap_plot = generate_shap_waterfall(patient)

        return render_template(
            "explain.html",
            patient=patient,
            prediction=prediction,
            factors=factors,
            shap_explanation=shap_explanation,
            shap_plot=shap_plot,
            shap_error=None,
        )

    except ValueError as exc:
        flash(str(exc), "warning")

        return render_template(
            "explain.html",
            patient=session.get("patient", DEFAULT_PATIENT),
            prediction=session.get("prediction"),
            factors=[],
            shap_explanation=None,
            shap_plot=None,
            shap_error=str(exc),
        )

    except Exception as exc:
        app.logger.exception("ExplainAI failed")

        flash(
            f"ExplainAI failed: {exc}",
            "danger"
        )

        return render_template(
            "explain.html",
            patient=session.get("patient", DEFAULT_PATIENT),
            prediction=session.get("prediction"),
            factors=[],
            shap_explanation=None,
            shap_plot=None,
            shap_error=str(exc),
        )


# ============================================================
# WHAT-IF ANALYSIS
# ============================================================

@app.route("/whatif", methods=["GET", "POST"], endpoint="whatif")
def whatif():

    if analyzer is None:
        flash(
            "The XGBoost model could not be loaded.",
            "danger"
        )

        return render_template(
            "whatif.html",
            patient=DEFAULT_PATIENT,
            baseline_patient=DEFAULT_PATIENT,
            scenario_patient=DEFAULT_PATIENT,
            baseline=None,
            scenario=None,
            changes=[],
            total_change=None,
            percent_change=None,
            model_error=MODEL_LOAD_ERROR,
        )

    baseline_patient = session.get("patient", DEFAULT_PATIENT)

    if request.method == "GET":
        try:
            baseline_raw = analyzer.predict(baseline_patient)
            baseline_prediction = format_prediction(baseline_raw)
        except Exception:
            baseline_prediction = None

        return render_template(
            "whatif.html",
            patient=baseline_patient,
            baseline_patient=baseline_patient,
            scenario_patient=baseline_patient,
            baseline=baseline_prediction,
            scenario=baseline_prediction,
            changes=[],
            total_change=0,
            percent_change=0.0,
        )

    try:
        # Check if custom baseline provided in form
        if "baseline_age" in request.form or "age" in request.form:
            try:
                baseline_patient = parse_patient_form(request.form, allow_defaults=True)
            except Exception:
                baseline_patient = session.get("patient", DEFAULT_PATIENT)

        # Start scenario as a copy of baseline
        scenario_patient = dict(baseline_patient)

        fields = [
            "age",
            "sex",
            "bmi",
            "children",
            "smoker",
            "region",
        ]

        # Read what-if fields
        for field in fields:
            key = f"whatif_{field}"
            value = request.form.get(key, "").strip()
            if value != "":
                scenario_patient[field] = value

        # Validate scenario
        scenario_patient = parse_patient_form(scenario_patient)

        # Compare using real model
        comparison = analyzer.compare(
            baseline_patient,
            scenario_patient
        )

        baseline_prediction = format_prediction(
            comparison["baseline"]
        )

        scenario_prediction = format_prediction(
            comparison["scenario"]
        )

        # SHAP for scenario
        shap_explanation = get_shap_explanation(
            scenario_patient
        )

        if shap_explanation:
            factors = shap_explanation.get(
                "top_factors",
                []
            )
        else:
            factors = []

        shap_plot = generate_shap_waterfall(
            scenario_patient
        )

        return render_template(
            "whatif.html",
            patient=baseline_patient,
            baseline=baseline_prediction,
            scenario=scenario_prediction,
            baseline_patient=baseline_patient,
            scenario_patient=scenario_patient,
            changes=comparison.get(
                "changes",
                []
            ),
            total_change=float(
                comparison.get(
                    "premium_change",
                    0.0
                )
            ),
            percent_change=float(
                comparison.get(
                    "percent_change",
                    0.0
                )
            ),
            factors=factors,
            shap_explanation=shap_explanation,
            shap_plot=shap_plot,
        )

    except ValueError as exc:
        flash(str(exc), "warning")

        return render_template(
            "whatif.html",
            patient=baseline_patient,
            baseline_patient=baseline_patient,
            scenario_patient=baseline_patient,
            baseline=None,
            scenario=None,
            changes=[],
            total_change=None,
            percent_change=None,
        )

    except Exception as exc:
        app.logger.exception(
            "What-if analysis failed"
        )

        flash(
            f"What-if analysis failed: {exc}",
            "danger"
        )

        return render_template(
            "whatif.html",
            patient=baseline_patient,
            baseline_patient=baseline_patient,
            scenario_patient=baseline_patient,
            baseline=None,
            scenario=None,
            changes=[],
            total_change=None,
            percent_change=None,
        )


# ============================================================
# ABOUT
# ============================================================

@app.route("/about", endpoint="about")
def about():
    return render_template(
        "about.html",
        model_loaded=(analyzer is not None),
        shap_loaded=(explain_ai is not None),
        model_error=MODEL_LOAD_ERROR,
        shap_error=SHAP_LOAD_ERROR,
    )


# ============================================================
# API
# ============================================================

@app.route("/api/health", endpoint="api_health")
def api_health():
    return jsonify({
        "status": "ok",
        "model_loaded": analyzer is not None,
        "shap_loaded": explain_ai is not None,
        "model_path": MODEL_PATH,
        "model_error": MODEL_LOAD_ERROR,
        "shap_error": SHAP_LOAD_ERROR,
    })


@app.route("/api/predict", methods=["POST"], endpoint="api_predict")
def api_predict():

    if analyzer is None:
        return jsonify({
            "success": False,
            "error": "Model is not loaded.",
            "details": MODEL_LOAD_ERROR,
        }), 500

    try:
        data = request.get_json(
            silent=True
        ) or {}

        patient = parse_patient_form(data)

        raw_prediction = analyzer.predict(
            patient
        )

        prediction = format_prediction(
            raw_prediction
        )

        return jsonify({
            "success": True,
            "patient": patient,
            "prediction": prediction,
        })

    except ValueError as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400

    except Exception as exc:
        app.logger.exception(
            "API prediction failed"
        )

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 500


@app.route("/api/explain", methods=["POST"], endpoint="api_explain")
def api_explain():

    if explain_ai is None:
        return jsonify({
            "success": False,
            "error": "ExplainAI/SHAP is not loaded.",
            "details": SHAP_LOAD_ERROR,
        }), 500

    try:
        data = request.get_json(
            silent=True
        ) or {}

        patient = parse_patient_form(data)

        explanation = explain_ai.explain_patient(
            patient
        )

        return jsonify({
            "success": True,
            "patient": patient,
            "explanation": explanation,
        })

    except ValueError as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400

    except Exception as exc:
        app.logger.exception(
            "API ExplainAI failed"
        )

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 500


@app.route("/api/whatif", methods=["POST"], endpoint="api_whatif")
def api_whatif():

    if analyzer is None:
        return jsonify({
            "success": False,
            "error": "Model is not loaded.",
            "details": MODEL_LOAD_ERROR,
        }), 500

    try:
        data = request.get_json(
            silent=True
        ) or {}

        raw_baseline = data.get("baseline")
        if raw_baseline:
            baseline = parse_patient_form(raw_baseline)
        else:
            baseline = session.get("patient", DEFAULT_PATIENT)

        raw_scenario = data.get("scenario")
        if raw_scenario:
            scenario = parse_patient_form(raw_scenario)
        else:
            scenario = dict(baseline)

        comparison = analyzer.compare(
            baseline,
            scenario
        )

        comparison["baseline_formatted"] = format_prediction(
            comparison["baseline"]
        )
        comparison["scenario_formatted"] = format_prediction(
            comparison["scenario"]
        )

        return jsonify({
            "success": True,
            "result": comparison,
        })

    except ValueError as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400

    except Exception as exc:
        app.logger.exception(
            "API What-if failed"
        )

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 500


# ============================================================
# ENDPOINT ALIASES
# ============================================================
#
# This is the important fix for:
#
# werkzeug.routing.exceptions.BuildError:
# Could not build url for endpoint ...
#
# Different HTML files sometimes use names such as:
# url_for('home')
# url_for('index')
# url_for('landing')
# url_for('predict')
# url_for('prediction')
# url_for('explain')
# url_for('whatif')
# url_for('what_if')
#
# We provide aliases so the UI does not break because of
# a small endpoint-name mismatch.
# ============================================================

app.add_url_rule(
    "/predict",
    endpoint="prediction",
    view_func=predict,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/explain",
    endpoint="explain_ai",
    view_func=explain,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/whatif",
    endpoint="what_if",
    view_func=whatif,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/",
    endpoint="landing_page",
    view_func=home,
    methods=["GET"]
)


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print(" Insurance AI - XGBoost + SHAP")
    print("=" * 60)
    print(f"Model path : {MODEL_PATH}")
    print(f"Model      : {'LOADED' if analyzer else 'ERROR'}")
    print(f"ExplainAI  : {'LOADED' if explain_ai else 'ERROR'}")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True,
    )
