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
            --leaf: #2f9e6f;
            --leaf-soft: #78c39f;
            --mint: #eaf5ee;
            --paper: #f4f8f5;
            --ink: #17241d;
            --citrus: #f0a92b;
            --teal: #1c857f;
            --alert: #d8574b;
            --line: rgba(23, 36, 29, 0.10);
            --glass: rgba(255, 255, 255, 0.72);
        }

        html, body, [class*="css"] { font-family: "Inter", sans-serif; }
        .stApp { background: var(--paper); color: var(--ink); }
        .stApp::before {
            content: ""; position: fixed; inset: 0; pointer-events: none;
            background-color: var(--paper);
            background-image: linear-gradient(rgba(47,158,111,.025) 1px, transparent 1px), linear-gradient(90deg, rgba(47,158,111,.025) 1px, transparent 1px);
            background-size: 32px 32px;
        }
        header[data-testid="stHeader"] { background: rgba(244,248,245,.80); backdrop-filter: blur(20px); }
        #MainMenu, footer { visibility: hidden; }
        .block-container { max-width: 1180px; padding: 2.25rem 2rem 4rem; position: relative; }
        h1, h2, h3 { font-family: "Space Grotesk", sans-serif; color: var(--ink); letter-spacing: 0; }
        h1 { font-size: clamp(2rem, 4vw, 3.25rem); line-height: 1.08; font-weight: 700; }
        h2, h3 { font-weight: 600; }
        p, label, .stMarkdown { color: var(--ink); }
        hr { border-color: var(--line); margin: 1.6rem 0; }

        .brandbar { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:2rem; }
        .brand { display:flex; align-items:center; gap:.75rem; font:700 1.12rem "Space Grotesk",sans-serif; }
        .brand-mark { width:2.25rem; height:2.25rem; display:grid; place-items:center; border-radius:.75rem; background:var(--leaf); color:white; }
        .status-chip { display:inline-flex; align-items:center; gap:.5rem; padding:.45rem .75rem; border-radius:999px; background:var(--mint); color:var(--leaf); font-size:.78rem; font-weight:700; border:1px solid rgba(47,158,111,.16); }
        .status-chip::before { content:""; width:.42rem; height:.42rem; border-radius:50%; background:var(--leaf); }
        .eyebrow { color:var(--leaf); font-size:.76rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.7rem; }
        .lead { color:rgba(23,36,29,.66); font-size:1.03rem; line-height:1.7; max-width:680px; }
        .glass, .feature-card, .step-card, .summary-card, .meal-card {
            background:var(--glass); border:1px solid rgba(255,255,255,.9); box-shadow:0 12px 40px rgba(23,36,29,.06); backdrop-filter:blur(18px); border-radius:16px;
        }
        .hero-panel { padding:clamp(1.5rem,4vw,3rem); margin-bottom:1rem; overflow:hidden; position:relative; }
        .hero-panel::after { content:""; position:absolute; width:8px; top:0; bottom:0; left:0; background:var(--leaf); }
        .hero-grid { display:grid; grid-template-columns:1.45fr .75fr; gap:2rem; align-items:center; }
        .hero-score { background:var(--ink); color:white; border-radius:14px; padding:1.3rem; }
        .hero-score strong { display:block; font:600 2.1rem "Space Grotesk",sans-serif; color:white; }
        .hero-score span { color:rgba(255,255,255,.68); font-size:.84rem; }
        .trust-row { display:flex; flex-wrap:wrap; gap:.65rem; margin-top:1.4rem; }
        .trust-item { padding:.5rem .7rem; border-radius:8px; background:var(--mint); color:var(--leaf); font-size:.78rem; font-weight:700; }
        .section-heading { display:flex; align-items:end; justify-content:space-between; gap:1rem; margin:2rem 0 1rem; }
        .section-heading h2 { margin:0; font-size:1.5rem; }
        .section-heading p { margin:0; color:rgba(23,36,29,.55); font-size:.85rem; }
        .feature-card, .step-card { min-height:190px; padding:1.35rem; }
        .feature-number { display:grid; place-items:center; width:2.25rem; height:2.25rem; border-radius:.7rem; margin-bottom:1.1rem; background:var(--mint); color:var(--leaf); font-weight:800; }
        .feature-card h3, .step-card h3 { font-size:1rem; margin:.2rem 0 .55rem; }
        .feature-card p, .step-card p { color:rgba(23,36,29,.62); font-size:.88rem; line-height:1.6; }
        .notice { border-left:3px solid var(--citrus); background:rgba(240,169,43,.10); padding:1rem 1.1rem; border-radius:0 12px 12px 0; color:rgba(23,36,29,.72); font-size:.86rem; }

        div[data-testid="stMetric"] { background:var(--glass); border:1px solid rgba(255,255,255,.9); padding:1rem; border-radius:14px; box-shadow:0 8px 28px rgba(23,36,29,.05); min-height:126px; }
        div[data-testid="stMetricLabel"] { font-weight:600; color:rgba(23,36,29,.55); }
        div[data-testid="stMetricValue"] { font-family:"Space Grotesk",sans-serif; color:var(--ink); }
        div[data-testid="stAlert"] { border-radius:12px; border-width:1px; }
        div[data-testid="stExpander"] { background:rgba(255,255,255,.65); border:1px solid rgba(255,255,255,.9); border-radius:14px; overflow:hidden; }
        div[data-baseweb="select"] > div, textarea, input { border-radius:10px !important; border-color:var(--line) !important; background:rgba(255,255,255,.76) !important; }
        textarea:focus, input:focus { border-color:var(--leaf) !important; box-shadow:0 0 0 2px rgba(47,158,111,.12) !important; }
        .stButton > button, .stDownloadButton > button { border-radius:10px; min-height:44px; font-weight:700; border-color:var(--line); transition:transform .16s ease, box-shadow .16s ease; }
        .stButton > button:hover, .stDownloadButton > button:hover { transform:translateY(-1px); box-shadow:0 8px 18px rgba(23,36,29,.10); border-color:var(--leaf); }
        .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] { background:var(--ink); color:white; border-color:var(--ink); }
        .stButton > button[kind="primary"] p, .stDownloadButton > button[kind="primary"] p { color:white; }
        .stProgress > div > div > div > div { background:var(--leaf); }
        .stTabs [data-baseweb="tab-list"] { gap:.3rem; background:rgba(23,36,29,.04); border-radius:12px; padding:.3rem; }
        .stTabs [data-baseweb="tab"] { border-radius:9px; padding:.55rem 1rem; }
        .stTabs [aria-selected="true"] { background:white; color:var(--leaf); }
        .stTabs [data-baseweb="tab-highlight"] { display:none; }
        .summary-card { padding:1.35rem; margin-bottom:1rem; }
        .summary-card h2 { margin:0 0 .35rem; font-size:1.35rem; }
        .summary-card p { margin:.2rem 0; color:rgba(23,36,29,.62); }
        .meal-card { padding:1rem; margin:.65rem 0; border-left:3px solid var(--leaf); font-size:.9rem; }
        .wizard-shell { background:var(--glass); border:1px solid rgba(255,255,255,.9); border-radius:16px; padding:1.3rem; margin:1rem 0 1.5rem; box-shadow:0 12px 40px rgba(23,36,29,.05); }
        .wizard-labels { display:grid; grid-template-columns:repeat(3,1fr); gap:.75rem; margin-top:.75rem; }
        .wizard-step { color:rgba(23,36,29,.42); font-size:.78rem; font-weight:600; }
        .wizard-step.active { color:var(--leaf); }
        .wizard-step.done { color:var(--teal); }
        .app-footer { text-align:center; padding:2rem 0 .5rem; color:rgba(23,36,29,.48); font-size:.78rem; }
        .small-note { font-size:.84rem; color:rgba(23,36,29,.55); }

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
# HELPER FUNCTIONS
# ============================================================

