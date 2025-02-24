import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from llm_api import generate_questions, generate_report
from config import SKILL_CATEGORIES, CATEGORY_DETAILS, CORRECT_ANSWERS, SCORE_THRESHOLDS

def create_speedometer_chart(score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Overall Performance"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, SCORE_THRESHOLDS["Needs Improvement"]], 'color': "red"},
                {'range': [SCORE_THRESHOLDS["Needs Improvement"], SCORE_THRESHOLDS["Average"]], 'color': "yellow"},
                {'range': [SCORE_THRESHOLDS["Average"], SCORE_THRESHOLDS["Good"]], 'color': "lightgreen"},
                {'range': [SCORE_THRESHOLDS["Good"], SCORE_THRESHOLDS["Excellent"]], 'color': "green"}
            ]
        }
    ))
    return fig

def create_pie_chart(scores):
    fig = px.pie(
        values=list(scores.values()),
        names=list(scores.keys()),
        title="Score Distribution by Category",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    return fig

def create_bar_chart(scores):
    fig = px.bar(
        x=list(scores.keys()),
        y=list(scores.values()),
        title="Category-wise Performance",
        labels={'x': 'Categories', 'y': 'Score (%)'},
        color=list(scores.values()),
        color_continuous_scale='RdYlGn'
    )
    fig.update_layout(xaxis_tickangle=-45)
    return fig

def create_radar_chart(scores):
    categories = list(scores.keys())
    values = list(scores.values())
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        title="Skill Radar Chart"
    )
    return fig

def initialize_session_state():
    if 'current_phase' not in st.session_state:
        st.session_state.current_phase = "student_info"
    if 'questions' not in st.session_state:
        st.session_state.questions = {}
    if 'answers' not in st.session_state:
        st.session_state.answers = {}
    if 'current_category_index' not in st.session_state:
        st.session_state.current_category_index = 0
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0

def display_student_info_form():
    st.header("Student Information")
    with st.form("student_info_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name")
            email = st.text_input("Email")
        with col2:
            department = st.text_input("Department")
            year = st.selectbox("Year", ["1st Year", "2nd Year", "3rd Year", "4th Year"])
        
        if st.form_submit_button("Start Assessment"):
            if name and email and department:
                st.session_state.student_info = {
                    "name": name,
                    "email": email,
                    "department": department,
                    "year": year
                }
                st.session_state.current_phase = "generate_questions"
                st.rerun()
            else:
                st.error("Please fill in all required fields.")

def display_test():
    current_category = SKILL_CATEGORIES[st.session_state.current_category_index]
    
    # Generate questions if not already generated
    if current_category not in st.session_state.questions:
        with st.spinner(f"Generating questions for {current_category}..."):
            questions = generate_questions(current_category)
            if isinstance(questions, str):  # Error message
                st.error(f"Error generating questions: {questions}")
                return
            st.session_state.questions[current_category] = questions

    # Display progress
    st.header(f"Assessment: {current_category}")
    progress = (st.session_state.current_category_index * 5 + st.session_state.current_question_index + 1) / (len(SKILL_CATEGORIES) * 5)
    st.progress(progress)
    st.write(f"Question {st.session_state.current_question_index + 1} of 5")
    
    try:
        current_question = st.session_state.questions[current_category][st.session_state.current_question_index]
        
        with st.form("question_form"):
            st.write("### Question:")
            st.write(current_question["question"])
            if "focus_area" in current_question:
                st.write(f"*Focus Area: {current_question['focus_area']}*")
            
            answer = st.radio(
                "Select your answer:",
                list(current_question["options"].keys()),
                format_func=lambda x: current_question["options"][x]
            )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.form_submit_button("Next Question"):
                    # Store answer
                    if current_category not in st.session_state.answers:
                        st.session_state.answers[current_category] = []
                    st.session_state.answers[current_category].append(answer)
                    
                    # Show if answer was correct and explanation
                    if answer == current_question["correct"]:
                        st.success("✅ Correct!")
                    else:
                        st.error(f"❌ Incorrect. The correct answer was: {current_question['options'][current_question['correct']]}")
                    
                    if "explanation" in current_question:
                        st.info(f"Explanation: {current_question['explanation']}")
                    
                    # Move to next question or category
                    if st.session_state.current_question_index < 4:
                        st.session_state.current_question_index += 1
                    else:
                        st.session_state.current_question_index = 0
                        st.session_state.current_category_index += 1
                        
                        if st.session_state.current_category_index >= len(SKILL_CATEGORIES):
                            st.session_state.current_phase = "generate_report"
                    st.rerun()
                    
    except Exception as e:
        st.error(f"Error displaying question: {str(e)}")
        st.write("Current question data:", current_question)

