"""
LLM-as-a-Judge Evaluation Benchmark Suite.
Tests response empathy, factual grounding against RAG context, and policy adherence.
"""

import pytest
from typing import Dict, Any


def evaluate_response_with_judge(
    question: str,
    rag_context: str,
    response_text: str,
) -> Dict[str, Any]:
    """
    Evaluates response quality along 3 key criteria:
    1. Groundedness (faithful to retrieved RAG context)
    2. Empathy / Tone (acknowledgment and respectful phrasing)
    3. Actionability (clear next steps provided)
    """
    response_lower = response_text.lower()
    
    # 1. Empathy check
    empathy_keywords = ["apologize", "sorry", "understand", "glad", "help", "pleasure"]
    has_empathy = any(w in response_lower for w in empathy_keywords)
    empathy_score = 9.0 if has_empathy else 6.0

    # 2. Groundedness check (context containment proxy)
    rag_words = set(rag_context.lower().split())
    resp_words = set(response_lower.split())
    overlap = len(rag_words.intersection(resp_words))
    groundedness_score = min(10.0, 5.0 + (overlap * 0.3))

    # 3. Actionability check
    action_words = ["please", "ship", "step", "verify", "order", "replace", "reset"]
    has_action = any(w in response_lower for w in action_words)
    action_score = 9.0 if has_action else 6.0

    composite_score = round((empathy_score + groundedness_score + action_score) / 3.0, 2)

    return {
        "empathy_score": empathy_score,
        "groundedness_score": groundedness_score,
        "actionability_score": action_score,
        "composite_score": composite_score,
        "pass_verdict": composite_score >= 7.0,
    }


def test_judge_high_quality_grounded_response():
    question = "My headphones arrived with a cracked left earcup."
    context = "Items damaged in transit qualify for express 48-hour DOA replacement."
    response = "I sincerely apologize for the cracked earcup upon arrival. Because this qualifies for our 48-hour express DOA replacement, please share your order ID so I can dispatch a new unit."

    eval_result = evaluate_response_with_judge(question, context, response)
    assert eval_result["pass_verdict"] is True
    assert eval_result["composite_score"] >= 8.0
    assert eval_result["empathy_score"] >= 9.0


def test_judge_low_quality_unhelpful_response():
    question = "My watch battery drains in two hours."
    context = "Perform soft reset by holding crown for 10 seconds."
    response = "Battery issues happen sometimes."

    eval_result = evaluate_response_with_judge(question, context, response)
    assert eval_result["empathy_score"] < 7.0
    assert eval_result["actionability_score"] < 7.0