def clean_json_response(text):
    """Clean AI output and convert it into a Python dictionary."""

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

        if not isinstance(result, dict):
            raise RuntimeError("INVALID_JSON")

        return result

    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:

        json_text = text[start:end + 1]

        try:

            result = json.loads(json_text)

            if not isinstance(result, dict):
                raise RuntimeError("INVALID_JSON")

            return result

        except json.JSONDecodeError as error:

            raise RuntimeError(
                "INVALID_JSON"
            ) from error

    raise RuntimeError("INVALID_JSON")


def generate_ai_response(prompt, retries=3):
    """Generate Groq response with safe error handling."""

    for attempt in range(retries):

        try:

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            content = response.choices[0].message.content

            if not content:

                raise RuntimeError(
                    "Groq returned an empty response."
                )

            return content

        except Exception as error:

            error_message = str(error).lower()

            if (
                "401" in error_message
                or "unauthorized" in error_message
                or "api key" in error_message
            ):

                raise RuntimeError(
                    "INVALID_API_KEY"
                ) from error

            if (
                "429" in error_message
                or "rate_limit" in error_message
                or "quota" in error_message
            ):

                raise RuntimeError(
                    "API_QUOTA_EXCEEDED"
                ) from error

            if (
                "503" in error_message
                or "unavailable" in error_message
            ):

                if attempt < retries - 1:

                    time.sleep(3)
                    continue

                raise RuntimeError(
                    "GROQ_TEMPORARILY_UNAVAILABLE"
                ) from error

            # This passes the exact error message up to the UI
            raise RuntimeError(f"RAW_ERROR: {error_message}") from error

    raise RuntimeError("RAW_ERROR: Max retries exceeded")


def show_ai_error(error):
    """Display a friendly message for a known AI/workflow error code."""

    error_code = str(error)

    if error_code == "INVALID_API_KEY":

        st.error("🔑 Your Groq API key is invalid or not authorised.")
        st.info(
            "Please check GROQ_API_KEY in your Streamlit "
            "Secrets and try again."
        )

    elif error_code == "API_QUOTA_EXCEEDED":

        st.warning("⏳ Groq API rate limit or quota has been reached.")
        st.info("Please wait a moment and try again later.")

    elif error_code == "GROQ_TEMPORARILY_UNAVAILABLE":

        st.warning("🔄 Groq service is temporarily unavailable.")
        st.info("Please wait a few moments and try again.")

    elif error_code == "INVALID_JSON":

        st.error("📄 The AI returned an unexpected response format.")
        st.info("Please try generating the guidance again.")

    else:

        st.error(f"⚠️ RAW ERROR DETAILS: {str(error)}")


