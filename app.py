"""
EcoPackAI — Flask Backend API with Authentication
Endpoints:
  GET  /                        -> Home page (login required)
  GET  /dashboard               -> BI Dashboard (login required)
  GET  /login                   -> Login page
  POST /login                   -> Process login
  GET  /signup                  -> Signup page
  POST /signup                  -> Process signup
  GET  /logout                  -> Logout
  POST /api/recommend           -> AI packaging recommendation
  GET  /api/materials           -> All materials summary
  GET  /api/dashboard-data      -> Analytics data for charts
  GET  /api/model-metrics       -> ML model performance metrics
  POST /api/history/save        -> Save prediction to server history
  GET  /api/history             -> Get user's server-side history
  DELETE /api/history/clear     -> Clear user's history
  POST /api/export/pdf          -> Export sustainability report as PDF
  POST /api/export/excel        -> Export sustainability report as Excel
"""

import os
import io
from flask import (
    Flask, request, jsonify, render_template,
    send_file, redirect, url_for, flash
)
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
import pandas as pd

from utils.ml_models import recommend, load_models
from utils.data_preparation import load_and_enhance
from utils.db import (
    init_db, get_user_by_email, get_user_by_id,
    create_user, verify_password,
    save_prediction, get_user_history, clear_user_history
)

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ecopackai-dev-secret-2024")

# ── Flask-Login setup ──────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "login_page"
login_manager.login_message = "Please log in to use EcoPackAI."
login_manager.login_message_category = "info"


class User(UserMixin):
    """Thin wrapper around a db row to satisfy Flask-Login."""
    def __init__(self, row):
        self.id       = row["id"]
        self.username = row["username"]
        self.email    = row["email"]

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    row = get_user_by_id(user_id)
    return User(row) if row else None


# Initialise DB on startup
init_db()

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "processed_dataset.csv")


def get_df():
    if os.path.exists(DATA_PATH):
        return pd.read_csv(DATA_PATH)
    df = load_and_enhance()
    df.to_csv(DATA_PATH, index=False)
    return df


# ── Auth Pages ────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))
        user_row = get_user_by_email(email)
        if user_row and verify_password(user_row, password):
            login_user(User(user_row), remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        flash("Invalid email or password. Please try again.", "error")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        # Validation
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            try:
                uid = create_user(username, email, password)
                row = get_user_by_id(uid)
                login_user(User(row))
                flash(f"Welcome, {username}! Your account has been created.", "success")
                return redirect(url_for("index"))
            except Exception:
                flash("An account with that email or username already exists.", "error")
    return render_template("signup.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_page"))


# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return render_template("index.html", username=current_user.username)


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=current_user.username)


