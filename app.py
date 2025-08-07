import streamlit as st
from logic import parse_answers

st.set_page_config(page_title="CarMatch AI", page_icon="🚗")
st.title("🚗 CarMatch AI - Your Car Recommendation Assistant")

# Initialize session state
if "question_index" not in st.session_state:
    st.session_state.question_index = 0

if "answers" not in st.session_state:
    st.session_state.answers = {}

# Define questions and example hints
questions = [
    ("Would you like a new or used car?", "e.g. new, used, leased"),
    ("What’s your maximum budget?", "e.g. 100,000"),
    ("What will you mostly use the car for?", "e.g. commuting, family, work"),
    ("How many people usually ride in the car?", "e.g. 1, 2, 5"),
    ("How many kilometers do you drive per year?", "5-10k, 10-20k, 20-30k, 30k+"),
    ("How long do you plan to keep the car?", "e.g. 2 years, 5 years, forever"),
    ("What are the top 2-3 things that matter most to you in a car?", "e.g. comfort, sporty, fuel economy"),
    ("What car are you currently driving?", "e.g. Kia Sportage 2016"),
    ("What do you like about your current car?", "e.g. comfort, design"),
    ("What do you dislike about your current car?", "e.g. fuel consumption"),
    ("Any special needs or features you’re looking for?", "e.g. high seating, tow bar, electric only"),
]

# Check if "sporty" is in the user's priorities and add follow-up question if needed
if (
    st.session_state.question_index == len(questions)
    and "sport" in st.session_state.answers.get("What are the top 2-3 things that matter most to you in a car?", "").lower()
    and "When you say 'sporty', what do you mean?" not in [q for q, _ in questions]
):
    questions.insert(
        st.session_state.question_index,
        ("When you say 'sporty', what do you mean?", "e.g. strong performance like Golf GTI, or fun-to-drive like Mazda MX-5"),
    )

# Show current question
if st.session_state.question_index < len(questions):
    q, hint = questions[st.session_state.question_index]
    st.subheader(q)
    st.caption(hint)

    with st.form(key="question_form"):
        user_input = st.text_input("Your answer:", key=f"input_{st.session_state.question_index}")
        submit = st.form_submit_button("Submit")

        if submit and user_input:
            st.session_state.answers[q] = user_input
            st.session_state.question_index += 1
            st.rerun()

# If all questions answered, show summary
elif st.session_state.question_index >= len(questions):
    st.success("✅ Thank you! Here's a summary of your preferences:")
    for q, a in st.session_state.answers.items():
        st.write(f"**{q}** 👉 {a}")

    # ניתוח התשובות
    st.subheader("🧠 Processed User Profile")
    profile = parse_answers(st.session_state.answers)

    for key, value in profile.items():
        st.write(f"**{key}**: {value}")