def regenerate_meal_ideas(meal_label, meal_key, existing_ideas):
    """Ask the Guidance Agent for a fresh batch of ideas for one meal type."""

    user_data = st.session_state.get("user_data", {})
    assessment = st.session_state.get("assessment", {})
    safety_result = st.session_state.get("safety_result", {})

    prompt = f"""
You are the Nutrition Guidance Agent for NutriGuide AI.

Generate 4 NEW general {meal_label} ideas for this user, different
from the ideas already given below.

USER INFORMATION:
{json.dumps(user_data, indent=2)}

ASSESSMENT:
{json.dumps(assessment, indent=2)}

SAFETY CHECK:
{json.dumps(safety_result, indent=2)}

IDEAS ALREADY GIVEN (do not repeat these):
{json.dumps(existing_ideas, indent=2)}

IMPORTANT RULES:
- This is general nutrition education, not medical advice.
- Do not diagnose, prescribe treatment diets, or give calorie or
  weight targets.
- Respect all allergies and foods the user avoids.
- Respect dietary preferences.
- Use practical, familiar and culturally appropriate foods.

Return ONLY valid JSON in exactly this structure:

{{
  "{meal_key}": [
    "Idea 1",
    "Idea 2",
    "Idea 3",
    "Idea 4"
  ]
}}
"""

    text = generate_ai_response(prompt)
    result = clean_json_response(text)

    return result.get(meal_key, [])