# ── API: Recommend ─────────────────────────────────────────────────────────────
@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    data = request.get_json()
    required = [
        "product_weight_g",
        "material_type",
        "fragility",
        "recyclable",
        "transport_mode",
        "product_category",
    ]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    try:
        results = recommend(
            product_weight_g=int(data["product_weight_g"]),
            material_type=data["material_type"],
            fragility=data["fragility"],
            recyclable=data["recyclable"],
            transport_mode=data["transport_mode"],
            product_category=data["product_category"],
            top_n=int(data.get("top_n", 3)),
        )
        return jsonify({"status": "success", "recommendations": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Materials summary ─────────────────────────────────────────────────────
@app.route("/api/materials")
def api_materials():
    df = get_df()
    summary = (
        df.groupby("Material_Type")
        .agg(
            count=("Product_ID", "count"),
            avg_co2=("LCA_Emission_kgCO2", "mean"),
            avg_cost=("Cost_per_unit", "mean"),
            avg_biodeg=("Biodegradability_Score", "mean"),
            avg_suitability=("Material_Suitability_Score", "mean"),
        )
        .reset_index()
        .round(3)
        .to_dict(orient="records")
    )
    return jsonify({"status": "success", "materials": summary})


# ── API: Dashboard data ────────────────────────────────────────────────────────
@app.route("/api/dashboard-data")
def api_dashboard():
    df = get_df()

    # CO2 by packaging option
    co2_by_pkg = (
        df.groupby("Packaging_Option")["LCA_Emission_kgCO2"]
        .mean()
        .round(3)
        .reset_index()
        .rename(columns={"LCA_Emission_kgCO2": "avg_co2"})
        .to_dict(orient="records")
    )

    # Cost by packaging option
    cost_by_pkg = (
        df.groupby("Packaging_Option")["Cost_per_unit"]
        .mean()
        .round(3)
        .reset_index()
        .rename(columns={"Cost_per_unit": "avg_cost"})
        .to_dict(orient="records")
    )

    # Recyclability by material
    recyc = (
        df.groupby("Material_Type")["Recyclable_Binary"]
        .mean()
        .mul(100)
        .round(1)
        .reset_index()
        .rename(columns={"Recyclable_Binary": "recyclable_pct"})
        .to_dict(orient="records")
    )

    # Transport mode distribution
    transport = df["Transport_Mode"].value_counts().reset_index()
    transport.columns = ["mode", "count"]
    transport = transport.to_dict(orient="records")

    # Category distribution
    category = df["Product_Category"].value_counts().reset_index()
    category.columns = ["category", "count"]
    category = category.to_dict(orient="records")

    # Biodegradability by material
    biodeg = (
        df.groupby("Material_Type")["Biodegradability_Score"]
        .mean()
        .round(1)
        .reset_index()
        .to_dict(orient="records")
    )

    # Summary stats
    avg_plastic_co2 = float(
        df[df["Material_Type"] == "Plastic"]["LCA_Emission_kgCO2"].mean()
    )
    avg_bio_co2 = float(
        df[df["Material_Type"] == "Bioplastic"]["LCA_Emission_kgCO2"].mean()
    )
    co2_saved_pct = round((avg_plastic_co2 - avg_bio_co2) / avg_plastic_co2 * 100, 1)

    stats = {
        "total_products": int(len(df)),
        "total_materials": int(df["Material_Type"].nunique()),
        "total_packaging_types": int(df["Packaging_Option"].nunique()),
        "avg_co2": round(float(df["LCA_Emission_kgCO2"].mean()), 3),
        "avg_cost": round(float(df["Cost_per_unit"].mean()), 2),
        "co2_savings_vs_plastic": co2_saved_pct,
        "recyclable_pct": round(float(df["Recyclable_Binary"].mean() * 100), 1),
    }

    return jsonify(
        {
            "status": "success",
            "stats": stats,
            "co2_by_packaging": co2_by_pkg,
            "cost_by_packaging": cost_by_pkg,
            "recyclability": recyc,
            "transport_distribution": transport,
            "category_distribution": category,
            "biodegradability": biodeg,
        }
    )


# ── API: Model metrics ─────────────────────────────────────────────────────────
@app.route("/api/model-metrics")
def api_metrics():
    arts = load_models()
    return jsonify({"status": "success", "metrics": arts["metrics"]})
# ── API: Prediction History ───────────────────────────────────────────────────
@app.route("/api/history/save", methods=["POST"])
@login_required
def api_history_save():
    try:
        data = request.get_json()
        profile = data.get("profile", {})
        recs = data.get("recommendations", [])
        if not profile or not recs:
            return jsonify({"error": "Profile and recommendations are required."}), 400
        save_prediction(current_user.id, profile, recs)
        return jsonify({"status": "success", "message": "Prediction saved successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
@login_required
def api_get_history():
    try:
        history = get_user_history(current_user.id)
        return jsonify({"status": "success", "history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history/clear", methods=["DELETE"])
@login_required
def api_clear_history():
    try:
        clear_user_history(current_user.id)
        return jsonify({"status": "success", "message": "History cleared successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Export Excel ──────────────────────────────────────────────────────────
@app.route("/api/export/excel", methods=["POST"])
def export_excel():
    data = request.get_json()
    recs = data.get("recommendations", [])
    profile = data.get("profile", {})

    df_rec = pd.DataFrame(recs)
    df_profile = pd.DataFrame([profile])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_profile.to_excel(writer, sheet_name="Product Profile", index=False)
        df_rec.to_excel(writer, sheet_name="Recommendations", index=False)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="ecopackai_report.xlsx",
    )


# ── API: Export PDF ────────────────────────────────────────────────────────────
@app.route("/api/export/pdf", methods=["POST"])
def export_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.lib.units import cm
    except ImportError:
        return jsonify({"error": "reportlab not installed"}), 500

    data = request.get_json()
    recs = data.get("recommendations", [])
    profile = data.get("profile", {})

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("EcoPackAI — Sustainability Report", styles["Title"]))
    story.append(Spacer(1, 0.4 * cm))

    # Profile section
    story.append(Paragraph("Product Profile", styles["Heading2"]))
    pdata = [["Field", "Value"]] + [
        [k.replace("_", " ").title(), str(v)] for k, v in profile.items()
    ]
    pt = Table(pdata, colWidths=[6 * cm, 10 * cm])
    pt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D9E75")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F0F9F5")],
                ),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(pt)
    story.append(Spacer(1, 0.5 * cm))

    # Recommendations section
    story.append(Paragraph("AI Packaging Recommendations", styles["Heading2"]))
    if recs:
        headers = [
            "Rank",
            "Packaging Option",
            "Confidence %",
            "Cost (USD)",
            "CO₂ (kg)",
            "Suitability",
        ]
        rdata = [headers] + [
            [
                r.get("rank", ""),
                r.get("packaging_option", ""),
                f"{r.get('confidence', 0)}%",
                f"${r.get('predicted_cost_usd', 0)}",
                r.get("predicted_co2_kg", 0),
                r.get("suitability_score", 0),
            ]
            for r in recs
        ]
        rt = Table(
            rdata, colWidths=[1.5 * cm, 5 * cm, 3 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm]
        )
        rt.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D9E75")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F0F9F5")],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(rt)

    doc.build(story)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="ecopackai_report.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
