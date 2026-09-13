import os
import json
import time
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="NutriGuide AI",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

try:
    API_KEY = st.secrets.get("GROQ_API_KEY")
except Exception:
    API_KEY = None

if not API_KEY:
    API_KEY = os.getenv("GROQ_API_KEY")

if API_KEY:
    API_KEY = API_KEY.strip()

if not API_KEY:
    st.error("🔑 Groq API key is missing.")
    st.info(
        "For Streamlit Cloud, add GROQ_API_KEY under "
        "Settings → Secrets. For local development, add it "
        "to your .env file."
    )
    st.stop()

client = Groq(api_key=API_KEY)

MODEL_NAME = "openai/gpt-oss-120b"


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "page": "home",
    "user_data": {},
    "assessment": {},
    "safety_result": {},
    "guidance": {},
    "workflow_context": {},
    "wizard_step": 0,
    "wizard_data": {},
}

for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root {
            --leaf: #087b57;
            --leaf-deep: #064e3b;
            --leaf-soft: #a7d9bc;
            --mint: #e7f5ed;
            --paper: #faf9f4;
            --ink: #183c30;
            --muted: #52675e;
            --surface: #ffffff;
            --citrus: #d99a24;
            --citrus-soft: #fff3d6;
            --citrus-ink: #80540d;
            --teal: #0f766e;
            --teal-soft: #e4f3f1;
            --alert: #b94336;
            --line: #d6e4db;
            --focus: rgba(8, 123, 87, 0.20);
            --glass: rgba(255, 255, 255, 0.94);
            color-scheme: light;
        }

        html, body, [class*="css"] { font-family: "Inter", sans-serif; }
        .stApp { background: var(--paper); color: var(--ink); }
        .stApp::before {
            content: ""; position: fixed; inset: 0; pointer-events: none;
            background-color: var(--paper);
            background-image: radial-gradient(ellipse at 0% 0%, rgba(167,217,188,.30), transparent 55%), radial-gradient(ellipse at 100% 10%, rgba(255,228,173,.24), transparent 45%);
        }
        header[data-testid="stHeader"] { background: rgba(250,249,244,.90); backdrop-filter: blur(20px); }
        #MainMenu, footer { visibility: hidden; }
        .block-container { max-width: 1180px; padding: 2.25rem 2rem 4rem; position: relative; }
        h1, h2, h3 { font-family: "Space Grotesk", sans-serif; color: var(--ink); letter-spacing: 0; }
        h1 { font-size: clamp(2rem, 4vw, 3.25rem); line-height: 1.08; font-weight: 700; }
        h2, h3 { font-weight: 600; }
        p, label, .stMarkdown { color: var(--ink); }
        hr { border-color: var(--line); margin: 1.6rem 0; }

        .brandbar { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:2rem; }
        .brand { display:flex; align-items:center; gap:.75rem; font:700 1.12rem "Space Grotesk",sans-serif; }
        .brand-mark { width:2.25rem; height:2.25rem; display:grid; place-items:center; border-radius:.75rem; background:linear-gradient(135deg,var(--leaf),var(--teal)); color:white; }
        .status-chip { display:inline-flex; align-items:center; gap:.5rem; padding:.45rem .75rem; border-radius:999px; background:var(--mint); color:var(--leaf); font-size:.78rem; font-weight:700; border:1px solid var(--line); }
        .status-chip::before { content:""; width:.42rem; height:.42rem; border-radius:50%; background:var(--leaf); }
        .eyebrow { color:var(--leaf); font-size:.76rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.7rem; }
        .lead { color:var(--muted); font-size:1.03rem; line-height:1.7; max-width:680px; }
        .glass, .feature-card, .step-card, .summary-card, .meal-card {
            background:var(--glass); border:1px solid var(--line); box-shadow:0 12px 40px rgba(6,78,59,.06); backdrop-filter:blur(18px); border-radius:16px;
        }
        .hero-panel { background:linear-gradient(120deg,#f0faf3 0%,#ffffff 65%,#fff6e3 100%); border-color:#c8dfcf; padding:clamp(1.5rem,4vw,3rem); margin-bottom:1rem; overflow:hidden; position:relative; }
        .hero-panel::after { content:""; position:absolute; width:8px; top:0; bottom:0; left:0; background:linear-gradient(180deg,var(--leaf),var(--leaf-soft),var(--citrus)); }
        .hero-grid { display:grid; grid-template-columns:1.45fr .75fr; gap:2rem; align-items:center; }
        .hero-score { background:linear-gradient(140deg,var(--leaf-deep),var(--teal)); color:white; border:1px solid rgba(255,255,255,.16); border-radius:14px; padding:1.3rem; box-shadow:0 16px 32px rgba(6,78,59,.16); }
        .hero-score strong { display:block; font:600 2.1rem "Space Grotesk",sans-serif; color:white; }
        .hero-score span { color:#d9eee4; font-size:.84rem; }
        .trust-row { display:flex; flex-wrap:wrap; gap:.65rem; margin-top:1.4rem; }
        .trust-item { padding:.5rem .7rem; border-radius:8px; background:var(--mint); color:var(--leaf); font-size:.78rem; font-weight:700; }
        .trust-item:nth-child(even) { background:var(--teal-soft); color:var(--teal); }
        .trust-item:last-child { background:var(--citrus-soft); color:var(--citrus-ink); }
        [data-testid="stColumn"]:nth-child(2) .feature-number { background:var(--teal-soft); color:var(--teal); }
        [data-testid="stColumn"]:nth-child(3) .feature-number { background:var(--citrus-soft); color:var(--citrus-ink); }
        [data-testid="stChatMessage"] { background:var(--mint); border:1px solid var(--line); border-radius:14px; }
        [data-testid="stChatInputSubmitButton"] { color:var(--leaf); }
        [data-testid="stBottom"], [data-testid="stBottom"] > div { background:var(--paper); }
        .section-heading { display:flex; align-items:end; justify-content:space-between; gap:1rem; margin:2rem 0 1rem; }
        .section-heading h2 { margin:0; font-size:1.5rem; }
        .section-heading p { margin:0; color:var(--muted); font-size:.85rem; }
        .feature-card, .step-card { min-height:190px; padding:1.35rem; }
        .feature-number { display:grid; place-items:center; width:2.25rem; height:2.25rem; border-radius:.7rem; margin-bottom:1.1rem; background:var(--mint); color:var(--leaf); font-weight:800; }
        .feature-card h3, .step-card h3 { font-size:1rem; margin:.2rem 0 .55rem; }
        .feature-card p, .step-card p { color:var(--muted); font-size:.88rem; line-height:1.6; }
        .notice { border-left:3px solid var(--citrus); background:var(--citrus-soft); padding:1rem 1.1rem; border-radius:0 12px 12px 0; color:var(--citrus-ink); font-size:.86rem; }

        div[data-testid="stMetric"] { background:var(--glass); border:1px solid var(--line); padding:1rem; border-radius:14px; box-shadow:0 8px 28px rgba(6,78,59,.05); min-height:126px; }
        div[data-testid="stMetricLabel"] { font-weight:600; color:var(--muted); }
        div[data-testid="stMetricValue"] { font-family:"Space Grotesk",sans-serif; color:var(--leaf-deep); }
        div[data-testid="stAlert"] { border-radius:12px; border-width:1px; }
        div[data-testid="stExpander"] { background:var(--surface); border:1px solid var(--line); border-radius:14px; overflow:hidden; }
        div[data-baseweb="select"] > div, div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="textarea"], [data-testid="stChatInput"] {
            border-radius:10px !important; border-color:var(--line) !important; background:var(--surface) !important; color:var(--ink) !important;
        }
        .stApp input, .stApp textarea { background:var(--surface) !important; color:var(--ink) !important; caret-color:var(--leaf); }
        .stApp input::placeholder, .stApp textarea::placeholder { color:var(--muted) !important; opacity:1; }
        div[data-baseweb="select"] span { color:var(--ink); }
        div[data-baseweb="select"] svg { color:var(--muted); }
        div[data-baseweb="select"] [data-baseweb="tag"] { background:var(--mint); color:var(--leaf-deep); border-color:var(--line); }
        [data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] [role="option"] { background:var(--surface); color:var(--ink); }
        [data-baseweb="popover"] [role="option"]:hover, [data-baseweb="popover"] [role="option"][aria-selected="true"] { background:var(--mint); color:var(--leaf-deep); }
        div[data-baseweb="select"]:focus-within > div, div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within, [data-testid="stChatInput"]:focus-within { border-color:var(--leaf) !important; box-shadow:0 0 0 3px var(--focus) !important; }
        .stApp input:focus-visible, .stApp textarea:focus-visible { outline:2px solid var(--leaf); outline-offset:2px; }
        .stApp a { color:var(--teal); }
        .stApp a:hover { color:var(--leaf-deep); }
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:var(--muted); }
        [data-testid="stNumberInput"] button { background:var(--mint); color:var(--leaf-deep); }
        [data-testid="stCheckbox"] label:has(input:checked) > span { background-color:var(--leaf); border-color:var(--leaf); }
        [data-testid="stRadio"] label:has(input:checked) > div:first-child { background-color:var(--leaf); }
        [data-testid="stCheckbox"] label:has(input:focus-visible) > span, [data-testid="stRadio"] label:has(input:focus-visible) > div:first-child { outline:2px solid var(--leaf); outline-offset:3px; }
        .stButton > button, .stDownloadButton > button { border-radius:10px; min-height:44px; font-weight:700; background:var(--surface); color:var(--leaf-deep); border-color:var(--line); transition:transform .16s ease, box-shadow .16s ease; }
        .stButton > button p, .stDownloadButton > button p { color:inherit; }
        .stButton > button:hover:not(:disabled), .stDownloadButton > button:hover:not(:disabled) { background:var(--mint); color:var(--leaf-deep); transform:translateY(-1px); box-shadow:0 8px 18px rgba(6,78,59,.12); border-color:var(--leaf); }
        .stButton > button:focus-visible, .stDownloadButton > button:focus-visible { outline:3px solid var(--leaf); outline-offset:3px; }
        .stButton > button:disabled, .stDownloadButton > button:disabled { opacity:.5; cursor:not-allowed; }
        .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] { background:linear-gradient(110deg,var(--leaf),var(--teal)); color:white; border-color:var(--leaf); box-shadow:0 6px 16px rgba(8,123,87,.16); }
        .stButton > button[kind="primary"] p, .stDownloadButton > button[kind="primary"] p { color:white; }
        .stButton > button[kind="primary"]:hover:not(:disabled), .stDownloadButton > button[kind="primary"]:hover:not(:disabled) { background:var(--leaf-deep); color:white; border-color:var(--leaf-deep); }
        .stProgress > div > div > div { background:var(--mint); }
        .stProgress > div > div > div > div { background:linear-gradient(90deg,var(--leaf),var(--teal)); }
        .stTabs [data-baseweb="tab-list"] { gap:.3rem; background:var(--mint); border-radius:12px; padding:.3rem; }
        .stTabs [data-baseweb="tab"] { border-radius:9px; padding:.55rem 1rem; color:var(--muted); }
        .stTabs [data-baseweb="tab"] p { color:inherit; }
        .stTabs [aria-selected="true"] { background:white; color:var(--leaf); }
        .stTabs [data-baseweb="tab-highlight"] { display:none; }
        .summary-card { background:linear-gradient(120deg,var(--mint),var(--surface)); padding:1.35rem; margin-bottom:1rem; }
        .summary-card h2 { margin:0 0 .35rem; font-size:1.35rem; }
        .summary-card p { margin:.2rem 0; color:var(--muted); }
        .meal-card { background:#f3faf5; padding:1rem; margin:.65rem 0; border-left:3px solid var(--leaf); font-size:.9rem; }
        .wizard-shell { background:var(--glass); border:1px solid var(--line); border-radius:16px; padding:1.3rem; margin:1rem 0 1.5rem; box-shadow:0 12px 40px rgba(6,78,59,.05); }
        .wizard-labels { display:grid; grid-template-columns:repeat(3,1fr); gap:.75rem; margin-top:.75rem; }
        .wizard-step { color:var(--muted); font-size:.78rem; font-weight:600; }
        .wizard-step.active { color:var(--leaf); }
        .wizard-step.done { color:var(--teal); }
        .app-footer { text-align:center; padding:2rem 0 .5rem; color:var(--muted); font-size:.78rem; }
        .small-note { font-size:.84rem; color:var(--muted); }

        @keyframes ng-fade { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }
        .hero-panel, div[data-testid="stMetric"] { animation:ng-fade .5s ease both; }
        @media (prefers-reduced-motion:reduce) { *, *::before, *::after { animation:none !important; transition:none !important; } }
        @media (max-width:760px) {
            .block-container { padding:1.2rem 1rem 3rem; }
            .hero-grid { grid-template-columns:1fr; }
            .brandbar { align-items:flex-start; }
            .status-chip { display:none; }
            .feature-card, .step-card { min-height:auto; }
            .wizard-labels { gap:.3rem; }
            .wizard-step { font-size:.68rem; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)



# ============================================================
# HELPERS, NUTRITION ENGINE & SAFETY LOGIC
# ============================================================

def clean_json_response(text):
    """Clean an LLM response and return a JSON dictionary."""
    if not text:
        raise RuntimeError("INVALID_JSON")
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    raise RuntimeError("INVALID_JSON")


def generate_ai_response(prompt, retries=3, temperature=0.3):
    """Call Groq GPT-OSS reliably, with JSON mode and useful diagnostics."""
    last_error = None

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are NutriGuide AI, a careful nutrition-support "
                            "assistant. Follow the supplied safety constraints exactly. "
                            "Return valid JSON whenever the user requests JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                # GPT-OSS exposes reasoning separately. Disabling it prevents
                # the application from mistaking an empty content field for
                # a failed generation.
                include_reasoning=False,
                reasoning_effort="low",
                response_format={"type": "json_object"},
            )

            if not response.choices:
                raise RuntimeError("Groq returned no choices.")

            message_obj = response.choices[0].message
            content = getattr(message_obj, "content", None)

            if content and str(content).strip():
                return str(content).strip()

            # Some SDK/model responses may expose text through a different
            # field, so inspect common alternatives before failing.
            for field in ("text", "output_text"):
                alternative = getattr(response, field, None)
                if alternative and str(alternative).strip():
                    return str(alternative).strip()

            finish_reason = getattr(response.choices[0], "finish_reason", None)
            raise RuntimeError(
                f"Groq returned an empty content field "
                f"(finish_reason={finish_reason})."
            )

        except Exception as error:
            last_error = error
            message = str(error).lower()

            if "401" in message or "unauthorized" in message or "api key" in message:
                raise RuntimeError("INVALID_API_KEY") from error

            if "429" in message or "rate_limit" in message or "quota" in message:
                raise RuntimeError("API_QUOTA_EXCEEDED") from error

            if "400" in message and (
                "response_format" in message
                or "json" in message
                or "reasoning" in message
            ):
                # Retry once without optional GPT-OSS controls. This protects
                # the app from SDK/version differences while keeping JSON prompts.
                try:
                    fallback = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are NutriGuide AI. Follow the safety "
                                    "constraints exactly and return valid JSON."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=temperature,
                    )
                    fallback_content = getattr(
                        fallback.choices[0].message, "content", None
                    )
                    if fallback_content and str(fallback_content).strip():
                        return str(fallback_content).strip()
                except Exception as fallback_error:
                    last_error = fallback_error
                    message = str(fallback_error).lower()

            if "503" in message or "unavailable" in message or "timeout" in message:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue

            if attempt < retries - 1:
                time.sleep(1)
                continue

            # Preserve the real provider error instead of reporting only
            # "empty_response".
            raise RuntimeError(
                f"RAW_ERROR: {str(last_error).strip() or 'Unknown Groq error'}"
            ) from error

    raise RuntimeError(
        f"RAW_ERROR: {str(last_error).strip() or 'Max retries exceeded'}"
    )