def display_list_items(
    items,
    empty_message="No information available.",
    card_style=False,
):
    """Display a list safely in the Streamlit UI."""

    if not items:

        st.write(empty_message)
        return

    if not isinstance(items, list):

        items = [items]

    for item in items:

        if card_style:

            st.markdown(
                f"""
                <div class="meal-card">
                    🍽️ {item}
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            st.write(f"• {item}")


def reset_app():
    """Reset the application for a new assessment."""

    for key, value in DEFAULT_STATE.items():

        st.session_state[key] = value


def get_bool(value):
    """Safely convert common AI boolean values to bool."""

    if isinstance(value, bool):
        return value

    if isinstance(value, str):

        return value.strip().lower() in {
            "true",
            "yes",
            "1",
        }

    return bool(value)


def pdf_text(value):
    """
    Safely convert text for ReportLab Paragraphs.

    Escaping prevents AI-generated characters such as
    &, < and > from breaking PDF markup.
    """

    if value is None:
        return ""

    return escape(str(value)).replace(
        "\n",
        "<br/>",
    )


def create_pdf_report(
    user_data,
    assessment,
    safety_result,
    guidance,
):
    """Create a downloadable PDF nutrition report."""

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=20,
    )

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )

    small_style = ParagraphStyle(
        "ReportSmall",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        spaceAfter=5,
    )

    story = []

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "NutriGuide AI - Nutrition Report",
            title_style,
        )
    )

    story.append(
        Paragraph(
            "Generated: "
            + datetime.now().strftime(
                "%d %B %Y, %H:%M"
            ),
            small_style,
        )
    )

    story.append(Spacer(1, 10))

    # --------------------------------------------------------
    # NUTRITION PROFILE
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "1. Nutrition Profile",
            heading_style,
        )
    )

    profile_data = [
        [
            "Information",
            "Details",
        ],
        [
            "Age Group",
            pdf_text(
                user_data.get(
                    "age_group",
                    "Not provided",
                )
            ),
        ],
        [
            "Activity Level",
            pdf_text(
                user_data.get(
                    "activity_level",
                    "Not provided",
                )
            ),
        ],
        [
            "Dietary Preference",
            pdf_text(
                user_data.get(
                    "dietary_preference",
                    "Not provided",
                )
            ),
        ],
        [
            "Goal",
            pdf_text(
                user_data.get(
                    "goal",
                    "Not provided",
                )
            ),
        ],
    ]

    profile_table = Table(
        profile_data,
        colWidths=[150, 320],
    )

    profile_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.black,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    "Helvetica",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(profile_table)

    story.append(Spacer(1, 12))

    # --------------------------------------------------------
    # ADDITIONAL USER INFORMATION
    # --------------------------------------------------------

    allergies_input = user_data.get(
        "food_allergies",
        "",
    )

    avoid_input = user_data.get(
        "foods_to_avoid",
        "",
    )

    favourite_input = user_data.get(
        "favourite_foods",
        "",
    )

    health_input = user_data.get(
        "health_information",
        "",
    )

    if any(
        [
            allergies_input,
            avoid_input,
            favourite_input,
            health_input,
        ]
    ):

        story.append(
            Paragraph(
                "Additional Information",
                heading_style,
            )
        )

        if allergies_input:

            story.append(
                Paragraph(
                    "<b>Food Allergies:</b> "
                    + pdf_text(allergies_input),
                    body_style,
                )
            )

        if avoid_input:

            story.append(
                Paragraph(
                    "<b>Foods Avoided:</b> "
                    + pdf_text(avoid_input),
                    body_style,
                )
            )

        if favourite_input:

            story.append(
                Paragraph(
                    "<b>Favourite / Available Foods:</b> "
                    + pdf_text(favourite_input),
                    body_style,
                )
            )

        if health_input:

            story.append(
                Paragraph(
                    "<b>Health Information:</b> "
                    + pdf_text(health_input),
                    body_style,
                )
            )

    # --------------------------------------------------------
    # AI ASSESSMENT
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "2. AI Assessment",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            pdf_text(
                assessment.get(
                    "profile_summary",
                    "No assessment summary available.",
                )
            ),
            body_style,
        )
    )

    planning_items = assessment.get(
        "planning_considerations",
        [],
    )

    if planning_items:

        story.append(
            Paragraph(
                "<b>Planning Considerations</b>",
                body_style,
            )
        )

        for item in planning_items:

            story.append(
                Paragraph(
                    "• " + pdf_text(item),
                    body_style,
                )
            )

    # --------------------------------------------------------
    # SAFETY INFORMATION
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "3. Safety Information",
            heading_style,
        )
    )

    safety_status = safety_result.get(
        "status",
        "safe_to_continue",
    )

    story.append(
        Paragraph(
            "<b>Status:</b> "
            + pdf_text(safety_status),
            body_style,
        )
    )

    safety_flags = safety_result.get(
        "safety_flags",
        [],
    )

    if safety_flags:

        story.append(
            Paragraph(
                "<b>Safety Considerations</b>",
                body_style,
            )
        )

        for item in safety_flags:

            story.append(
                Paragraph(
                    "• " + pdf_text(item),
                    body_style,
                )
            )

    allergy_restrictions = safety_result.get(
        "allergy_restrictions",
        [],
    )

    if allergy_restrictions:

        story.append(
            Paragraph(
                "<b>Allergy Restrictions</b>",
                body_style,
            )
        )

        for item in allergy_restrictions:

            story.append(
                Paragraph(
                    "• " + pdf_text(item),
                    body_style,
                )
            )

    dietary_restrictions = safety_result.get(
        "dietary_restrictions",
        [],
    )

    if dietary_restrictions:

        story.append(
            Paragraph(
                "<b>Dietary Restrictions</b>",
                body_style,
            )
        )

        for item in dietary_restrictions:

            story.append(
                Paragraph(
                    "• " + pdf_text(item),
                    body_style,
                )
            )

    foods_to_avoid = safety_result.get(
        "foods_to_avoid",
        [],
    )

    if foods_to_avoid:

        story.append(
            Paragraph(
                "<b>Foods to Avoid</b>",
                body_style,
            )
        )

        for item in foods_to_avoid:

            story.append(
                Paragraph(
                    "• " + pdf_text(item),
                    body_style,
                )
            )

    # --------------------------------------------------------
    # MEAL IDEAS
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "4. Meal Ideas",
            heading_style,
        )
    )

    meal_sections = [
        (
            "Breakfast",
            guidance.get(
                "breakfast_ideas",
                [],
            ),
        ),
        (
            "Lunch",
            guidance.get(
                "lunch_ideas",
                [],
            ),
        ),
        (
            "Snacks",
            guidance.get(
                "snack_ideas",
                [],
            ),
        ),
        (
            "Dinner",
            guidance.get(
                "dinner_ideas",
                [],
            ),
        ),
    ]

    for meal_name, meal_items in meal_sections:

        story.append(
            Paragraph(
                f"<b>{meal_name}</b>",
                body_style,
            )
        )

        if meal_items:

            if not isinstance(
                meal_items,
                list,
            ):

                meal_items = [meal_items]

            for item in meal_items:

                story.append(
                    Paragraph(
                        "• " + pdf_text(item),
                        body_style,
                    )
                )

        else:

            story.append(
                Paragraph(
                    "No meal ideas available.",
                    body_style,
                )
            )

    # --------------------------------------------------------
    # NUTRITION TIPS
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "5. General Nutrition Tips",
            heading_style,
        )
    )

    nutrition_tips = guidance.get(
        "nutrition_tips",
        [],
    )

    if nutrition_tips:

        if not isinstance(
            nutrition_tips,
            list,
        ):

            nutrition_tips = [nutrition_tips]

        for item in nutrition_tips:

            story.append(
                Paragraph(
                    "• " + pdf_text(item),
                    body_style,
                )
            )

    else:

        story.append(
            Paragraph(
                "No nutrition tips available.",
                body_style,
            )
        )

    # --------------------------------------------------------
    # IMPORTANT SAFETY NOTE
    # --------------------------------------------------------

    important_note = guidance.get(
        "important_safety_note",
        "",
    )

    if important_note:

        story.append(
            Paragraph(
                "Important Safety Note",
                heading_style,
            )
        )

        story.append(
            Paragraph(
                pdf_text(important_note),
                body_style,
            )
        )

    # --------------------------------------------------------
    # DISCLAIMER
    # --------------------------------------------------------

    story.append(Spacer(1, 15))

    story.append(
        Paragraph(
            "<b>Disclaimer:</b> This report provides general "
            "educational nutrition information and is not a "
            "substitute for professional medical advice. For "
            "medical conditions or personalised dietary treatment, "
            "consult a qualified healthcare professional or "
            "registered dietitian.",
            small_style,
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# HOME PAGE
# ============================================================

def show_home():
    st.markdown(
        """
        <div class="brandbar">
            <div class="brand"><span class="brand-mark">n</span>NutriGuide <span style="color:var(--leaf)">AI</span></div>
            <span class="status-chip">Nutrition intelligence ready</span>
        </div>
        <section class="glass hero-panel">
            <div class="hero-grid">
                <div>
                    <div class="eyebrow">Personal nutrition, clearly guided</div>
                    <h1>Build healthier habits around food that fits your life.</h1>
                    <p class="lead">Share your preferences, routine and goals. NutriGuide AI turns them into practical meal ideas and safety-aware, everyday nutrition guidance.</p>
                    <div class="trust-row">
                        <span class="trust-item">Preference aware</span>
                        <span class="trust-item">Allergy checked</span>
                        <span class="trust-item">Flexible meal ideas</span>
                    </div>
                </div>
                <div class="hero-score">
                    <span>Your guided path</span>
                    <strong>3 simple steps</strong>
                    <span>Profile · Safety review · Personal guidance</span>
                </div>
            </div>
        </section>
        <div class="notice"><strong>General wellness guidance.</strong> For medical or condition-specific dietary advice, consult a qualified healthcare professional.</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-heading"><h2>Designed around your needs</h2><p>Clear guidance, no rigid diet plans</p></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    cards = [
        ("01", "Personalised guidance", "Recommendations reflect your food preferences, activity level, goals and dietary needs."),
        ("02", "Practical meal ideas", "Flexible breakfast, lunch, snack and dinner ideas built for everyday routines."),
        ("03", "Safety-aware review", "Allergies, foods to avoid and health concerns are reviewed before guidance is prepared."),
    ]
    for col, (number, title, body) in zip(cols, cards):
        with col:
            st.markdown(f'<div class="feature-card"><span class="feature-number">{number}</span><h3>{title}</h3><p>{body}</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-heading"><h2>How your plan comes together</h2><p>About two minutes to complete</p></div>', unsafe_allow_html=True)
    steps = st.columns(3)
    step_content = [
        ("1", "Tell us about yourself", "Add your age group, activity level and the foods that work for you."),
        ("2", "Complete a safety check", "The AI reviews dietary restrictions and important health considerations."),
        ("3", "Explore your guidance", "Review personalised meal ideas, nutrition tips and a downloadable report."),
    ]
    for col, (number, title, body) in zip(steps, step_content):
        with col:
            st.markdown(f'<div class="step-card"><span class="feature-number">{number}</span><h3>{title}</h3><p>{body}</p></div>', unsafe_allow_html=True)

    st.write("")
    if st.button("Start nutrition assessment", type="primary", use_container_width=True, key="start_assessment_home"):
        st.session_state.page = "assessment"
        st.rerun()

    st.markdown('<div class="app-footer">NutriGuide AI · General educational nutrition guidance</div>', unsafe_allow_html=True)


