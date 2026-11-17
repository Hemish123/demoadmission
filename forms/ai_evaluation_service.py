"""
AI Evaluation Service for Shreyas Foundation Parental Understanding Questionnaire.
Evaluates Written Responses (Q11 - Q14, 5 marks each = 20 marks total)
using Azure OpenAI GPT-4o / GPT-4o-mini based on the school's official rubric.

Rubric:
  5: Specific, thoughtful response; clear understanding with realistic examples/commitments aligned with school philosophy.
  4: Good understanding and relevant intentions; some practical detail or reflection.
  3: Basic, relevant understanding, but general with limited examples.
  2: Limited or vague response; little connection to question's intent.
  1: Very brief response with minimal evidence of reflection.
  0: No response or unrelated response.
"""
import os
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Supported environment variable names from .env
AZURE_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip()
AZURE_OPENAI_ENDPOINT = (os.getenv("ENDPOINT_URL") or os.getenv("AZURE_OPENAI_ENDPOINT") or "https://jivihireopenai.openai.azure.com").strip().rstrip('/')
AZURE_OPENAI_MODEL = (os.getenv("model") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip().strip('"').strip("'")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

WRITTEN_QUESTION_PROMPTS = {
    11: {
        "focus": "Reflection on child's real-life learning experience",
        "question": "Please describe one recent situation in which your child showed curiosity, frustration, independence or care for someone. What did you do, and what did your child learn from the experience?",
        "criteria": "Look for authentic observation of the child, parental empathy and restraint (not taking over immediately), and clear reflection on how the child learned through the experience."
    },
    12: {
        "focus": "Year-round support for underprivileged children",
        "question": "Shreyas Foundation believes in supporting underprivileged children throughout the year. In what practical ways could you and your family contribute time, skills, resources or participation to support these children and help sustain this initiative?",
        "criteria": "Assess willingness and realistic participation (volunteering time, teaching skills, participating in activities, sharing resources). Note: financial contribution must not be treated as a condition of admission."
    },
    13: {
        "focus": "Education, values, life skills, Gujarati and Sanskar",
        "question": "What does a meaningful education mean to you beyond marks and examination results? What values, life skills and abilities would you most like your child to develop? Please include how you see Gujarati language, culture and Sanskar contributing to your child's growth.",
        "criteria": "Look for holistic vision of learning beyond exam marks, appreciation of character building, respect for Gujarati language, local culture, and moral Sanskar."
    },
    14: {
        "focus": "Parent's role in school partnership",
        "question": "What kind of partnership would you like to build with Shreyas Foundation? How would you contribute to your child's learning at home and work with educators if the school shares feedback or suggests a different approach?",
        "criteria": "Look for mutual respect, openness to constructive dialogue, willingness to align home environment with school philosophy, and proactive collaboration with educators."
    }
}


def evaluate_written_answers_with_ai(
    written_responses: Dict[int, str],
    child_name: str = "",
    standard: str = ""
) -> Dict[str, Any]:
    """
    Evaluates Q11-Q14 written answers using Azure OpenAI GPT-4o / GPT-4o-mini.
    Supports both Azure OpenAI and standard OpenAI endpoints.
    """
    api_key = os.getenv("OPENAI_API_KEY", AZURE_OPENAI_KEY).strip()
    endpoint = (os.getenv("ENDPOINT_URL") or os.getenv("AZURE_OPENAI_ENDPOINT") or AZURE_OPENAI_ENDPOINT).strip().rstrip('/')
    model_name = (os.getenv("model") or os.getenv("OPENAI_MODEL") or AZURE_OPENAI_MODEL).strip().strip('"').strip("'")

    if not api_key:
        logger.warning("[AI EVALUATION] No API key configured. Falling back to heuristic baseline.")
        return _fallback_heuristic_evaluation(written_responses)

    try:
        items_to_evaluate = []
        for q_id in [11, 12, 13, 14]:
            text = str(written_responses.get(q_id) or written_responses.get(str(q_id)) or "").strip()
            meta = WRITTEN_QUESTION_PROMPTS.get(q_id, {})
            items_to_evaluate.append({
                "question_id": q_id,
                "focus": meta.get("focus"),
                "question": meta.get("question"),
                "rubric_criteria": meta.get("criteria"),
                "parent_answer": text
            })

        system_prompt = (
            "You are an empathetic, insightful educational psychologist evaluating parent admission questionnaires "
            "for Shreyas Foundation Vikas Kendra, an alternative, child-centric, experiential school in Ahmedabad, Gujarat.\n\n"
            "School Philosophy:\n"
            "- Learning through play, exploration, curiosity, relationship, and independence.\n"
            "- Multilingual (English and Gujarati), deep respect for culture, nature, and community Sanskar.\n"
            "- True partnership between home and school without competitive academic pressure.\n\n"
            "Official Rubric for each question (0 to 5 marks):\n"
            "5 Marks: Specific, thoughtful response; clear understanding with realistic examples/commitments aligned with school philosophy.\n"
            "4 Marks: Good understanding and relevant intentions; some practical detail or reflection.\n"
            "3 Marks: Basic, relevant understanding, but general with limited examples.\n"
            "2 Marks: Limited or vague response; little connection to the question's intent.\n"
            "1 Mark: Very brief response with minimal evidence of reflection.\n"
            "0 Marks: No response or completely unrelated response.\n\n"
            "Return valid JSON ONLY with key 'evaluations', where each item has:\n"
            "- 'question_id': integer (11, 12, 13, or 14)\n"
            "- 'score': number from 0.0 to 5.0 (can use 0.5 increments like 3.5, 4.0, 4.5, 5.0)\n"
            "- 'feedback': 1-2 constructive sentences in English explaining why this score was awarded."
        )

        user_content = json.dumps({
            "applicant": {
                "child_name": child_name or "Applicant",
                "standard": standard or "Nursery"
            },
            "questions": items_to_evaluate
        }, ensure_ascii=False)

        request_payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        # Azure OpenAI Endpoint or standard OpenAI URL
        if "openai.azure.com" in endpoint:
            url = f"{endpoint}/openai/deployments/{model_name}/chat/completions?api-version={AZURE_API_VERSION}"
            headers = {
                "Content-Type": "application/json",
                "api-key": api_key
            }
        else:
            url = "https://api.openai.com/v1/chat/completions"
            request_payload["model"] = model_name
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

        req = urllib.request.Request(
            url,
            data=json.dumps(request_payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=25) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)

        raw_content = res_json["choices"][0]["message"]["content"]
        parsed = json.loads(raw_content)

        evaluations_list = parsed.get("evaluations", [])
        if isinstance(parsed, dict) and not evaluations_list:
            evaluations_list = []
            for k, v in parsed.items():
                if str(k).isdigit() and isinstance(v, dict):
                    evaluations_list.append({"question_id": int(k), **v})

        written_scores = {}
        evaluations_dict = {}
        total = 0.0

        for item in evaluations_list:
            qid = str(item.get("question_id"))
            score_val = min(max(float(item.get("score", 0.0)), 0.0), 5.0)
            written_scores[qid] = round(score_val, 1)
            evaluations_dict[qid] = {
                "score": round(score_val, 1),
                "feedback": item.get("feedback", "")
            }
            total += score_val

        # Fill any missing questions with 0
        for q_id in [11, 12, 13, 14]:
            qid_str = str(q_id)
            if qid_str not in written_scores:
                written_scores[qid_str] = 0.0
                evaluations_dict[qid_str] = {"score": 0.0, "feedback": "No answer provided."}

        total = round(min(total, 20.0), 1)

        logger.info(f"[AI EVALUATION SUCCESS] Evaluated Q11-Q14 with {model_name} via Azure OpenAI. Total: {total}/20")
        return {
            "written_scores": written_scores,
            "total_written_score": total,
            "evaluations": evaluations_dict,
            "ai_evaluated": True,
            "model_used": model_name
        }

    except Exception as e:
        logger.exception(f"[AI EVALUATION ERROR] Failed to call Azure OpenAI: {e}")
        return _fallback_heuristic_evaluation(written_responses)


def _fallback_heuristic_evaluation(written_responses: Dict[int, str]) -> Dict[str, Any]:
    """
    Fallback heuristic scoring if Azure OpenAI call fails.
    """
    written_scores = {}
    evaluations_dict = {}
    total = 0.0

    for q_id in [11, 12, 13, 14]:
        qid_str = str(q_id)
        text = str(written_responses.get(q_id) or written_responses.get(qid_str) or "").strip()
        length = len(text)
        if length >= 120:
            score_val = 4.5
            fb = "Thoughtful and detailed response reflecting good parental engagement."
        elif length >= 60:
            score_val = 3.5
            fb = "Relevant response with moderate detail."
        elif length >= 20:
            score_val = 2.5
            fb = "Basic response; could be more specific with examples."
        elif length > 0:
            score_val = 1.5
            fb = "Brief response."
        else:
            score_val = 0.0
            fb = "No response provided."

        written_scores[qid_str] = score_val
        evaluations_dict[qid_str] = {"score": score_val, "feedback": fb}
        total += score_val

    return {
        "written_scores": written_scores,
        "total_written_score": round(total, 1),
        "evaluations": evaluations_dict,
        "ai_evaluated": False,
        "model_used": "heuristic_fallback"
    }