def show_ai_error(error):
    code = str(error)
    if code == "INVALID_API_KEY":
        st.error("🔑 Your Groq API key is invalid or not authorised.")
        st.info("Check GROQ_API_KEY in Streamlit Secrets or your .env file.")
    elif code == "API_QUOTA_EXCEEDED":
        st.warning("⏳ Groq API rate limit or quota has been reached.")
        st.info("Please wait and try again.")
    elif code == "GROQ_TEMPORARILY_UNAVAILABLE":
        st.warning("🔄 Groq service is temporarily unavailable.")
        st.info("Please try again in a few moments.")
    elif code == "INVALID_JSON":
        st.error("📄 The AI returned an unexpected response format.")
        st.info("Please generate the plan again.")
    else:
        st.error(f"⚠️ Something went wrong: {str(error)}")


def reset_app():
    for key, value in DEFAULT_STATE.items():
        if isinstance(value, dict):
            st.session_state[key] = {}
        elif isinstance(value, list):
            st.session_state[key] = []
        else:
            st.session_state[key] = value
    st.session_state["chat_messages"] = []


def get_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def calculate_nutrition(age, sex, height_cm, weight_kg, activity_level, goal, medical_conditions=None):
    """
    Deterministic nutrition engine.
    Mifflin-St Jeor -> TDEE -> conservative goal adjustment.
    The LLM never performs these calculations.
    """
    activity_factors = {
        "Sedentary": 1.20,
        "Lightly active": 1.375,
        "Moderately active": 1.55,
        "Very active": 1.725,
        "Extra active": 1.90,
    }
    factor = activity_factors.get(activity_level, 1.20)

    if sex == "Male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    tdee = bmr * factor
    conditions = [str(x).lower() for x in (medical_conditions or [])]
    complex_condition = any(
        any(term in condition for term in [
            "kidney", "renal", "liver", "pregnan", "eating disorder",
            "severe malnutrition", "complex diabetes", "dialysis"
        ])
        for condition in conditions
    )

    if complex_condition:
        target = None
        calorie_note = (
            "Standard calorie targeting was not applied because the reported "
            "condition may require individualized medical nutrition therapy."
        )
    else:
        if goal == "Weight loss":
            target = max(1200 if sex == "Female" else 1500, round(tdee - 300))
        elif goal == "Weight gain":
            target = round(tdee + 250)
        elif goal == "Weight maintenance":
            target = round(tdee)
        else:
            target = round(tdee)
        calorie_note = "Estimated target; actual needs may differ."

    if target:
        # Balanced default macro split; values are deterministic estimates.
        protein_g = round((target * 0.25) / 4)
        carbs_g = round((target * 0.45) / 4)
        fat_g = round((target * 0.30) / 9)
    else:
        protein_g = carbs_g = fat_g = None

    return {
        "bmr_kcal": round(bmr),
        "activity_factor": factor,
        "tdee_kcal": round(tdee),
        "target_calories_kcal": target,
        "protein_g": protein_g,
        "carbohydrate_g": carbs_g,
        "fat_g": fat_g,
        "calorie_note": calorie_note,
        "calculation_method": "Mifflin–St Jeor BMR × activity factor",
        "complex_condition_flag": complex_condition,
    }