# ============================================================
# NUTRITION ASSESSMENT PAGE
# ============================================================

def run_ai_workflow(user_data):
    """Run the 3-stage AI workflow: assessment, safety check, guidance."""

    try:

        # =================================================
        # STAGE 1 - ASSESSMENT
        # =================================================

        with st.spinner("🧠 Analysing your information..."):

            assessment_prompt = f"""
You are the Assessment Agent for NutriGuide AI.

Your job is to analyse the user's nutrition information and
prepare a structured profile for the next workflow stages.

USER INFORMATION:
{json.dumps(user_data, indent=2)}

IMPORTANT SAFETY RULES:
- This app provides general nutrition education.
- Do not diagnose medical conditions.
- Do not prescribe treatment diets.
- Do not create restrictive weight-loss plans.
- Do not provide calorie restriction targets.
- Do not set weight-loss or weight-gain targets.
- If the user mentions a medical condition or health concern,
  clearly recommend consultation with a qualified healthcare
  professional or registered dietitian for condition-specific
  advice.
- Respect allergies and foods the user avoids.
- The user's age group must be considered.
- If the user is under 18, provide only age-appropriate,
  general healthy-eating guidance and avoid dieting or
  weight-focused advice.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "profile_summary": "Short general summary.",
  "dietary_preference": "Dietary preference",
  "allergies": [],
  "foods_to_avoid": [],
  "goal": "Main goal",
  "plan_type": "long_term_guidance",
  "plan_type_reason": "Short explanation.",
  "planning_considerations": [],
  "safety_notes": [],
  "professional_advice_recommended": false
}}

PLAN TYPE RULES:
- Use "long_term_guidance" for healthy eating, healthy
  lifestyle, fitness/active lifestyle and meal variety.
- Use "short_term_general_guidance" when the user mentions a
  health or medical concern where condition-specific advice
  would require professional guidance.
- Do NOT create a fixed 7-day or 30-day plan.
"""

            assessment_text = generate_ai_response(assessment_prompt)

            assessment = clean_json_response(assessment_text)

            st.session_state.assessment = assessment

        # =================================================
        # STAGE 2 - SAFETY CHECK
        # =================================================

        with st.spinner("🛡️ Checking your dietary needs..."):

            safety_prompt = f"""
You are the Safety Agent for NutriGuide AI.

Review the user's information and the Assessment Agent's
result before nutrition guidance is generated.

USER INFORMATION:
{json.dumps(user_data, indent=2)}

ASSESSMENT:
{json.dumps(assessment, indent=2)}

Check:
1. Food allergies.
2. Foods the user avoids.
3. Dietary preferences.
4. Health or medical concerns.
5. Age-related safety.
6. Whether professional advice should be recommended.

IMPORTANT:
- Never diagnose.
- Never prescribe a medical treatment diet.
- Never recommend dangerous or highly restrictive diets.
- Never provide weight-loss targets or calorie restriction.
- For users under 18, avoid weight-focused dieting advice.
- For health/medical concerns, recommend a qualified healthcare
  professional or registered dietitian for condition-specific
  advice.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "status": "safe_to_continue",
  "allergy_restrictions": [],
  "dietary_restrictions": [],
  "foods_to_avoid": [],
  "safety_flags": [],
  "meal_planning_rules": [],
  "professional_advice_recommended": false
}}

STATUS OPTIONS:
- "safe_to_continue"
- "continue_with_caution"
- "professional_review_recommended"
"""

            safety_text = generate_ai_response(safety_prompt)

            safety_result = clean_json_response(safety_text)

            st.session_state.safety_result = safety_result

        # =================================================
        # STAGE 3 - NUTRITION GUIDANCE
        # =================================================

        with st.spinner("🍽️ Preparing your nutrition guidance..."):

            guidance_prompt = f"""
You are the Nutrition Guidance Agent for NutriGuide AI.

Create personalised GENERAL nutrition guidance using the
information passed from the previous workflow stages.

USER INFORMATION:
{json.dumps(user_data, indent=2)}

ASSESSMENT:
{json.dumps(assessment, indent=2)}

SAFETY CHECK:
{json.dumps(safety_result, indent=2)}

IMPORTANT RULES:
- This is general nutrition education, not medical advice.
- Do not diagnose diseases or health conditions.
- Do not prescribe treatment diets.
- Do not provide weight-loss or weight-gain targets.
- Do not provide calorie restriction targets.
- Do not encourage restrictive eating.
- Do not create a fixed 7-day plan.
- Do not create a fixed 30-day plan.
- Do not mention a specific duration such as "follow this for
  one week".
- Instead, provide flexible ongoing guidance and meal ideas.
- Respect all allergies and foods the user avoids.
- Respect dietary preferences.
- Use practical, familiar and culturally appropriate foods
  where possible.
- Keep meals balanced and varied.
- For users under 18, focus on healthy growth, regular meals,
  balanced food choices and overall wellbeing rather than
  weight change.
- If a medical/health concern is present, provide only general
  nutrition information and clearly recommend a qualified
  healthcare professional or registered dietitian for
  condition-specific advice.
- Do not claim that food can cure or treat a medical condition.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "plan_title": "Personalised Nutrition Guidance",
  "guidance_type": "Long-term healthy lifestyle guidance",
  "duration": "Ongoing guidance - no fixed duration",
  "important_safety_note": "Short safety message.",
  "breakfast_ideas": [
    "Breakfast idea 1",
    "Breakfast idea 2",
    "Breakfast idea 3",
    "Breakfast idea 4"
  ],
  "lunch_ideas": [
    "Lunch idea 1",
    "Lunch idea 2",
    "Lunch idea 3",
    "Lunch idea 4"
  ],
  "snack_ideas": [
    "Snack idea 1",
    "Snack idea 2",
    "Snack idea 3",
    "Snack idea 4"
  ],
  "dinner_ideas": [
    "Dinner idea 1",
    "Dinner idea 2",
    "Dinner idea 3",
    "Dinner idea 4"
  ],
  "nutrition_tips": [
    "General nutrition tip 1",
    "General nutrition tip 2",
    "General nutrition tip 3",
    "General nutrition tip 4",
    "General nutrition tip 5"
  ]
}}
"""

            guidance_text = generate_ai_response(guidance_prompt)

            guidance = clean_json_response(guidance_text)

            st.session_state.guidance = guidance

        # ------------------------------------------------
        # SAVE WORKFLOW CONTEXT
        # ------------------------------------------------

        st.session_state.workflow_context = {
            "user_data": user_data,
            "assessment": assessment,
            "safety_result": safety_result,
            "guidance": guidance,
        }

        st.session_state.page = "results"

        st.rerun()

    except Exception as error:

        show_ai_error(error)

        st.divider()

        if st.button(
            "⬅️ Back to Home",
            key="assessment_error_back_home",
        ):

            reset_app()

            st.session_state.page = "home"

            st.rerun()


