"""
app.py
Interactive Streamlit UI for PDF Quiz with Real Gemini AI Integration
"""
from engine import generate_questions_batch, analyze_answer, build_report
from datetime import datetime
import streamlit as st

from pdf_utils import extract_text, get_pdf_metadata
from engine import generate_question, analyze_answer, build_report


# =========================================================
# ⚙️ Page Configuration
# =========================================================
st.set_page_config(
    page_title="PDF Quiz - Hackathon",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 🔧 Session State Management
# =========================================================
def init_session_state():
    defaults = {
        "pdf_text": "",
        "pdf_meta": {},
        "questions": [],
        "current_q_index": 0,
        "history": [],
        "quiz_started": False,
        "quiz_finished": False,
        "show_hint": False,
        "hint_text": "",
        "last_eval": None,
        "filename": "",
        "answers": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session_state()


# =========================================================
# 🎨 Custom CSS
# =========================================================
st.markdown("""
<style>
    .main-title {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(90deg, #6366f1, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        text-align: center;
        color: #6b7280;
        margin-bottom: 1.5rem;
    }
    .question-card {
        background: linear-gradient(135deg, #f0f9ff, #e0e7ff);
        border-left: 5px solid #6366f1;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
        font-size: 1.15rem;
        font-weight: 600;
        color: #1e293b;
    }
    .feedback-box {
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-top: 0.8rem;
        font-weight: 500;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# 🎬 Main UI
# =========================================================
st.markdown('<div class="main-title">📚 AI PDF Quiz Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Upload a PDF, generate smart questions via Gemini AI, and receive real-time evaluation</div>', unsafe_allow_html=True)


# -------- Sidebar --------
with st.sidebar:
    st.header("⚙️ Settings")
    
    uploaded_file = st.file_uploader(
        "📄 Upload PDF Document",
        type=["pdf"],
        help="Upload your study material or lecture slides to generate quiz questions.",
    )
    
    num_questions = st.slider(
        "🔢 Number of Questions",
        min_value=1,
        max_value=5,
        value=3,
    )
    
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        start_btn = st.button("🚀 Start Quiz", use_container_width=True, type="primary")
    with col_b:
        reset_btn = st.button("🔄 Reset", use_container_width=True)


# -------- Start Button Handling --------
if start_btn:
    if uploaded_file is None:
        st.sidebar.error("⚠️ Please upload a PDF file first!")
    else:
        with st.spinner("⏳ Extracting text and generating questions with Gemini AI..."):
            text = extract_text(uploaded_file)
            meta = get_pdf_metadata(uploaded_file)
            
            questions = generate_questions_batch(text, count=num_questions)
            
            st.session_state.pdf_text = text
            st.session_state.pdf_meta = meta
            st.session_state.questions = questions
            st.session_state.current_q_index = 0
            st.session_state.history = []
            st.session_state.answers = []
            st.session_state.quiz_started = True
            st.session_state.quiz_finished = False
            st.session_state.last_eval = None
            st.session_state.show_hint = False
            st.session_state.filename = uploaded_file.name
        
        st.success("✅ Questions generated successfully!")
        st.rerun()


# -------- Reset Button Handling --------
if reset_btn:
    for k in ["pdf_text", "questions", "history", "answers", "last_eval"]:
        st.session_state[k] = [] if k in ["questions", "history", "answers"] else None
    st.session_state.current_q_index = 0
    st.session_state.quiz_started = False
    st.session_state.quiz_finished = False
    st.session_state.show_hint = False
    st.rerun()


# =========================================================
# 🎯 Quiz Area
# =========================================================
if st.session_state.quiz_started and not st.session_state.quiz_finished:
    total = len(st.session_state.questions)
    idx = st.session_state.current_q_index
    
    if idx < total:
        q = st.session_state.questions[idx]
        
        st.progress((idx) / total, text=f"Question {idx + 1} of {total}")
        
        st.markdown(
            f'<div class="question-card">❓ Question {idx + 1}: {q["question"]}</div>',
            unsafe_allow_html=True,
        )
        
        answer = st.text_area(
            "✍️ Your Answer:",
            key=f"answer_{idx}",
            height=140,
            placeholder="Type your answer here in detail...",
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit_btn = st.button("✅ Submit Answer", use_container_width=True, type="primary")
        with col2:
            skip_btn = st.button("⏭️ Skip Question", use_container_width=True)
            
        if submit_btn:
            if not answer.strip():
                st.warning("⚠️ Please enter an answer before submitting!")
            else:
                with st.spinner("🧠 Gemini is analyzing your answer..."):
                    evaluation = analyze_answer(
                        q["question"], q.get("key_points", []), answer
                    )
                
                st.session_state.last_eval = evaluation
                st.session_state.answers.append(answer)
                st.session_state.history.append({
                    "question": q["question"],
                    "topic": q.get("topic", "General"),
                    "verdict": evaluation.get("verdict", "far"),
                    "misconception": evaluation.get("misconception", ""),
                    "score_label": evaluation.get("verdict")
                })

        if st.session_state.last_eval:
            ev = st.session_state.last_eval
            verdict = ev.get("verdict", "far")
            
            color_map = {"correct": "#dcfce7", "close": "#fef3c7", "far": "#fee2e2"}
            border_map = {"correct": "#16a34a", "close": "#f59e0b", "far": "#dc2626"}
            text_map = {"correct": "#166534", "close": "#92400e", "far": "#991b1b"}
            label_map = {"correct": "Excellent (Correct)", "close": "Almost There (Close)", "far": "Needs Review (Far)"}
            
            st.markdown(
                f"""
                <div class="feedback-box" style="background:{color_map[verdict]};
                     border-left: 5px solid {border_map[verdict]};
                     color:{text_map[verdict]};">
                    <b>Evaluation: {label_map[verdict]}</b><br>
                    {ev.get('feedback', '')}<br>
                    <small>💡 Hint: {ev.get('hint', '—')}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            if st.button("➡️ Next Question", type="primary", key=f"next_{idx}"):
                st.session_state.current_q_index += 1
                st.session_state.last_eval = None
                if st.session_state.current_q_index >= total:
                    st.session_state.quiz_finished = True
                st.rerun()
                
        if skip_btn:
            st.session_state.answers.append("")
            st.session_state.history.append({
                "question": q["question"],
                "topic": q.get("topic", "General"),
                "verdict": "far",
                "misconception": "Question skipped."
            })
            st.session_state.current_q_index += 1
            st.session_state.last_eval = None
            if st.session_state.current_q_index >= total:
                st.session_state.quiz_finished = True
            st.rerun()


# =========================================================
# 📊 Final Report
# =========================================================
if st.session_state.quiz_finished:
    st.balloons()
    st.markdown("## 🎉 Quiz Completed!")
    st.markdown("### 📊 Performance Report by Gemini AI")
    
    with st.spinner("⏳ Generating final performance analytics..."):
        report = build_report(st.session_state.history)
    
    stats = report.get("stats", {})
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Correct Answers", stats.get("correct", 0))
    with col2:
        st.metric("🟧 Close Answers", stats.get("close", 0))
    with col3:
        st.metric("❓ Total Questions", len(st.session_state.questions))
    
    st.info(f"**Summary:** {report.get('summary', '—')}")
    
    if report.get("recommendation"):
        st.success(f"📌 **Recommendation:** {report.get('recommendation')}")
        
    with st.expander("🔍 Detailed Answer Breakdown", expanded=True):
        for i, (q, ans, h) in enumerate(zip(
            st.session_state.questions,
            st.session_state.answers,
            st.session_state.history
        ), 1):
            st.markdown(f"**Q{i}: {q['question']}**")
            st.markdown(f"- Your Answer: _{ans or '—'}_")
            st.markdown(f"- Verdict: **{h.get('verdict')}**")
            if h.get("misconception"):
                st.markdown(f"- Note: {h.get('misconception')}")
            st.divider()


st.divider()
st.caption("🚀 Gen AI Hackathon | Powered by Gemini 3.6 Flash & Streamlit")