def assess_health_safety(user_data):
    """Deterministic safety layer; AI is not allowed to make medication decisions."""
    conditions = user_data.get("medical_conditions", [])
    if not isinstance(conditions, list):
        conditions = [conditions] if conditions else []
    medications = user_data.get("medications", [])
    if not isinstance(medications, list):
        medications = [medications] if medications else []

    condition_text = " ".join(str(x).lower() for x in conditions)
    high_risk_terms = {
        "kidney disease", "chronic kidney", "renal", "dialysis",
        "severe liver", "cirrhosis", "pregnancy", "pregnant",
        "eating disorder", "anorexia", "bulimia", "severe malnutrition",
        "complex diabetes", "type 1 diabetes", "multiple interacting",
    }
    high_risk = any(term in condition_text for term in high_risk_terms)

    flags = []
    if conditions:
        flags.append("Medical condition reported: recommendations should remain general and condition-aware.")
    if medications:
        flags.append("Medication information provided: review possible food–medication considerations; do not change treatment.")
    if high_risk:
        flags.append("The reported health context may require individualized medical nutrition therapy.")

    status = "professional_review_recommended" if high_risk else (
        "continue_with_caution" if conditions or medications else "safe_to_continue"
    )

    referral = bool(conditions or medications)
    return {
        "status": status,
        "medical_conditions": conditions,
        "medication_context": medications,
        "safety_flags": flags,
        "professional_advice_recommended": referral,
        "high_risk_context": high_risk,
        "allergy_restrictions": [user_data.get("food_allergies", "")] if user_data.get("food_allergies") else [],
        "dietary_restrictions": [user_data.get("dietary_restrictions", "")] if user_data.get("dietary_restrictions") else [],
        "foods_to_avoid": [user_data.get("foods_to_avoid", "")] if user_data.get("foods_to_avoid") else [],
    }