WIZARD_STEPS = ["Basic Info", "Preferences", "Goals & Health"]


def show_wizard_progress(current):
    """Render clear progress and labels for the assessment wizard."""
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
    st.markdown('<p class="lead">Your answers help create practical, safety-aware guidance. You can move back at any time without losing your progress.</p>', unsafe_allow_html=True)

    current = st.session_state.wizard_step
    data = st.session_state.wizard_data
    show_wizard_progress(current)

    if current == 0:
        st.subheader("Your everyday profile")
        st.caption("Start with two simple details so the guidance fits your stage of life and routine.")
        col1, col2 = st.columns(2)
        age_options = ["Under 18", "18–30", "31–45", "46–60", "60+"]
        activity_options = ["Low", "Moderate", "High"]
        with col1:
            data["age_group"] = st.selectbox("Age group", age_options, index=age_options.index(data.get("age_group", age_options[1])))
        with col2:
            data["activity_level"] = st.selectbox("Activity level", activity_options, index=activity_options.index(data.get("activity_level", "Moderate")))
        st.write("")
        _, next_col = st.columns([3, 1])
        with next_col:
            if st.button("Continue", type="primary", use_container_width=True, key="wizard_next_0"):
                st.session_state.wizard_step = 1
                st.rerun()

    elif current == 1:
        st.subheader("Food preferences and needs")
        st.caption("Include anything the guidance should always respect or avoid.")
        dietary_options = ["No specific preference", "Vegetarian", "Vegan", "Other"]
        data["dietary_preference"] = st.selectbox("Dietary preference", dietary_options, index=dietary_options.index(data.get("dietary_preference", dietary_options[0])))
        if data["dietary_preference"] == "Other":
            data["dietary_other"] = st.text_input("Describe your dietary preference", value=data.get("dietary_other", ""))
        left, right = st.columns(2)
        with left:
            data["food_allergies"] = st.text_area("Food allergies", value=data.get("food_allergies", ""), placeholder="For example: peanuts, eggs, milk")
            data["foods_to_avoid"] = st.text_area("Foods you avoid", value=data.get("foods_to_avoid", ""), placeholder="For example: very spicy food")
        with right:
            data["favourite_foods"] = st.text_area("Favourite or available foods", value=data.get("favourite_foods", ""), placeholder="For example: rice, roti, chicken, vegetables, fruit, yoghurt", height=178)
        st.write("")
        back_col, next_col = st.columns(2)
        with back_col:
            if st.button("Back", use_container_width=True, key="wizard_back_1"):
                st.session_state.wizard_step = 0
                st.rerun()
        with next_col:
            if st.button("Continue", type="primary", use_container_width=True, key="wizard_next_1"):
                st.session_state.wizard_step = 2
                st.rerun()

    elif current == 2:
        st.subheader("Goals and health context")
        st.caption("This final step helps balance your goal with appropriate safety guidance.")
        goal_options = ["Healthy eating", "Fitness / active lifestyle", "Better meal variety", "Healthy lifestyle", "General health concern", "Other"]
        data["goal"] = st.selectbox("What would you like help with?", goal_options, index=goal_options.index(data.get("goal", goal_options[0])))
        if data["goal"] == "Other":
            data["other_goal"] = st.text_input("Describe your goal", value=data.get("other_goal", ""))
        data["health_information"] = st.text_area("Health information or concerns", value=data.get("health_information", ""), placeholder="Optional. Add any concern the AI should consider.")
        st.markdown('<div class="notice"><strong>Safety first.</strong> NutriGuide AI provides general education and does not diagnose conditions or prescribe treatment diets.</div>', unsafe_allow_html=True)
        st.write("")
        back_col, submit_col = st.columns(2)
        with back_col:
            if st.button("Back", use_container_width=True, key="wizard_back_2"):
                st.session_state.wizard_step = 1
                st.rerun()
        with submit_col:
            submitted = st.button("Generate my guidance", type="primary", use_container_width=True, key="wizard_submit")
        if submitted:
            actual_preference = data.get("dietary_preference", "No specific preference")
            if actual_preference == "Other" and data.get("dietary_other", "").strip():
                actual_preference = data["dietary_other"].strip()
            actual_goal = data.get("goal", "Healthy eating")
            if actual_goal == "Other" and data.get("other_goal", "").strip():
                actual_goal = data["other_goal"].strip()
            user_data = {
                "age_group": data.get("age_group", ""),
                "activity_level": data.get("activity_level", ""),
                "dietary_preference": actual_preference,
                "food_allergies": data.get("food_allergies", "").strip(),
                "foods_to_avoid": data.get("foods_to_avoid", "").strip(),
                "favourite_foods": data.get("favourite_foods", "").strip(),
                "goal": actual_goal,
                "health_information": data.get("health_information", "").strip(),
            }
            st.session_state.user_data = user_data
            run_ai_workflow(user_data)


