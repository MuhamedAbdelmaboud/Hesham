import copy
import html

import streamlit as st

from engine import (
    analyze_answer,
    build_report,
    explain_gap,
    generate_question,
    next_difficulty,
)
from pdf_utils import extract_text

st.set_page_config(
    page_title="Hesham - Adaptive Assessment",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

START_DIFFICULTY = "medium"

DIFFICULTY_LABELS = {"easy": "🟢 Easy", "medium": "🟡 Medium", "hard": "🔴 Hard"}
COLOR_MAP = {"correct": "#dcfce7", "close": "#fef3c7", "far": "#fee2e2"}
BORDER_MAP = {"correct": "#16a34a", "close": "#f59e0b", "far": "#dc2626"}
TEXT_MAP = {"correct": "#166534", "close": "#92400e", "far": "#991b1b"}
LABEL_MAP = {
    "correct": "Excellent (Correct)",
    "close": "Almost There (Close)",
    "far": "Needs Review (Far)",
}

DEFAULTS = {
    "material": "",
    "file_name": "",
    "target": 5,
    "current_q": None,
    "difficulty": START_DIFFICULTY,
    "history": [],
    "last_result": None,
    "far_streak": 0,
    "explanation": None,
    "report": None,
    "quiz_started": False,
    "quiz_finished": False,
}


def init_session_state():
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)


def reset_session():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()


def esc(text):
    return html.escape(str(text or ""))


def record_result(question, answer, evaluation, skipped=False):
    state = st.session_state
    verdict = evaluation.get("verdict", "far")
    state.history.append(
        {
            "question": question["question"],
            "topic": question.get("topic", "General"),
            "difficulty": question.get("difficulty", START_DIFFICULTY),
            "answer": answer,
            "verdict": verdict,
            "misconception": evaluation.get("misconception", ""),
            "skipped": skipped,
        }
    )
    state.far_streak = state.far_streak + 1 if verdict == "far" else 0
    state.last_result = {**evaluation, "skipped": skipped}
    state.explanation = None


def prepare_next_question(result, question):
    state = st.session_state
    verdict = result.get("verdict", "far")
    difficulty = next_difficulty(question.get("difficulty", START_DIFFICULTY), verdict)

    focus = None
    if verdict in ("close", "far") and not result.get("skipped"):
        focus = result.get("misconception") or None

    explanation = None
    if state.far_streak >= 2:
        try:
            explanation = explain_gap(
                question.get("topic", "this topic"),
                question.get("key_points", []),
                state.material,
            )
        except Exception:
            explanation = None

    new_question = generate_question(
        state.material,
        difficulty,
        focus=focus,
        previous_questions=[h["question"] for h in state.history],
    )
    new_question["difficulty"] = difficulty

    state.current_q = new_question
    state.difficulty = difficulty
    state.last_result = None
    state.explanation = explanation
    if explanation:
        state.far_streak = 0


def difficulty_path(history, current_question, answered_current):
    steps = [h["difficulty"] for h in history]
    if not answered_current:
        steps.append(current_question.get("difficulty", START_DIFFICULTY))
    return " → ".join(DIFFICULTY_LABELS.get(step, step) for step in steps)


init_session_state()
state = st.session_state