def calculate_scores():
    scores = {}
    for category in SKILL_CATEGORIES:
        category_answers = st.session_state.answers.get(category, [])
        if category_answers:
            correct_count = sum(
                1 for i, ans in enumerate(category_answers)
                if ans == CORRECT_ANSWERS[f"{category}_{i}"]
            )
            scores[category] = (correct_count / len(category_answers)) * 100
    return scores

def display_report():
    scores = calculate_scores()
    overall_score = sum(scores.values()) / len(scores)
    
    st.header("Skill Gap Analysis Report")
    
    # Student Information
    st.subheader("Student Information")
    col1, col2 = st.columns(2)
    with col1:
        for key in ['name', 'email']:
            st.write(f"**{key.title()}:** {st.session_state.student_info[key]}")
    with col2:
        for key in ['department', 'year']:
            st.write(f"**{key.title()}:** {st.session_state.student_info[key]}")
    
    # Visualizations
    st.subheader("Performance Analysis")
    
    # Speedometer and Radar charts
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(create_speedometer_chart(overall_score))
    with col2:
        st.plotly_chart(create_radar_chart(scores))
    
    # Pie and Bar charts
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(create_pie_chart(scores))
    with col2:
        st.plotly_chart(create_bar_chart(scores))
    
    # Detailed scores
    st.subheader("Detailed Scores")
    score_df = pd.DataFrame(list(scores.items()), columns=['Category', 'Score'])
    
    # Format the scores with color coding using custom HTML
    def color_score(score):
        if score >= SCORE_THRESHOLDS["Excellent"]:
            color = "green"
        elif score >= SCORE_THRESHOLDS["Good"]:
            color = "lightgreen"
        elif score >= SCORE_THRESHOLDS["Average"]:
            color = "yellow"
        else:
            color = "red"
        return f'background-color: {color}'
    
    # Display scores with custom formatting
    st.write("### Score Breakdown")
    for idx, row in score_df.iterrows():
        score = row['Score']
        if score >= SCORE_THRESHOLDS["Excellent"]:
            emoji = "🌟"
        elif score >= SCORE_THRESHOLDS["Good"]:
            emoji = "✅"
        elif score >= SCORE_THRESHOLDS["Average"]:
            emoji = "⚠️"
        else:
            emoji = "❌"
        
        st.write(f"{emoji} **{row['Category']}:** {score:.1f}%")
    
    # Generate and display detailed report
    st.subheader("Detailed Analysis")
    with st.spinner("Generating detailed report..."):
        report = generate_report(scores, st.session_state.student_info)
        st.markdown(report)
    
    # Download options
    st.subheader("Download Report")
    col1, col2 = st.columns(2)
    with col1:
        report_csv = score_df.to_csv(index=False)
        st.download_button(
            label="Download Scores (CSV)",
            data=report_csv,
            file_name="assessment_scores.csv",
            mime="text/csv"
        )
    with col2:
        full_report = f"""# Skill Gap Analysis Report
        
## Student Information
Name: {st.session_state.student_info['name']}
Email: {st.session_state.student_info['email']}
Department: {st.session_state.student_info['department']}
Year: {st.session_state.student_info['year']}

## Overall Score: {overall_score:.1f}%

## Detailed Scores
{score_df.to_markdown()}

## Detailed Analysis
{report}
"""
        st.download_button(
            label="Download Full Report (MD)",
            data=full_report,
            file_name="full_assessment_report.md",
            mime="text/markdown"
        )

def main():
    st.set_page_config(page_title="Skill Gap Assessment", layout="wide")
    
    st.title("Skill Gap Assessment")
    
    initialize_session_state()
    
    if st.session_state.current_phase == "student_info":
        display_student_info_form()
    elif st.session_state.current_phase == "generate_questions":
        display_test()
    elif st.session_state.current_phase == "generate_report":
        display_report()

if __name__ == "__main__":
    main()