# ============================================================
# RESULTS PAGE
# ============================================================

def show_results():
    assessment = st.session_state.get("assessment", {})
    safety_result = st.session_state.get("safety_result", {})
    guidance = st.session_state.get("guidance", {})
    user_data = st.session_state.get("user_data", {})

    plan_title = escape(str(guidance.get("plan_title", "Personalised Nutrition Guidance")))
    guidance_type = escape(str(guidance.get("guidance_type", "General nutrition guidance")))
    duration = escape(str(guidance.get("duration", "Ongoing guidance")))
    safety_status = safety_result.get("status", "safe_to_continue")
    safety_label = "Safety clear" if safety_status == "safe_to_continue" else "Review advised"

    st.markdown(
        f'<div class="brandbar"><div class="brand"><span class="brand-mark">n</span>NutriGuide <span style="color:var(--leaf)">AI</span></div><span class="status-chip">{safety_label}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="eyebrow">Your nutrition dashboard</div>', unsafe_allow_html=True)
    st.title("Your personalised guidance is ready")
    st.markdown('<p class="lead">Review the key details first, then explore meal ideas, nutrition tips and your downloadable report.</p>', unsafe_allow_html=True)

    st.markdown(f'<div class="summary-card"><h2>{plan_title}</h2><p>{guidance_type}</p><p><strong>Approach:</strong> {duration}</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-heading"><h2>Profile overview</h2><p>Based on your latest assessment</p></div>', unsafe_allow_html=True)
    cols = st.columns(4)
    metrics = [
        ("Age group", user_data.get("age_group", "Not provided")),
        ("Activity", user_data.get("activity_level", "Not provided")),
        ("Diet", user_data.get("dietary_preference", "Not provided")),
        ("Primary goal", user_data.get("goal", "Not provided")),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.metric(label, value)

    st.markdown('<div class="section-heading"><h2>Safety and assessment</h2><p>Reviewed before meal guidance</p></div>', unsafe_allow_html=True)
    if safety_status == "professional_review_recommended":
        st.warning("Professional review is recommended for condition-specific dietary advice.")
    elif safety_status == "continue_with_caution":
        st.warning("Continue with caution and seek professional advice where appropriate.")
    else:
        st.success("Dietary preferences and safety information have been considered.")

    with st.expander("View personalised assessment", expanded=True):
        st.write(assessment.get("profile_summary", "No assessment summary available."))
        planning_considerations = assessment.get("planning_considerations", [])
        if planning_considerations:
            st.markdown("**Planning considerations**")
            display_list_items(planning_considerations)

    allergy_restrictions = safety_result.get("allergy_restrictions", [])
    dietary_restrictions = safety_result.get("dietary_restrictions", [])
    foods_to_avoid = safety_result.get("foods_to_avoid", [])
    safety_flags = safety_result.get("safety_flags", [])
    if allergy_restrictions or dietary_restrictions or foods_to_avoid or safety_flags:
        left, right = st.columns(2)
        with left:
            with st.expander("Allergies", expanded=True):
                display_list_items(allergy_restrictions, empty_message="No allergies reported.")
            with st.expander("Foods to avoid", expanded=True):
                display_list_items(foods_to_avoid, empty_message="No foods to avoid reported.")
        with right:
            with st.expander("Dietary restrictions", expanded=True):
                display_list_items(dietary_restrictions, empty_message="No additional restrictions.")
            with st.expander("Safety considerations", expanded=True):
                display_list_items(safety_flags, empty_message="No additional safety flags.")

    professional_advice = get_bool(assessment.get("professional_advice_recommended", False)) or get_bool(safety_result.get("professional_advice_recommended", False))
    if professional_advice:
        st.warning("For health or medical concerns, consult a qualified healthcare professional or registered dietitian for personalised advice.")

    st.markdown('<div class="section-heading"><h2>Your meal ideas</h2><p>Regenerate any category for fresh options</p></div>', unsafe_allow_html=True)
    meal_categories = [
        ("breakfast_ideas", "breakfast", "Breakfast"),
        ("lunch_ideas", "lunch", "Lunch"),
        ("snack_ideas", "snack", "Snacks"),
        ("dinner_ideas", "dinner", "Dinner"),
    ]
    meal_tabs = st.tabs([label for _, _, label in meal_categories])
    for tab, (guidance_key, meal_label, display_label) in zip(meal_tabs, meal_categories):
        with tab:
            current_ideas = guidance.get(guidance_key, [])
            display_list_items(current_ideas, empty_message="No ideas available yet.", card_style=True)
            if st.button(f"Regenerate {meal_label} ideas", key=f"regen_{meal_label}", use_container_width=True):
                with st.spinner(f"Finding new {meal_label} ideas..."):
                    try:
                        new_ideas = regenerate_meal_ideas(display_label.lower(), guidance_key, current_ideas)
                        if new_ideas:
                            guidance[guidance_key] = new_ideas
                            st.session_state.guidance = guidance
                            st.session_state.workflow_context["guidance"] = guidance
                            st.rerun()
                        else:
                            st.warning("Couldn't get new ideas this time — please try again.")
                    except Exception as error:
                        show_ai_error(error)

    st.markdown('<div class="section-heading"><h2>Everyday nutrition tips</h2><p>Small actions for steady progress</p></div>', unsafe_allow_html=True)
    display_list_items(guidance.get("nutrition_tips", []), empty_message="No nutrition tips available.")

    important_safety_note = guidance.get("important_safety_note", "These suggestions are general nutrition guidance.")
    st.info(important_safety_note)
    st.caption("For medical conditions or personalised dietary treatment, consult a qualified healthcare professional or registered dietitian.")

    st.markdown('<div class="section-heading"><h2>Your report</h2><p>Save a copy for easy reference</p></div>', unsafe_allow_html=True)
    try:
        pdf_data = create_pdf_report(user_data, assessment, safety_result, guidance)
        st.download_button(label="Download nutrition report", data=pdf_data, file_name="NutriGuide_AI_Report.pdf", mime="application/pdf", type="primary", use_container_width=True, key="download_nutrition_report")
    except Exception:
        st.error("The PDF report could not be generated. Please try again.")

    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create new assessment", type="primary", use_container_width=True, key="create_new_assessment_results"):
            reset_app()
            st.session_state.page = "assessment"
            st.rerun()
    with col2:
        if st.button("Back to home", use_container_width=True, key="back_to_home_results"):
            reset_app()
            st.session_state.page = "home"
            st.rerun()

    st.markdown('<div class="app-footer">NutriGuide AI · General educational nutrition guidance</div>', unsafe_allow_html=True)


# ============================================================
# PAGE ROUTING
# ============================================================

if st.session_state.page == "home":

    show_home()

elif st.session_state.page == "assessment":

    show_assessment()

elif st.session_state.page == "results":

    show_results()

else:

    reset_app()

    show_home()
