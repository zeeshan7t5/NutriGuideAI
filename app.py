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

MODEL_NAME = "llama-3.3-70b-versatile"


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

        .block-container {
            max-width: 1150px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        h1 {
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        h2,
        h3 {
            font-weight: 650;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.22);
            padding: 18px;
            border-radius: 16px;
            background: rgba(128, 128, 128, 0.04);
        }

        div[data-testid="stMetricLabel"] {
            font-weight: 600;
        }

        .stButton > button {
            border-radius: 10px;
            min-height: 45px;
            font-weight: 600;
        }

        div[data-baseweb="select"] > div {
            border-radius: 10px;
        }

        textarea,
        input {
            border-radius: 10px !important;
        }

        div[data-testid="stAlert"] {
            border-radius: 12px;
        }

        .feature-card {
            padding: 1.25rem;
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 16px;
            min-height: 180px;
            background: rgba(128, 128, 128, 0.035);
        }

        .feature-card h3 {
            margin-bottom: 0.6rem;
        }

        .step-card {
            padding: 1.2rem;
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 14px;
            min-height: 165px;
            background: rgba(128, 128, 128, 0.025);
        }

        .step-card h3 {
            margin-bottom: 0.6rem;
        }

        .meal-card {
            padding: 1rem 1.1rem;
            margin-bottom: 0.7rem;
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 12px;
            background: rgba(128, 128, 128, 0.035);
        }

        .summary-card {
            padding: 1.25rem;
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 16px;
            background: rgba(128, 128, 128, 0.035);
            margin-bottom: 1rem;
        }

        .small-note {
            font-size: 0.9rem;
            opacity: 0.78;
        }

        .app-footer {
            text-align: center;
            padding: 1.5rem 0 0.5rem 0;
            opacity: 0.7;
            font-size: 0.85rem;
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
            raise RuntimeError("INVALID_JSON") from error

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
                raise RuntimeError("Groq returned an empty response.")

            return content

        except Exception as error:
            error_message = str(error).lower()

            if (
                "401" in error_message
                or "unauthorized" in error_message
                or "api key" in error_message
            ):
                raise RuntimeError("INVALID_API_KEY") from error

            if (
                "429" in error_message
                or "rate_limit" in error_message
                or "quota" in error_message
            ):
                raise RuntimeError("API_QUOTA_EXCEEDED") from error

            if (
                "503" in error_message
                or "unavailable" in error_message
            ):
                if attempt < retries - 1:
                    time.sleep(3)
                    continue

                raise RuntimeError("GROQ_TEMPORARILY_UNAVAILABLE") from error

            raise RuntimeError("GROQ_REQUEST_FAILED") from error

    raise RuntimeError("GROQ_REQUEST_FAILED")


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

    st.title("🥗 NutriGuide AI")

    st.subheader(
        "Your AI-Powered Nutrition Assistant"
    )

    st.write(
        "Get personalised general nutrition guidance based on "
        "your preferences, goals and dietary needs."
    )

    st.divider()

    st.info(
        "💡 This app provides general nutrition guidance. "
        "For medical or condition-specific dietary advice, "
        "please consult a qualified healthcare professional."
    )

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    st.subheader("✨ What you can get")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <h3>🧠 Personalised Guidance</h3>
                <p>
                    Guidance based on your food preferences,
                    activity level, goals and dietary needs.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <h3>🍽️ Meal Ideas</h3>
                <p>
                    Practical breakfast, lunch, snack and dinner
                    ideas for everyday nutrition.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="feature-card">
                <h3>🛡️ Safety-Aware</h3>
                <p>
                    Allergies, dietary restrictions and health
                    concerns are considered before guidance is generated.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # --------------------------------------------------------
    # HOW IT WORKS
    # --------------------------------------------------------

    st.subheader("🚀 How it works")

    step1, step2, step3 = st.columns(3)

    with step1:
        st.markdown(
            """
            <div class="step-card">
                <h3>1️⃣ Tell us about yourself</h3>
                <p>
                    Share your basic dietary preferences,
                    activity level, goals and food information.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with step2:
        st.markdown(
            """
            <div class="step-card">
                <h3>2️⃣ AI reviews your information</h3>
                <p>
                    NutriGuide AI analyses your information
                    and checks important dietary considerations.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with step3:
        st.markdown(
            """
            <div class="step-card">
                <h3>3️⃣ Get your guidance</h3>
                <p>
                    Receive personalised meal ideas and
                    practical general nutrition guidance.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    if st.button(
        "🥗 Start Nutrition Assessment",
        type="primary",
        use_container_width=True,
        key="start_assessment_home",
    ):
        st.session_state.page = "assessment"
        st.rerun()

    st.markdown(
        """
        <div class="app-footer">
            NutriGuide AI is for general educational nutrition
            guidance and is not a substitute for professional medical advice.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# NUTRITION ASSESSMENT PAGE
# ============================================================

def show_assessment():

    st.title("📝 Nutrition Assessment")

    st.write(
        "Tell us a little about your nutrition preferences and "
        "goals. This information will be used to prepare general "
        "personalised guidance."
    )

    st.divider()

    with st.form("nutrition_assessment_form"):

        st.subheader("👤 Basic Information")

        col1, col2 = st.columns(2)

        with col1:
            age_group = st.selectbox(
                "Age Group",
                [
                    "Under 18",
                    "18–30",
                    "31–45",
                    "46–60",
                    "60+",
                ],
            )

        with col2:
            activity_level = st.selectbox(
                "Activity Level",
                [
                    "Low",
                    "Moderate",
                    "High",
                ],
            )

        st.subheader("🥗 Dietary Preferences")

        dietary_preference = st.selectbox(
            "Dietary Preference",
            [
                "No specific preference",
                "Vegetarian",
                "Vegan",
                "Other",
            ],
        )

        dietary_other = ""

        if dietary_preference == "Other":
            dietary_other = st.text_input(
                "Please describe your dietary preference"
            )

        food_allergies = st.text_area(
            "Food Allergies",
            placeholder="Example: peanuts, eggs, milk",
        )

        foods_to_avoid = st.text_area(
            "Foods You Avoid",
            placeholder=(
                "Example: very spicy food, certain vegetables"
            ),
        )

        favourite_foods = st.text_area(
            "Favourite / Available Foods",
            placeholder=(
                "Example: rice, roti, chicken, vegetables, "
                "fruit, yoghurt"
            ),
        )

        st.subheader("🎯 Your Goal")

        goal = st.selectbox(
            "What would you like help with?",
            [
                "Healthy eating",
                "Fitness / active lifestyle",
                "Better meal variety",
                "Healthy lifestyle",
                "General health concern",
                "Other",
            ],
        )

        other_goal = ""

        if goal == "Other":
            other_goal = st.text_input(
                "Please describe your goal"
            )

        health_information = st.text_area(
            "Health Information / Concerns",
            placeholder=(
                "Optional. Mention any health concern you want "
                "the AI to consider."
            ),
        )

        st.divider()

        submitted = st.form_submit_button(
            "🧠 Generate Nutrition Guidance",
            type="primary",
            use_container_width=True,
        )

    if submitted:

        actual_preference = dietary_preference

        if (
            dietary_preference == "Other"
            and dietary_other.strip()
        ):
            actual_preference = dietary_other.strip()

        actual_goal = goal

        if goal == "Other" and other_goal.strip():
            actual_goal = other_goal.strip()

        user_data = {
            "age_group": age_group,
            "activity_level": activity_level,
            "dietary_preference": actual_preference,
            "food_allergies": food_allergies.strip(),
            "foods_to_avoid": foods_to_avoid.strip(),
            "favourite_foods": favourite_foods.strip(),
            "goal": actual_goal,
            "health_information": health_information.strip(),
        }

        st.session_state.user_data = user_data

        # ----------------------------------------------------
        # AI WORKFLOW
        # ----------------------------------------------------

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

                assessment_text = generate_ai_response(
                    assessment_prompt
                )

                assessment = clean_json_response(
                    assessment_text
                )

                st.session_state.assessment = assessment
                st.session_state.page = "results"
                st.rerun()

        except Exception as error:
            st.error(f"⚠️ An error occurred: {str(error)}")


# ============================================================
# RESULTS PAGE
# ============================================================

def show_results():

    st.title("📋 Your Personalised Guidance")

    st.divider()

    user_data = st.session_state.get("user_data", {})
    assessment = st.session_state.get("assessment", {})

    st.subheader("👤 Profile Summary")
    st.write(
        assessment.get("profile_summary", "No summary available.")
    )

    st.divider()

    if st.button("🔄 Start New Assessment", type="secondary"):
        reset_app()
        st.rerun()


# ============================================================
# MAIN APP ENTRY POINT
# ============================================================

def main():
    if st.session_state.page == "home":
        show_home()
    elif st.session_state.page == "assessment":
        show_assessment()
    elif st.session_state.page == "results":
        show_results()


if __name__ == "__main__":
    main()

```