def validate_user_data(data):
    errors = []
    age = int(data.get("age", 0) or 0)
    height = safe_float(data.get("height_cm"))
    weight = safe_float(data.get("weight_kg"))

    if not 18 <= age <= 100:
        errors.append("Age must be between 18 and 100 for this adult nutrition MVP.")
    if not 120 <= height <= 230:
        errors.append("Please enter a realistic height between 120 and 230 cm.")
    if not 25 <= weight <= 300:
        errors.append("Please enter a realistic weight between 25 and 300 kg.")
    return errors


def nutrition_prompt_context(user_data, assessment, safety, nutrition):
    return f"""
USER PROFILE:
{json.dumps(user_data, indent=2)}

DETERMINISTIC NUTRITION CALCULATIONS:
{json.dumps(nutrition, indent=2)}

ASSESSMENT:
{json.dumps(assessment, indent=2)}

SAFETY CONTEXT:
{json.dumps(safety, indent=2)}
"""


def generate_plan(user_data, assessment, safety, nutrition, duration):
    """Generate a day-by-day plan in manageable chunks and preserve deterministic calculations."""
    days = int(duration)
    all_days = []

    # 7-day chunks prevent a long 60/90-day request from becoming one enormous LLM call.
    for start in range(1, days + 1, 7):
        end = min(start + 6, days)
        count = end - start + 1
        prompt = f"""
Create a personalized nutrition plan for Days {start}-{end} ({count} days) as part
of a {days}-day plan.

{nutrition_prompt_context(user_data, assessment, safety, nutrition)}

REQUIREMENTS:
- This is nutrition support, not medical treatment.
- Respect every allergy, restriction, preference and food to avoid.
- Use practical, familiar foods and portions.
- Prefer culturally practical South Asian/Pakistani options when appropriate.
- Use the deterministic calorie and macro values supplied above; do not recalculate them.
- Aim for daily energy close to the supplied target when a target is available.
- If target_calories_kcal is null, do not invent a calorie target.
- For medical conditions or medications, provide cautious general nutrition guidance only.
- Never tell the user to start, stop, or change a medication or dose.
- Never claim food cures or treats a disease.
- For high-risk health contexts, explicitly support professional consultation.
- Every day must include breakfast, lunch, dinner and a snack where appropriate.
- Each meal must contain food items, a practical portion, estimated calories,
  protein/carbohydrate/fat grams, and one alternative.
- Keep meals varied; do not simply repeat the same menu every day.

Return ONLY valid JSON:
{{
  "days": [
    {{
      "day": {start},
      "breakfast": {{
        "meal": "food + portion",
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0,
        "alternative": "alternative + portion"
      }},
      "lunch": {{
        "meal": "food + portion",
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0,
        "alternative": "alternative + portion"
      }},
      "snack": {{
        "meal": "food + portion",
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0,
        "alternative": "alternative + portion"
      }},
      "dinner": {{
        "meal": "food + portion",
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0,
        "alternative": "alternative + portion"
      }}
    }}
  ]
}}
"""
        chunk = clean_json_response(generate_ai_response(prompt, temperature=0.2))
        days_data = chunk.get("days", [])
        if not isinstance(days_data, list):
            raise RuntimeError("INVALID_JSON")
        all_days.extend(days_data)

    return {
        "plan_title": f"{days}-Day Personalized Nutrition Plan",
        "duration_days": days,
        "days": all_days[:days],
        "calorie_target": nutrition.get("target_calories_kcal"),
        "macro_targets": {
            "protein_g": nutrition.get("protein_g"),
            "carbs_g": nutrition.get("carbohydrate_g"),
            "fat_g": nutrition.get("fat_g"),
        },
        "important_safety_note": (
            "Calories and nutrient values are estimates. Medical or medication-related "
            "dietary needs may require review by a qualified healthcare professional or pharmacist."
        ),
    }


def run_ai_workflow(user_data):
    try:
        with st.spinner("🧮 Calculating your nutritional requirements..."):
            nutrition = calculate_nutrition(
                user_data["age"], user_data["sex"], user_data["height_cm"],
                user_data["weight_kg"], user_data["activity_level"],
                user_data["goal"], user_data.get("medical_conditions", [])
            )
            safety = assess_health_safety(user_data)
            st.session_state.nutrition = nutrition
            st.session_state.safety_result = safety

        with st.spinner("🧠 Analysing your profile and health context..."):
            assessment_prompt = f"""
Analyse this NutriGuide AI user profile. Do not calculate calories yourself.

{json.dumps(user_data, indent=2)}

Return ONLY valid JSON:
{{
  "profile_summary": "short personalized summary",
  "planning_considerations": ["item 1", "item 2"],
  "health_context_summary": "cautious health-context summary",
  "medication_considerations": ["only relevant general food considerations; never treatment changes"],
  "professional_advice_recommended": false
}}
"""
            assessment = clean_json_response(generate_ai_response(assessment_prompt))
            st.session_state.assessment = assessment

        with st.spinner(f"🍽️ Building your {user_data['duration_days']}-day plan..."):
            guidance = generate_plan(
                user_data, assessment, safety, nutrition, user_data["duration_days"]
            )
            st.session_state.guidance = guidance

        st.session_state.workflow_context = {
            "user_data": user_data,
            "assessment": assessment,
            "safety_result": safety,
            "nutrition": nutrition,
            "guidance": guidance,
        }
        st.session_state.chat_messages = []
        st.session_state.page = "results"
        st.rerun()

    except Exception as error:
        show_ai_error(error)


