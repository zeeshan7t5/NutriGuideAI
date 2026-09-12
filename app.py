import os
import json
import time
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

import streamlit as st
import requests
from streamlit_lottie import st_lottie
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

MODEL_NAME = "llama3-8b-8192"


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
        /* Smooth fade-in for the whole app */
        .block-container {
            max-width: 1150px;
            padding-top: 2rem;
            padding-bottom: 3rem;
            animation: fadeIn 0.8s ease-in-out;
        }

        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(10px); }
            100% { opacity: 1; transform: translateY(0); }
        }

        /* Gradient Main Title */
        h1 {
            font-weight: 800;
            letter-spacing: -1px;
            background: -webkit-linear-gradient(45deg, #2e8b57, #3cb371);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        h2, h3 {
            font-weight: 700;
            color: #2c3e50;
        }

        /* Modernize Metrics (Quick Overview) */
        div[data-testid="stMetric"] {
            border: none;
            padding: 20px;
            border-radius: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            transition: transform 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px);
        }

        /* Styling Inputs & Buttons */
        .stButton > button {
            border-radius: 30px;
            min-height: 50px;
            font-weight: 700;
            font-size: 1.1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 14px rgba(46, 139, 87, 0.4);
        }
        .stButton > button:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 20px rgba(46, 139, 87, 0.6);
        }

        textarea, input, div[data-baseweb="select"] > div {
            border-radius: 15px !important;
            border: 1px solid #e0e0e0 !important;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.02) !important;
        }

        /* Card Layouts with Hover Animations */
        .feature-card, .step-card, .summary-card {
            padding: 1.5rem;
            border: none;
            border-radius: 20px;
            background: #ffffff;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
            margin-bottom: 1rem;
        }
        
        .feature-card:hover, .step-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.12);
        }

        .meal-card {
            padding: 1.2rem;
            margin-bottom: 1rem;
            border-left: 5px solid #3cb371;
            border-radius: 12px;
            background: #f8fcf9;
            box-shadow: 0 4px 10px rgba(0,0,0,0.03);
            transition: all 0.2s ease;
        }
        .meal-card:hover {
            background: #eff9f2;
            transform: translateX(5px);
        }

        /* Footer */
        .app-footer {
            text-align: center;
            padding: 2rem 0;
            color: #888;
            font-size: 0.9rem;
            border-top: 1px solid #eee;
            margin-top: 3rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def show_home():
    st.title("🥗 NutriGuide AI")
    st.subheader("Your AI-Powered Nutrition Assistant")
    st.write("Get personalised general nutrition guidance based on your preferences, goals and dietary needs.")
    st.info("💡 This app provides general nutrition guidance. For medical advice, consult a professional.")

    st.divider()

    st.subheader("✨ What you can get")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <h3>🧠 Personalised Guidance</h3>
                <p>Guidance based on your food preferences, activity level, goals and dietary needs.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <h3>🍽️ Meal Ideas</h3>
                <p>Practical breakfast, lunch, snack and dinner ideas for everyday nutrition.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="feature-card">
                <h3>🛡️ Safety-Aware</h3>
                <p>Allergies, dietary restrictions and health concerns are considered before guidance is generated.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    st.subheader("🚀 How it works")
    step1, step2, step3 = st.columns(3)

    with step1:
        st.markdown(
            """
            <div class="step-card">
                <h3>1️⃣ Tell us about yourself</h3>
                <p>Share your basic dietary preferences, activity level, goals and food information.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with step2:
        st.markdown(
            """
            <div class="step-card">
                <h3>2️⃣ AI reviews your information</h3>
                <p>NutriGuide AI analyses your information and checks important dietary considerations.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with step3:
        st.markdown(
            """
            <div class="step-card">
                <h3>3️⃣ Get your guidance</h3>
                <p>Receive personalised meal ideas and practical general nutrition guidance.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    if st.button("🥗 Start Nutrition Assessment", type="primary", use_container_width=True, key="start_assessment_home"):
        st.session_state.page = "assessment"
        st.rerun()

    st.markdown(
        """
        <div class="app-footer">
            NutriGuide AI is for general educational nutrition guidance and is not a substitute for professional medical advice.
        </div>
        """,
        unsafe_allow_html=True,
    )

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

            if "503" in error_message or "unavailable" in error_message:
                if attempt < retries - 1:
                    time.sleep(3)
                    continue
                raise RuntimeError("GROQ_TEMPORARILY_UNAVAILABLE") from error

            # Passes the exact error message up to the UI
            raise RuntimeError(f"RAW_ERROR: {error_message}") from error

    raise RuntimeError("RAW_ERROR: Max retries exceeded")


def display_list_items(items, empty_message="No information available.", card_style=False):
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
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def pdf_text(value):
    """Safely convert text for ReportLab Paragraphs."""
    if value is None:
        return ""
    return escape(str(value)).replace("\n", "<br/>")


def create_pdf_report(user_data, assessment, safety_result, guidance):
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
        "ReportTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=20, spaceAfter=20
    )
    heading_style = ParagraphStyle(
        "ReportHeading", parent=styles["Heading2"], fontSize=14, spaceBefore=12, spaceAfter=8
    )
    body_style = ParagraphStyle(
        "ReportBody", parent=styles["BodyText"], fontSize=10, leading=14, spaceAfter=6
    )
    small_style = ParagraphStyle(
        "ReportSmall", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=5
    )

    story = []

    story.append(Paragraph("NutriGuide AI - Nutrition Report", title_style))
    story.append(Paragraph("Generated: " + datetime.now().strftime("%d %B %Y, %H:%M"), small_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Nutrition Profile", heading_style))

    profile_data = [
        ["Information", "Details"],
        ["Age Group", pdf_text(user_data.get("age_group", "Not provided"))],
        ["Activity Level", pdf_text(user_data.get("activity_level", "Not provided"))],
        ["Dietary Preference", pdf_text(user_data.get("dietary_preference", "Not provided"))],
        ["Goal", pdf_text(user_data.get("goal", "Not provided"))],
    ]

    profile_table = Table(profile_data, colWidths=[150, 320])
    profile_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(profile_table)
    story.append(Spacer(1, 12))

    allergies_input = user_data.get("food_allergies", "")
    avoid_input = user_data.get("foods_to_avoid", "")
    favourite_input = user_data.get("favourite_foods", "")
    health_input = user_data.get("health_information", "")

    if any([allergies_input, avoid_input, favourite_input, health_input]):
        story.append(Paragraph("Additional Information", heading_style))
        if allergies_input:
            story.append(Paragraph("<b>Food Allergies:</b> " + pdf_text(allergies_input), body_style))
        if avoid_input:
            story.append(Paragraph("<b>Foods Avoided:</b> " + pdf_text(avoid_input), body_style))
        if favourite_input:
            story.append(Paragraph("<b>Favourite / Available Foods:</b> " + pdf_text(favourite_input), body_style))
        if health_input:
            story.append(Paragraph("<b>Health Information:</b> " + pdf_text(health_input), body_style))

    story.append(Paragraph("2. AI Assessment", heading_style))
    story.append(Paragraph(pdf_text(assessment.get("profile_summary", "No assessment summary available.")), body_style))

    planning_items = assessment.get("planning_considerations", [])
    if planning_items:
        story.append(Paragraph("<b>Planning Considerations</b>", body_style))
        for item in planning_items:
            story.append(Paragraph("• " + pdf_text(item), body_style))

    story.append(Paragraph("3. Safety Information", heading_style))
    safety_status = safety_result.get("status", "safe_to_continue")
    story.append(Paragraph("<b>Status:</b> " + pdf_text(safety_status), body_style))

    safety_flags = safety_result.get("safety_flags", [])
    if safety_flags:
        story.append(Paragraph("<b>Safety Considerations</b>", body_style))
        for item in safety_flags:
            story.append(Paragraph("• " + pdf_text(item), body_style))

    allergy_restrictions = safety_result.get("allergy_restrictions", [])
    if allergy_restrictions:
        story.append(Paragraph("<b>Allergy Restrictions</b>", body_style))
        for item in allergy_restrictions:
            story.append(Paragraph("• " + pdf_text(item), body_style))

    dietary_restrictions = safety_result.get("dietary_restrictions", [])
    if dietary_restrictions:
        story.append(Paragraph("<b>Dietary Restrictions</b>", body_style))
        for item in dietary_restrictions:
            story.append(Paragraph("• " + pdf_text(item), body_style))

    foods_to_avoid = safety_result.get("foods_to_avoid", [])
    if foods_to_avoid:
        story.append(Paragraph("<b>Foods to Avoid</b>", body_style))
        for item in foods_to_avoid:
            story.append(Paragraph("• " + pdf_text(item), body_style))

    story.append(Paragraph("4. Meal Ideas", heading_style))
    meal_sections = [
        ("Breakfast", guidance.get("breakfast_ideas", [])),
        ("Lunch", guidance.get("lunch_ideas", [])),
        ("Snacks", guidance.get("snack_ideas", [])),
        ("Dinner", guidance.get("dinner_ideas", [])),
    ]

    for meal_name, meal_items in meal_sections:
        story.append(Paragraph(f"<b>{meal_name}</b>", body_style))
        if meal_items:
            if not isinstance(meal_items, list):
                meal_items = [meal_items]
            for item in meal_items:
                story.append(Paragraph("• " + pdf_text(item), body_style))
        else:
            story.append(Paragraph("No meal ideas available.", body_style))

    story.append(Paragraph("5. General Nutrition Tips", heading_style))
    nutrition_tips = guidance.get("nutrition_tips", [])
    if nutrition_tips:
        if not isinstance(nutrition_tips, list):
            nutrition_tips = [nutrition_tips]
        for item in nutrition_tips:
            story.append(Paragraph("• " + pdf_text(item), body_style))
    else:
        story.append(Paragraph("No nutrition tips available.", body_style))

    important_note = guidance.get("important_safety_note", "")
    if important_note:
        story.append(Paragraph("Important Safety Note", heading_style))
        story.append(Paragraph(pdf_text(important_note), body_style))

    story.append(Spacer(1, 15))
    story.append(
        Paragraph(
            "<b>Disclaimer:</b> This report provides general educational nutrition information and is not a substitute for professional medical advice. For medical conditions or personalised dietary treatment, consult a qualified healthcare professional or registered dietitian.",
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
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.title("🥗 NutriGuide AI")
        st.subheader("Your AI-Powered Nutrition Assistant")
        st.write("Get personalised general nutrition guidance based on your preferences, goals and dietary needs.")
        st.info("💡 This app provides general nutrition guidance. For medical advice, consult a professional.")
        
    with col2:
        # Load a free animated food graphic
        lottie_url = "[https://lottie.host/020bd926-2a7f-4bba-9577-fb1777265a7f/p1yWpY1j7c.json](https://lottie.host/020bd926-2a7f-4bba-9577-fb1777265a7f/p1yWpY1j7c.json)"
        lottie_anim = load_lottieurl(lottie_url)
        if lottie_anim:
            st_lottie(lottie_anim, height=250, key="food_animation")

    st.divider()

    st.subheader("✨ What you can get")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <h3>🧠 Personalised Guidance</h3>
                <p>Guidance based on your food preferences, activity level, goals and dietary needs.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <h3>🍽️ Meal Ideas</h3>
                <p>Practical breakfast, lunch, snack and dinner ideas for everyday nutrition.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="feature-card">
                <h3>🛡️ Safety-Aware</h3>
                <p>Allergies, dietary restrictions and health concerns are considered before guidance is generated.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    st.subheader("🚀 How it works")
    step1, step2, step3 = st.columns(3)

    with step1:
        st.markdown(
            """
            <div class="step-card">
                <h3>1️⃣ Tell us about yourself</h3>
                <p>Share your basic dietary preferences, activity level, goals and food information.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with step2:
        st.markdown(
            """
            <div class="step-card">
                <h3>2️⃣ AI reviews your information</h3>
                <p>NutriGuide AI analyses your information and checks important dietary considerations.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with step3:
        st.markdown(
            """
            <div class="step-card">
                <h3>3️⃣ Get your guidance</h3>
                <p>Receive personalised meal ideas and practical general nutrition guidance.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    if st.button("🥗 Start Nutrition Assessment", type="primary", use_container_width=True, key="start_assessment_home"):
        st.session_state.page = "assessment"
        st.rerun()

    st.markdown(
        """
        <div class="app-footer">
            NutriGuide AI is for general educational nutrition guidance and is not a substitute for professional medical advice.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# NUTRITION ASSESSMENT PAGE
# ============================================================

def show_assessment():
    st.title("📝 Nutrition Assessment")
    st.write("Tell us a little about your nutrition preferences and goals. This information will be used to prepare general personalised guidance.")
    st.divider()

    with st.form("nutrition_assessment_form"):
        st.subheader("👤 Basic Information")
        col1, col2 = st.columns(2)
        with col1:
            age_group = st.selectbox("Age Group", ["Under 18", "18–30", "31–45", "46–60", "60+"])
        with col2:
            activity_level = st.selectbox("Activity Level", ["Low", "Moderate", "High"])

        st.subheader("🥗 Dietary Preferences")
        dietary_preference = st.selectbox("Dietary Preference", ["No specific preference", "Vegetarian", "Vegan", "Other"])
        
        dietary_other = ""
        if dietary_preference == "Other":
            dietary_other = st.text_input("Please describe your dietary preference")

        food_allergies = st.text_area("Food Allergies", placeholder="Example: peanuts, eggs, milk")
        foods_to_avoid = st.text_area("Foods You Avoid", placeholder="Example: very spicy food, certain vegetables")
        favourite_foods = st.text_area("Favourite / Available Foods", placeholder="Example: rice, roti, chicken, vegetables, fruit, yoghurt")

        st.subheader("🎯 Your Goal")
        goal = st.selectbox("What would you like help with?", ["Healthy eating", "Fitness / active lifestyle", "Better meal variety", "Healthy lifestyle", "General health concern", "Other"])
        
        other_goal = ""
        if goal == "Other":
            other_goal = st.text_input("Please describe your goal")

        health_information = st.text_area("Health Information / Concerns", placeholder="Optional. Mention any health concern you want the AI to consider.")

        st.divider()
        submitted = st.form_submit_button("🧠 Generate Nutrition Guidance", type="primary", use_container_width=True)

    if submitted:
        actual_preference = dietary_other.strip() if (dietary_preference == "Other" and dietary_other.strip()) else dietary_preference
        actual_goal = other_goal.strip() if (goal == "Other" and other_goal.strip()) else goal

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

        try:
            with st.spinner("🧠 Analysing your information..."):
                assessment_prompt = f"""
You are the Assessment Agent for NutriGuide AI. Your job is to analyse the user's nutrition information and prepare a structured profile.
USER INFORMATION: {json.dumps(user_data, indent=2)}

IMPORTANT SAFETY RULES:
- This app provides general nutrition education. Do not diagnose conditions or prescribe diets.
- No restrictive weight-loss plans, targets, or calorie tracking.
- Respect allergies and age bounds.
Return ONLY valid JSON using exactly this structure:
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
"""
                assessment_text = generate_ai_response(assessment_prompt)
                assessment = clean_json_response(assessment_text)
                st.session_state.assessment = assessment

            with st.spinner("🛡️ Checking your dietary needs..."):
                safety_prompt = f"""
You are the Safety Agent for NutriGuide AI. Review the user's information and Assessment before guidance is generated.
USER INFORMATION: {json.dumps(user_data, indent=2)}
ASSESSMENT: {json.dumps(assessment, indent=2)}

Return ONLY valid JSON using exactly this structure:
{{
  "status": "safe_to_continue",
  "allergy_restrictions": [],
  "dietary_restrictions": [],
  "foods_to_avoid": [],
  "safety_flags": [],
  "meal_planning_rules": [],
  "professional_advice_recommended": false
}}
"""
                safety_text = generate_ai_response(safety_prompt)
                safety_result = clean_json_response(safety_text)
                st.session_state.safety_result = safety_result

            with st.spinner("🍽️ Preparing your nutrition guidance..."):
                guidance_prompt = f"""
You are the Nutrition Guidance Agent for NutriGuide AI. Create personalised GENERAL nutrition guidance.
USER INFORMATION: {json.dumps(user_data, indent=2)}
ASSESSMENT: {json.dumps(assessment, indent=2)}
SAFETY CHECK: {json.dumps(safety_result, indent=2)}

Return ONLY valid JSON using exactly this structure:
{{
  "plan_title": "Personalised Nutrition Guidance",
  "guidance_type": "Long-term healthy lifestyle guidance",
  "duration": "Ongoing guidance - no fixed duration",
  "important_safety_note": "Short safety message.",
  "breakfast_ideas": ["idea 1", "idea 2", "idea 3"],
  "lunch_ideas": ["idea 1", "idea 2", "idea 3"],
  "snack_ideas": ["idea 1", "idea 2", "idea 3"],
  "dinner_ideas": ["idea 1", "idea 2", "idea 3"],
  "nutrition_tips": ["tip 1", "tip 2", "tip 3"]
}}
"""
                guidance_text = generate_ai_response(guidance_prompt)
                guidance = clean_json_response(guidance_text)
                st.session_state.guidance = guidance

            st.session_state.workflow_context = {
                "user_data": user_data,
                "assessment": assessment,
                "safety_result": safety_result,
                "guidance": guidance,
            }

            # Celebration UI block
            st.toast("Success! Your nutrition plan is ready.", icon="🎉")
            st.balloons()
            time.sleep(2) 

            st.session_state.page = "results"
            st.rerun()

        except Exception as error:
            error_code = str(error)
            if error_code == "INVALID_API_KEY":
                st.error("🔑 Your Groq API key is invalid or not authorised.")
                st.info("Please check GROQ_API_KEY in your Streamlit Secrets and try again.")
            elif error_code == "API_QUOTA_EXCEEDED":
                st.warning("⏳ Groq API rate limit or quota has been reached.")
            elif error_code == "GROQ_TEMPORARILY_UNAVAILABLE":
                st.warning("🔄 Groq service is temporarily unavailable.")
            elif error_code == "INVALID_JSON":
                st.error("📄 The AI returned an unexpected response format.")
            else:
                st.error(f"⚠️ RAW ERROR DETAILS: {str(error)}")
            
            st.divider()
            if st.button("⬅️ Back to Home", key="assessment_error_back_home"):
                reset_app()
                st.session_state.page = "home"
                st.rerun()


# ============================================================
# RESULTS PAGE
# ============================================================

def show_results():
    assessment = st.session_state.get("assessment", {})
    safety_result = st.session_state.get("safety_result", {})
    guidance = st.session_state.get("guidance", {})
    user_data = st.session_state.get("user_data", {})

    st.title("📊 Nutrition Dashboard")
    st.write("Your personalised general nutrition guidance is ready to review.")
    st.divider()

    plan_title = guidance.get("plan_title", "Personalised Nutrition Guidance")
    guidance_type = guidance.get("guidance_type", "General nutrition guidance")
    duration = guidance.get("duration", "Ongoing guidance")

    st.markdown(
        f"""
        <div class="summary-card">
            <h2>🌱 {plan_title}</h2>
            <p>{guidance_type}</p>
            <p><strong>Approach:</strong> {duration}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("👤 Quick Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Age Group", user_data.get("age_group", "Not provided"))
    with col2:
        st.metric("Activity", user_data.get("activity_level", "Not provided"))
    with col3:
        st.metric("Diet", user_data.get("dietary_preference", "Not provided"))
    with col4:
        st.metric("Goal", user_data.get("goal", "Not provided"))

    st.divider()
    st.subheader("🛡️ Safety Status")

    safety_status = safety_result.get("status", "safe_to_continue")
    if safety_status == "professional_review_recommended":
        st.warning("👩‍⚕️ Professional review is recommended for condition-specific dietary advice.")
    elif safety_status == "continue_with_caution":
        st.warning("⚠️ Continue with caution and seek professional advice where appropriate.")
    else:
        st.success("✅ Dietary preferences and safety information have been considered.")

    with st.expander("🧠 View AI Assessment", expanded=True):
        st.write(assessment.get("profile_summary", "No assessment summary available."))
        planning_considerations = assessment.get("planning_considerations", [])
        if planning_considerations:
            st.markdown("**Planning Considerations**")
            display_list_items(planning_considerations)

    allergy_restrictions = safety_result.get("allergy_restrictions", [])
    dietary_restrictions = safety_result.get("dietary_restrictions", [])
    foods_to_avoid = safety_result.get("foods_to_avoid", [])
    safety_flags = safety_result.get("safety_flags", [])

    if allergy_restrictions or dietary_restrictions or foods_to_avoid or safety_flags:
        st.subheader("🚫 Dietary Restrictions")
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("🚫 Allergies", expanded=True):
                display_list_items(allergy_restrictions, empty_message="No allergies reported.")
            with st.expander("🥗 Foods to Avoid", expanded=True):
                display_list_items(foods_to_avoid, empty_message="No foods to avoid reported.")
        with col2:
            with st.expander("🥗 Dietary Restrictions", expanded=True):
                display_list_items(dietary_restrictions, empty_message="No additional dietary restrictions.")
            with st.expander("⚠️ Safety Considerations", expanded=True):
                display_list_items(safety_flags, empty_message="No additional safety flags.")

    professional_advice = get_bool(assessment.get("professional_advice_recommended", False)) or get_bool(safety_result.get("professional_advice_recommended", False))
    if professional_advice:
        st.warning("👩‍⚕️ For health or medical concerns, please consult a qualified healthcare professional or registered dietitian.")

    st.divider()
    st.subheader("🍽️ Meal Ideas")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🍳 Breakfast")
        display_list_items(guidance.get("breakfast_ideas", []), card_style=True)
    with col2:
        st.markdown("### 🥗 Lunch")
        display_list_items(guidance.get("lunch_ideas", []), card_style=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🍎 Snacks")
        display_list_items(guidance.get("snack_ideas", []), card_style=True)
    with col2:
        st.markdown("### 🍽️ Dinner")
        display_list_items(guidance.get("dinner_ideas", []), card_style=True)

    st.divider()
    st.subheader("💡 General Nutrition Tips")
    display_list_items(guidance.get("nutrition_tips", []), empty_message="No nutrition tips available.")

    st.divider()
    important_safety_note = guidance.get("important_safety_note", "These suggestions are general nutrition guidance.")
    st.info(important_safety_note)
    st.info("🥗 For medical conditions or personalised dietary treatment, consult a qualified healthcare professional.")

    st.divider()
    st.subheader("📥 Your Report")
    st.write("Download your current nutrition assessment and AI-generated guidance as a PDF.")

    try:
        pdf_data = create_pdf_report(user_data, assessment, safety_result, guidance)
        st.download_button(
            label="📥 Download Nutrition Report",
            data=pdf_data,
            file_name="NutriGuide_AI_Report.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key="download_nutrition_report",
        )
    except Exception as error:
        st.error("⚠️ The PDF report could not be generated.")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Create New Assessment", type="primary", use_container_width=True):
            reset_app()
            st.session_state.page = "assessment"
            st.rerun()
    with col2:
        if st.button("🏠 Back to Home", use_container_width=True):
            reset_app()
            st.session_state.page = "home"
            st.rerun()

    st.markdown(
        """
        <div class="app-footer">
            NutriGuide AI • General educational nutrition guidance
        </div>
        """,
        unsafe_allow_html=True,
    )


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
