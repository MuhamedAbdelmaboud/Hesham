import random
from llm import call_llm, call_llm_json

LEVELS = ["easy", "medium", "hard"]
VERDICTS = ["correct", "close", "far"]
CHUNK_SIZE = 3000


def _pick_chunk(material: str, size: int = CHUNK_SIZE) -> str:
    if len(material) <= size:
        return material
    max_start = len(material) - size
    start = random.randint(0, max_start)
    return material[start:start + size]


def generate_question(material: str, difficulty: str = "easy", focus: str = None, previous_questions: list = None) -> dict:
    chunk = _pick_chunk(material)
    
    prompt = f"""You are a university teacher. Generate ONE question based on this study material:
---
{chunk}
---
Difficulty level: {difficulty}
- easy: Basic definitions or recall.
- medium: Explanation or comparison.
- hard: Application, analysis, or special cases.

Rules:
1. Open-ended question only (NO multiple choice, NO yes/no).
2. Answer must be available in the text.
3. Language must match the study material language.
"""
    if focus:
        prompt += f"\n- Focus: The question must specifically target this misconception: {focus}\n"
    if previous_questions:
        prompt += f"\n- Do NOT repeat any of these questions: {previous_questions}\n"
        
    prompt += """
Return ONLY a JSON object with these keys:
- "question": string
- "topic": string (main concept)
- "key_points": list of 2 to 4 key ideas the correct answer must cover
"""

    for _ in range(2):
        result = call_llm_json(prompt)
        if isinstance(result, dict) and "question" in result and "topic" in result and result.get("key_points"):
            return result
    raise RuntimeError("فشل توليد السؤال بالصيغة المطلوبة.")


def generate_questions_batch(material: str, count: int = 3) -> list:
    chunk = _pick_chunk(material)
    
    prompt = f"""You are a university teacher. Generate exactly {count} unique questions based on this study material:
---
{chunk}
---
Rules:
1. Open-ended questions only (NO multiple choice, NO yes/no).
2. Answer must be available in the text.
3. Language must match the study material language.

Return ONLY a JSON array containing objects with these keys for each question:
- "question": string
- "topic": string
- "key_points": list of 2 to 4 key ideas
"""
    result = call_llm_json(prompt)
    if isinstance(result, list):
        return result
    elif isinstance(result, dict) and "questions" in result:
        return result["questions"]
    return [result]


def analyze_answer(question: str, key_points: list, student_answer: str) -> dict:
    clean_ans = student_answer.strip().lower()
    if not clean_ans or len(clean_ans) < 3 or clean_ans in ["مش عارف", "لا أعرف", "idk", "dont know"]:
        return {
            "verdict": "far",
            "misconception": "لم يتم تقديم إجابة أو الإجابة غير كافية.",
            "feedback": "حاول كتابة محاولة حتى لو كانت بسيطة!",
            "hint": "راجع المفاهيم الأساسية للدرس."
        }
        
    prompt = f"""Analyze the student's answer based on the question and key points.

Question: {question}
Expected Key Points: {key_points}
Student Answer: {student_answer}

Evaluation criteria:
- Judge understanding, not exact word matching.
- verdict choices:
  * "correct": covered all essential key points.
  * "close": right direction, but missed or mixed up a point.
  * "far": incorrect understanding or unrelated answer.

Return ONLY a JSON object with:
- "verdict": "correct" | "close" | "far"
- "misconception": string (one sentence describing the misconception, empty string if correct)
- "feedback": string (1-2 encouraging sentences in the student's language)
- "hint": string (a hint pointing towards the correct answer without giving it away directly)
"""
    result = call_llm_json(prompt)
    if result.get("verdict") not in VERDICTS:
        result["verdict"] = "far"
    return result


def next_difficulty(current: str, verdict: str) -> str:
    idx = LEVELS.index(current) if current in LEVELS else 0
    if verdict == "correct":
        idx = min(idx + 1, len(LEVELS) - 1)
    elif verdict == "far":
        idx = max(idx - 1, 0)
    return LEVELS[idx]


def explain_gap(topic: str, key_points: list, material: str) -> str:
    chunk = _pick_chunk(material)
    prompt = f"""Explain this concept simply to a beginner student based on the material below:
Topic: {topic}
Key Points: {key_points}

Material:
{chunk}

Provide a 3 to 5 sentence simple explanation in the same language as the material, ending with an explicit recommendation on what section/topic to re-study.
"""
    return call_llm(prompt)


def build_report(history: list) -> dict:
    if not history:
        return {"summary": "لا توجد أسئلة مُجابة حتى الآن."}
        
    total = len(history)
    correct = sum(1 for h in history if h.get("verdict") == "correct")
    close = sum(1 for h in history if h.get("verdict") == "close")
    far = sum(1 for h in history if h.get("verdict") == "far")
    
    stats = {"total": total, "correct": correct, "close": close, "far": far}
    
    history_summary = [
        f"- Topic: {h.get('topic')}, Verdict: {h.get('verdict')}, Misconception: {h.get('misconception', '')}"
        for h in history
    ]
        
    prompt = f"""Generate a final performance report based on this student history:
{chr(10).join(history_summary)}

Return ONLY a JSON object with:
- "summary": string (overall summary of student's performance)
- "strengths": list of strings (topics mastered)
- "weaknesses": list of strings (topics needing focus)
- "top_gap": string (most repeated misconception or gap)
- "recommendation": string (specific actionable next study step)
"""
    report = call_llm_json(prompt)
    report["stats"] = stats
    return report


if __name__ == "__main__":
    print("اختبار engine.py جاهز.")