def meal_text(meal):
    if not isinstance(meal, dict):
        return str(meal)
    return meal.get("meal", "Meal unavailable")


def display_meal(meal, title):
    if not meal:
        st.write("No meal available.")
        return
    if isinstance(meal, dict):
        st.markdown(f"**{title}:** {meal.get('meal', '—')}")
        cols = st.columns(4)
        values = [
            ("Calories", f"{meal.get('calories', '—')} kcal"),
            ("Protein", f"{meal.get('protein_g', '—')} g"),
            ("Carbs", f"{meal.get('carbs_g', '—')} g"),
            ("Fat", f"{meal.get('fat_g', '—')} g"),
        ]
        for col, (label, value) in zip(cols, values):
            with col:
                st.metric(label, value)
        if meal.get("alternative"):
            st.caption(f"Alternative: {meal['alternative']}")


def create_pdf_report(user_data, assessment, safety_result, nutrition, guidance):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=19, spaceAfter=16)
    heading_style = ParagraphStyle("ReportHeading", parent=styles["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=4)

    def p(v):
        return escape(str(v if v is not None else "—")).replace("\n", "<br/>")

    story = [
        Paragraph("NutriGuide AI — Personalized Nutrition Report", title_style),
        Paragraph(datetime.now().strftime("Generated: %d %B %Y, %H:%M"), body_style),
        Paragraph("1. User Profile", heading_style),
    ]

    profile = [
        ["Age", user_data.get("age")],
        ["Sex", user_data.get("sex")],
        ["Height", f"{user_data.get('height_cm')} cm"],
        ["Weight", f"{user_data.get('weight_kg')} kg"],
        ["Activity", user_data.get("activity_level")],
        ["Goal", user_data.get("goal")],
        ["Plan duration", f"{user_data.get('duration_days')} days"],
        ["Diet", user_data.get("dietary_preference")],
        ["Allergies", user_data.get("food_allergies") or "None reported"],
        ["Conditions", ", ".join(user_data.get("medical_conditions", [])) or "None reported"],
        ["Medications", ", ".join(user_data.get("medication_names", [])) or "None reported"],
    ]
    table = Table([["Information", "Details"]] + [[p(a), p(b)] for a, b in profile], colWidths=[130, 365])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(table)

    story += [
        Paragraph("2. Nutritional Analysis", heading_style),
        Paragraph(f"BMR: {nutrition.get('bmr_kcal')} kcal/day", body_style),
        Paragraph(f"TDEE: {nutrition.get('tdee_kcal')} kcal/day", body_style),
        Paragraph(
            f"Estimated calorie target: {nutrition.get('target_calories_kcal') or 'Not provided due to health-safety context'}",
            body_style,
        ),
        Paragraph(
            f"Macro targets: Protein {nutrition.get('protein_g') or '—'} g · "
            f"Carbohydrates {nutrition.get('carbohydrate_g') or '—'} g · "
            f"Fat {nutrition.get('fat_g') or '—'} g",
            body_style,
        ),
        Paragraph("3. Safety & Health Context", heading_style),
        Paragraph(p(safety_result.get("status")), body_style),
        Paragraph(p(assessment.get("health_context_summary", "")), body_style),
    ]

    if safety_result.get("safety_flags"):
        for item in safety_result["safety_flags"]:
            story.append(Paragraph("• " + p(item), body_style))

    story.append(Paragraph("4. Personalized Meal Plan", heading_style))
    for day in guidance.get("days", []):
        story.append(Paragraph(f"<b>Day {p(day.get('day'))}</b>", body_style))
        for key in ["breakfast", "lunch", "snack", "dinner"]:
            meal = day.get(key, {})
            story.append(Paragraph(
                f"<b>{key.title()}:</b> {p(meal.get('meal', '—'))} "
                f"({p(meal.get('calories', '—'))} kcal; P {p(meal.get('protein_g', '—'))} g; "
                f"C {p(meal.get('carbs_g', '—'))} g; F {p(meal.get('fat_g', '—'))} g). "
                f"Alternative: {p(meal.get('alternative', '—'))}",
                body_style
            ))

    story += [
        Paragraph("Safety disclaimer", heading_style),
        Paragraph(
            "NutriGuide AI provides educational nutrition support and estimates. It is not a "
            "replacement for a physician, pharmacist, registered dietitian, or other qualified "
            "healthcare professional. Never start, stop, or change medication based on this report.",
            body_style,
        ),
    ]
    document.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# HOME
# ============================================================

def show_home():
    st.markdown(
        """
        <div class="brandbar">
            <div class="brand"><span class="brand-mark">n</span>NutriGuide <span style="color:var(--leaf)">AI</span></div>
            <span class="status-chip">Personalized nutrition MVP</span>
        </div>
        <section class="glass hero-panel">
            <div class="hero-grid">
                <div>
                    <div class="eyebrow">Personal nutrition, clearly guided</div>
                    <h1>A nutrition plan built around you.</h1>
                    <p class="lead">NutriGuide AI combines your profile, goals, dietary preferences, health context and medication information with deterministic nutrition calculations to create an adaptable meal plan.</p>
                    <div class="trust-row">
                        <span class="trust-item">BMR + TDEE</span>
                        <span class="trust-item">Health-aware</span>
                        <span class="trust-item">Allergy checked</span>
                        <span class="trust-item">AI meal alternatives</span>
                    </div>
                </div>
                <div class="hero-score">
                    <span>Your guided path</span>
                    <strong>Personal → Calculate → Plan</strong>
                    <span>Profile · Health context · Nutrition analysis · AI plan · Chat</span>
                </div>
            </div>
        </section>
        <div class="notice"><strong>Important:</strong> This is an educational nutrition-support tool. It does not diagnose disease, prescribe treatment, or replace a healthcare professional.</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-heading"><h2>What NutriGuide AI does</h2><p>Built around the PRD MVP</p></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    cards = [
        ("01", "Personalized inputs", "Age, sex, height, weight, activity, goal, preferences, allergies, conditions and medications."),
        ("02", "Deterministic nutrition", "BMR, TDEE, calorie target and macro estimates are calculated by Python rather than delegated to the LLM."),
        ("03", "Interactive plan", "Get day-by-day meals, portions, nutrition estimates, alternatives and conversational refinement."),
    ]
    for col, (number, title, body) in zip(cols, cards):
        with col:
            st.markdown(f'<div class="feature-card"><span class="feature-number">{number}</span><h3>{title}</h3><p>{body}</p></div>', unsafe_allow_html=True)

    st.write("")
    if st.button("Start nutrition assessment", type="primary", use_container_width=True, key="start_assessment_home"):
        st.session_state.page = "assessment"
        st.rerun()

    st.markdown('<div class="app-footer">NutriGuide AI · General educational nutrition support</div>', unsafe_allow_html=True)


# ============================================================
# ASSESSMENT WIZARD
# ============================================================

WIZARD_STEPS = ["Profile", "Health & Medication", "Goal & Preferences", "Plan Duration"]


def show_wizard_progress(current):
    st.markdown('<div class="wizard-shell"><div class="eyebrow">Assessment progress</div>', unsafe_allow_html=True)
    st.progress((current + 1) / len(WIZARD_STEPS))
    labels = []
    for i, label in enumerate(WIZARD_STEPS):
        state = "done" if i < current else "active" if i == current else ""
        prefix = "Complete" if i < current else f"Step {i + 1}"
        labels.append(f'<div class="wizard-step {state}">{prefix}<br><strong>{label}</strong></div>')
    st.markdown('<div class="wizard-labels">' + ''.join(labels) + '</div></div>', unsafe_allow_html=True)


def show_assessment():
    st.markdown(
        '<div class="brandbar"><div class="brand"><span class="brand-mark">n</span>NutriGuide <span style="color:var(--leaf)">AI</span></div><span class="status-chip">Private assessment</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="eyebrow">Personal nutrition profile</div>', unsafe_allow_html=True)
    st.title("Tell us what works for you")
    st.markdown('<p class="lead">These inputs are used to personalize your plan and apply the safety layer.</p>', unsafe_allow_html=True)

    current = st.session_state.wizard_step
    data = st.session_state.wizard_data
    show_wizard_progress(current)

    if current == 0:
        st.subheader("Your profile")
        c1, c2 = st.columns(2)
        with c1:
            data["age"] = st.number_input("Age", min_value=18, max_value=100, value=int(data.get("age", 25)), step=1)
            data["height_cm"] = st.number_input("Height (cm)", min_value=120.0, max_value=230.0, value=float(data.get("height_cm", 170.0)), step=0.5)
        with c2:
            data["sex"] = st.selectbox("Sex", ["Female", "Male"], index=["Female", "Male"].index(data.get("sex", "Female")))
            data["weight_kg"] = st.number_input("Weight (kg)", min_value=25.0, max_value=300.0, value=float(data.get("weight_kg", 70.0)), step=0.5)
        activity_options = ["Sedentary", "Lightly active", "Moderately active", "Very active", "Extra active"]
        data["activity_level"] = st.selectbox("Physical activity level", activity_options, index=activity_options.index(data.get("activity_level", "Moderately active")))
        st.caption("BMR/TDEE calculations use Mifflin–St Jeor and the selected activity factor.")
        _, nxt = st.columns([3,1])
        with nxt:
            if st.button("Continue", type="primary", use_container_width=True, key="wizard_next_0"):
                st.session_state.wizard_step = 1
                st.rerun()

    elif current == 1:
        st.subheader("Health & medication information")
        st.caption("This information is used for dietary context and safety checks. It does not change your medical treatment.")

        health_options = ["No", "Yes", "Not sure"]
        data["has_medical_condition"] = st.radio(
            "Do you have any medical condition that may affect your diet or nutritional needs?",
            health_options, index=health_options.index(data.get("has_medical_condition", "No")),
            horizontal=True
        )
        condition_options = [
            "Diabetes", "Hypertension", "Cardiovascular disease", "Kidney disease",
            "Liver disease", "Gastrointestinal condition", "Thyroid disorder", "Anemia", "Other"
        ]
        if data["has_medical_condition"] == "Yes":
            data["medical_conditions"] = st.multiselect(
                "What medical condition(s) do you have?",
                condition_options,
                default=data.get("medical_conditions", [])
            )
            if "Other" in data["medical_conditions"]:
                data["other_condition"] = st.text_input("Specify other condition", value=data.get("other_condition", ""))
        else:
            data["medical_conditions"] = []

        st.divider()
        data["taking_medication"] = st.radio(
            "Are you currently taking any medications that may be relevant to your diet or nutrition?",
            health_options, index=health_options.index(data.get("taking_medication", "No")),
            horizontal=True
        )
        if data["taking_medication"] == "Yes":
            st.caption("You may enter multiple medications. Strength and frequency are optional.")
            data["medication_names"] = st.text_area("Medication name(s)", value=", ".join(data.get("medication_names", [])), placeholder="Example: metformin, losartan")
            data["medication_strengths"] = st.text_area("Strength / dose, if known", value=data.get("medication_strengths", ""), placeholder="Example: 500 mg")
            data["medication_frequency"] = st.text_area("Frequency, if known", value=data.get("medication_frequency", ""), placeholder="Example: twice daily")
        else:
            data["medication_names"] = ""
            data["medication_strengths"] = ""
            data["medication_frequency"] = ""

        back, nxt = st.columns(2)
        with back:
            if st.button("Back", use_container_width=True, key="wizard_back_1"):
                st.session_state.wizard_step = 0
                st.rerun()
        with nxt:
            if st.button("Continue", type="primary", use_container_width=True, key="wizard_next_1"):
                st.session_state.wizard_step = 2
                st.rerun()

    elif current == 2:
        st.subheader("Goal & dietary preferences")
        goal_options = ["Weight loss", "Weight maintenance", "Weight gain", "General healthy eating"]
        data["goal"] = st.selectbox("Primary nutrition goal", goal_options, index=goal_options.index(data.get("goal", "General healthy eating")))
        dietary_options = ["No specific preference", "Vegetarian", "Vegan", "Halal", "Other"]
        data["dietary_preference"] = st.selectbox("Dietary preference", dietary_options, index=dietary_options.index(data.get("dietary_preference", "No specific preference")))
        if data["dietary_preference"] == "Other":
            data["dietary_other"] = st.text_input("Describe your dietary preference", value=data.get("dietary_other", ""))

        c1, c2 = st.columns(2)
        with c1:
            data["food_allergies"] = st.text_area("Food allergies", value=data.get("food_allergies", ""), placeholder="Example: peanuts, shellfish, milk")
            data["dietary_restrictions"] = st.text_area("Dietary restrictions", value=data.get("dietary_restrictions", ""), placeholder="Example: low sodium, gluten-free")
        with c2:
            data["foods_to_avoid"] = st.text_area("Foods you dislike or want to avoid", value=data.get("foods_to_avoid", ""), placeholder="Example: fish, very spicy foods")
            data["favourite_foods"] = st.text_area("Favourite or commonly available foods", value=data.get("favourite_foods", ""), placeholder="Example: roti, rice, chicken, lentils, vegetables")

        back, nxt = st.columns(2)
        with back:
            if st.button("Back", use_container_width=True, key="wizard_back_2"):
                st.session_state.wizard_step = 1
                st.rerun()
        with nxt:
            if st.button("Continue", type="primary", use_container_width=True, key="wizard_next_2"):
                st.session_state.wizard_step = 3
                st.rerun()

    else:
        st.subheader("Choose your plan duration")
        duration_options = [7, 14, 30, 60, 90]
        selected = st.selectbox(
            "Plan duration",
            duration_options,
            index=duration_options.index(int(data.get("duration_days", 30))),
            format_func=lambda x: f"{x} days"
        )
        data["duration_days"] = selected
        custom = st.checkbox("Use a custom duration instead", value=data.get("use_custom_duration", False), key="use_custom_duration")
        data["use_custom_duration"] = custom
        if custom:
            data["duration_days"] = st.number_input(
                "Custom duration (days)", min_value=1, max_value=365,
                value=int(data.get("custom_duration_days", 30)), step=1
            )
            data["custom_duration_days"] = data["duration_days"]

        st.info("30 days is the recommended default. You can choose another duration or enter your own.")
        st.markdown('<div class="notice"><strong>Safety first.</strong> Medical and medication information is considered for context only. NutriGuide AI never recommends starting, stopping, or changing medication.</div>', unsafe_allow_html=True)

        back, submit = st.columns(2)
        with back:
            if st.button("Back", use_container_width=True, key="wizard_back_3"):
                st.session_state.wizard_step = 2
                st.rerun()
        with submit:
            if st.button("Generate my personalized plan", type="primary", use_container_width=True, key="wizard_submit"):
                conditions = list(data.get("medical_conditions", []))
                if "Other" in conditions and data.get("other_condition", "").strip():
                    conditions = [x for x in conditions if x != "Other"] + [data["other_condition"].strip()]

                preference = data.get("dietary_preference", "No specific preference")
                if preference == "Other":
                    preference = data.get("dietary_other", "").strip() or "No specific preference"

                medication_text = data.get("medication_names", "").strip()
                medication_list = [x.strip() for x in medication_text.replace("\n", ",").split(",") if x.strip()]

                user_data = {
                    "age": int(data["age"]),
                    "sex": data["sex"],
                    "height_cm": float(data["height_cm"]),
                    "weight_kg": float(data["weight_kg"]),
                    "activity_level": data["activity_level"],
                    "has_medical_condition": data.get("has_medical_condition", "No"),
                    "medical_conditions": conditions,
                    "taking_medication": data.get("taking_medication", "No"),
                    "medication_names": medication_list,
                    "medication_strengths": data.get("medication_strengths", "").strip(),
                    "medication_frequency": data.get("medication_frequency", "").strip(),
                    "goal": data.get("goal", "General healthy eating"),
                    "dietary_preference": preference,
                    "food_allergies": data.get("food_allergies", "").strip(),
                    "dietary_restrictions": data.get("dietary_restrictions", "").strip(),
                    "foods_to_avoid": data.get("foods_to_avoid", "").strip(),
                    "favourite_foods": data.get("favourite_foods", "").strip(),
                    "duration_days": int(data["duration_days"]),
                }
                errors = validate_user_data(user_data)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    st.session_state.user_data = user_data
                    run_ai_workflow(user_data)


# ============================================================
# CHAT / PLAN REFINEMENT
# ============================================================

def chat_with_plan(user_message):
    context = st.session_state.workflow_context
    prompt = f"""
You are the NutriGuide AI conversational refinement assistant.

USER PROFILE:
{json.dumps(context.get("user_data", {}), indent=2)}

NUTRITION CALCULATIONS:
{json.dumps(context.get("nutrition", {}), indent=2)}

SAFETY CONTEXT:
{json.dumps(context.get("safety_result", {}), indent=2)}

CURRENT PLAN:
{json.dumps(context.get("guidance", {}), indent=2)}

USER REQUEST:
{user_message}

Rules:
- Keep the response connected to the current profile and plan.
- If the user requests a meal replacement, give a suitable alternative while preserving the meal's nutritional purpose.
- Respect allergies, restrictions, dislikes, goal, calorie target, medical conditions and medication context.
- Never advise starting, stopping or changing medication.
- Never claim food cures or treats disease.
- For health-condition-specific or medication-specific questions, give cautious general information and recommend a qualified professional when appropriate.
- If asked to change one meal, do not regenerate the entire plan.
- Answer naturally and clearly.

Return ONLY valid JSON:
{{
  "reply": "your concise response",
  "replacement": {{
      "day": 0,
      "meal_type": "",
      "meal": "",
      "calories": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0,
      "alternative": ""
  }},
  "apply_replacement": false
}}
"""
    result = clean_json_response(generate_ai_response(prompt, temperature=0.25))
    replacement = result.get("replacement", {})
    if get_bool(result.get("apply_replacement", False)):
        day_number = int(replacement.get("day", 0) or 0)
        meal_type = str(replacement.get("meal_type", "")).lower().strip()
        if day_number > 0 and meal_type in {"breakfast", "lunch", "snack", "dinner"}:
            for day in context["guidance"].get("days", []):
                if int(day.get("day", 0) or 0) == day_number:
                    day[meal_type] = {
                        "meal": replacement.get("meal", ""),
                        "calories": replacement.get("calories", 0),
                        "protein_g": replacement.get("protein_g", 0),
                        "carbs_g": replacement.get("carbs_g", 0),
                        "fat_g": replacement.get("fat_g", 0),
                        "alternative": replacement.get("alternative", ""),
                    }
                    break
            st.session_state.guidance = context["guidance"]
            st.session_state.workflow_context["guidance"] = context["guidance"]
    return result.get("reply", "I couldn't process that request.")


def show_chat():
    st.markdown('<div class="section-heading"><h2>Ask NutriGuide AI</h2><p>Refine the current plan without regenerating everything</p></div>', unsafe_allow_html=True)
    st.caption("Try: “Replace Day 1 dinner with a vegetarian option” or “Why was this breakfast recommended?”")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_message = st.chat_input("Ask about your plan or request a meal change...")
    if user_message:
        st.session_state.chat_messages.append({"role": "user", "content": user_message})
        try:
            with st.spinner("Thinking..."):
                reply = chat_with_plan(user_message)
            st.session_state.chat_messages.append({"role": "assistant", "content": reply})
        except Exception as error:
            show_ai_error(error)
        st.rerun()


# ============================================================
# RESULTS
# ============================================================

def show_results():
    user_data = st.session_state.user_data
    assessment = st.session_state.assessment
    safety = st.session_state.safety_result
    nutrition = st.session_state.nutrition
    guidance = st.session_state.guidance

    st.markdown(
        f'<div class="brandbar"><div class="brand"><span class="brand-mark">n</span>NutriGuide <span style="color:var(--leaf)">AI</span></div><span class="status-chip">{("Review advised" if safety.get("status") != "safe_to_continue" else "Safety reviewed")}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="eyebrow">Your nutrition dashboard</div>', unsafe_allow_html=True)
    st.title("Your personalized plan is ready")
    st.markdown(
        f'<p class="lead">{guidance.get("duration_days", user_data["duration_days"])}-day plan based on your profile, goal, dietary constraints and health context.</p>',
        unsafe_allow_html=True,
    )

    if safety.get("status") == "professional_review_recommended":
        st.warning("⚠️ Your reported health context may require individualized nutrition care. Use this plan only as general educational guidance and consult an appropriate healthcare professional.")
    elif safety.get("status") == "continue_with_caution":
        st.warning("⚠️ Health or medication information was reported. Condition-specific advice should be reviewed with a qualified healthcare professional or pharmacist.")

    st.markdown('<div class="section-heading"><h2>Nutrition analysis</h2><p>Calculated by the application</p></div>', unsafe_allow_html=True)
    cols = st.columns(4)
    metrics = [
        ("BMR", f"{nutrition.get('bmr_kcal')} kcal"),
        ("TDEE", f"{nutrition.get('tdee_kcal')} kcal"),
        ("Target", f"{nutrition.get('target_calories_kcal') or '—'} kcal"),
        ("Plan", f"{user_data.get('duration_days')} days"),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.metric(label, value)

    st.caption(f"{nutrition.get('calculation_method')}. {nutrition.get('calorie_note')}")

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Protein target", f"{nutrition.get('protein_g') or '—'} g/day")
    with m2:
        st.metric("Carbohydrate target", f"{nutrition.get('carbohydrate_g') or '—'} g/day")
    with m3:
        st.metric("Fat target", f"{nutrition.get('fat_g') or '—'} g/day")

    with st.expander("View your profile & health context"):
        st.json({
            "Age": user_data.get("age"),
            "Sex": user_data.get("sex"),
            "Height": f"{user_data.get('height_cm')} cm",
            "Weight": f"{user_data.get('weight_kg')} kg",
            "Activity": user_data.get("activity_level"),
            "Goal": user_data.get("goal"),
            "Dietary preference": user_data.get("dietary_preference"),
            "Allergies": user_data.get("food_allergies") or "None reported",
            "Restrictions": user_data.get("dietary_restrictions") or "None reported",
            "Foods to avoid": user_data.get("foods_to_avoid") or "None reported",
            "Medical conditions": user_data.get("medical_conditions") or "None reported",
            "Medications": user_data.get("medication_names") or "None reported",
        })

    with st.expander("Personalized assessment", expanded=True):
        st.write(assessment.get("profile_summary", ""))
        if assessment.get("planning_considerations"):
            st.markdown("**Planning considerations**")
            for item in assessment["planning_considerations"]:
                st.write("•", item)
        if assessment.get("medication_considerations"):
            st.markdown("**Medication-related dietary considerations**")
            for item in assessment["medication_considerations"]:
                st.write("•", item)

    st.markdown('<div class="section-heading"><h2>Your day-by-day plan</h2><p>Meals, portions, estimates and alternatives</p></div>', unsafe_allow_html=True)

    days = guidance.get("days", [])
    if days:
        for day in days:
            day_number = day.get("day", "?")
            with st.expander(f"Day {day_number}", expanded=(day_number == 1)):
                for key, label in [
                    ("breakfast", "Breakfast"),
                    ("lunch", "Lunch"),
                    ("snack", "Snack"),
                    ("dinner", "Dinner"),
                ]:
                    st.markdown('<div class="meal-card">', unsafe_allow_html=True)
                    display_meal(day.get(key, {}), label)
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error("No meal days were returned. Please create a new plan.")

    show_chat()

    st.markdown('<div class="section-heading"><h2>Your report</h2><p>Save the complete assessment and plan</p></div>', unsafe_allow_html=True)
    try:
        pdf_data = create_pdf_report(user_data, assessment, safety, nutrition, guidance)
        st.download_button(
            "Download nutrition report", data=pdf_data,
            file_name="NutriGuide_AI_Report.pdf", mime="application/pdf",
            type="primary", use_container_width=True, key="download_report"
        )
    except Exception:
        st.error("The PDF report could not be generated.")

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Create new assessment", type="primary", use_container_width=True, key="new_assessment"):
            reset_app()
            st.session_state.page = "assessment"
            st.rerun()
    with c2:
        if st.button("Back to home", use_container_width=True, key="back_home"):
            reset_app()
            st.session_state.page = "home"
            st.rerun()

    st.markdown('<div class="app-footer">NutriGuide AI · General educational nutrition support</div>', unsafe_allow_html=True)


# ============================================================
# ROUTING
# ============================================================

if "nutrition" not in st.session_state:
    st.session_state.nutrition = {}
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if st.session_state.page == "home":
    show_home()
elif st.session_state.page == "assessment":
    show_assessment()
elif st.session_state.page == "results":
    show_results()
else:
    reset_app()
    show_home()