st.markdown(
    """
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
    .badge {
        display: inline-block;
        background: #1e293b;
        color: #ffffff;
        border-radius: 999px;
        padding: 0.1rem 0.7rem;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .feedback-box {
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-top: 0.8rem;
        font-weight: 500;
        line-height: 1.7;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">📚 Hesham</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Upload a lecture, answer open-ended questions, and get '
    "questions that adapt to what you actually understand</div>",
    unsafe_allow_html=True,
)


with st.sidebar:
    st.header("⚙️ Settings")

    uploaded_file = st.file_uploader(
        "📄 Upload PDF Document",
        type=["pdf"],
        help="Upload your study material or lecture slides (text-based PDF).",
    )

    num_questions = st.slider(
        "🔢 Questions per session", min_value=3, max_value=10, value=5
    )

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        start_btn = st.button("🚀 Start Quiz", width="stretch", type="primary")
    with col_b:
        reset_btn = st.button("🔄 Reset", width="stretch")


if reset_btn:
    reset_session()
    st.rerun()

if start_btn:
    if uploaded_file is None:
        st.sidebar.error("⚠️ Please upload a PDF file first!")
    else:
        try:
            with st.spinner("⏳ Reading the PDF and writing the first question..."):
                text = extract_text(uploaded_file)
                if not text or text.strip().startswith("⚠️"):
                    raise ValueError(
                        text.strip() if text else "No text was found in this PDF."
                    )
                first_question = generate_question(text, START_DIFFICULTY)
        except Exception as e:
            st.sidebar.error(f"⚠️ {e}")
        else:
            reset_session()
            first_question["difficulty"] = START_DIFFICULTY
            state.material = text
            state.file_name = uploaded_file.name
            state.target = num_questions
            state.current_q = first_question
            state.quiz_started = True
            st.rerun()


if state.quiz_started and not state.quiz_finished:
    question = state.current_q
    total = state.target
    result = state.last_result
    answered = len(state.history)
    number = answered if result else answered + 1

    st.progress(answered / total, text=f"Question {number} of {total}")
    st.caption(
        "Difficulty path: "
        + difficulty_path(state.history, question, result is not None)
    )

    if state.explanation:
        st.info(
            "📖 **A quick explanation before this question**\n\n" + state.explanation
        )

    badge = DIFFICULTY_LABELS.get(question.get("difficulty"), "")
    st.markdown(
        f'<div class="question-card" dir="auto"><span class="badge">{badge}</span><br>'
        f"❓ {esc(question['question'])}</div>",
        unsafe_allow_html=True,
    )
    if question.get("topic"):
        st.caption(f"Topic: {question['topic']}")

    answer = st.text_area(
        "✍️ Your Answer:",
        key=f"answer_{number}",
        height=140,
        placeholder="Type your answer here in detail...",
        disabled=result is not None,
    )

    col1, col2 = st.columns(2)
    with col1:
        submit_btn = st.button(
            "✅ Submit Answer",
            width="stretch",
            type="primary",
            disabled=result is not None,
        )
    with col2:
        skip_btn = st.button(
            "⏭️ Skip Question", width="stretch", disabled=result is not None
        )

    if submit_btn:
        if not answer.strip():
            st.warning("⚠️ Please enter an answer before submitting!")
        else:
            try:
                with st.spinner("🧠 Analyzing your answer..."):
                    evaluation = analyze_answer(
                        question["question"], question.get("key_points", []), answer
                    )
            except Exception as e:
                st.error(f"⚠️ {e}")
            else:
                record_result(question, answer, evaluation)
                st.rerun()

    if skip_btn:
        record_result(
            question,
            "",
            {
                "verdict": "far",
                "misconception": "Skipped the question.",
                "feedback": "No problem, let's try another one.",
                "hint": "",
            },
            skipped=True,
        )
        st.rerun()

    if result:
        verdict = result.get("verdict", "far")
        if verdict not in COLOR_MAP:
            verdict = "far"

        lines = [
            f"<b>Evaluation: {LABEL_MAP[verdict]}</b>",
            esc(result.get("feedback", "")),
        ]
        if (
            verdict != "correct"
            and result.get("misconception")
            and not result.get("skipped")
        ):
            lines.append(f"<small>🎯 Gap: {esc(result['misconception'])}</small>")
        if verdict != "correct" and result.get("hint"):
            lines.append(f"<small>💡 Hint: {esc(result['hint'])}</small>")

        st.markdown(
            f'<div class="feedback-box" dir="auto" style="background:{COLOR_MAP[verdict]};'
            f'border-left:5px solid {BORDER_MAP[verdict]};color:{TEXT_MAP[verdict]};">'
            + "<br>".join(lines)
            + "</div>",
            unsafe_allow_html=True,
        )

        is_last = answered >= total
        next_label = "🏁 Finish & View Report" if is_last else "➡️ Next Question"
        if st.button(next_label, type="primary", key=f"next_{answered}"):
            if is_last:
                state.quiz_finished = True
                st.rerun()
            try:
                with st.spinner("🧠 Preparing your next question..."):
                    prepare_next_question(result, question)
            except Exception as e:
                st.error(f"⚠️ {e}")
            else:
                st.rerun()


if state.quiz_finished:
    st.markdown("## 🎉 Session Complete!")

    if state.report is None:
        try:
            with st.spinner("⏳ Generating your performance report..."):
                state.report = build_report(state.history)
            st.balloons()
        except Exception as e:
            st.error(f"⚠️ {e}")
            st.button("🔁 Try again")

    report = state.report
    if report:
        stats = report.get("stats", {})
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("✅ Correct", stats.get("correct", 0))
        m2.metric("🟧 Close", stats.get("close", 0))
        m3.metric("🟥 Far", stats.get("far", 0))
        m4.metric("❓ Total", stats.get("total", len(state.history)))

        st.info(f"**Summary:** {report.get('summary') or '—'}")

        left, right = st.columns(2)
        with left:
            st.markdown("#### 💪 Strengths")
            for item in report.get("strengths") or ["—"]:
                st.markdown(f"- {item}")
        with right:
            st.markdown("#### 🎯 Needs focus")
            for item in report.get("weaknesses") or ["—"]:
                st.markdown(f"- {item}")

        if report.get("top_gap"):
            st.warning(f"🔍 **Most repeated gap:** {report['top_gap']}")
        if report.get("recommendation"):
            st.success(f"📌 **Recommendation:** {report['recommendation']}")

        with st.expander("🔍 Detailed Answer Breakdown", expanded=False):
            for i, item in enumerate(state.history, 1):
                level = DIFFICULTY_LABELS.get(item.get("difficulty"), "")
                st.markdown(f"**Q{i}** ({level}): {item['question']}")
                st.markdown(f"- Your answer: _{item.get('answer') or '—'}_")
                st.markdown(f"- Verdict: **{item.get('verdict')}**")
                if item.get("misconception"):
                    st.markdown(f"- Note: {item['misconception']}")
                st.divider()

    if st.button("🆕 Start a new session", type="primary"):
        reset_session()
        st.rerun()


st.divider()
st.caption("Hesham · Adaptive assessment powered by Gemini & Streamlit")
