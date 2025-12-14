"""
LLM Reliability Evaluation Pipeline
----------------------------------
Inputs:
- chat_conversation.json
- context_vectors.json
"""

import time
import json
from typing import List, Dict
from difflib import SequenceMatcher

# -------------------------------
# Utility Functions
# -------------------------------

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def extract_claims(response: str) -> List[str]:
    return [s.strip() for s in response.split(".") if len(s.strip()) > 10]

def flatten_context(vectors: List[Dict]) -> str:
    return " ".join(v["text"] for v in vectors)

# -------------------------------
# Core Evaluators
# -------------------------------

def relevance_score(user_query: str, response: str) -> float:
    return similarity(user_query, response)

def completeness_score(user_query: str, response: str) -> float:
    expected_keywords = ["cost", "price", "address", "night", "rupees"]
    hits = sum(1 for k in expected_keywords if k in response.lower())
    return hits / len(expected_keywords)

def hallucination_score(response: str, context_text: str) -> Dict:
    claims = extract_claims(response)
    unsupported = []

    for claim in claims:
        if similarity(claim, context_text) < 0.35:
            unsupported.append(claim)

    score = 1 - (len(unsupported) / max(len(claims), 1))
    return {
        "hallucination_score": round(score, 2),
        "unsupported_claims": unsupported
    }

def latency_cost_metrics(start_time: float, tokens_used: int, cost_per_1k=0.002):
    latency = time.time() - start_time
    cost = (tokens_used / 1000) * cost_per_1k
    return {
        "latency_seconds": round(latency, 3),
        "estimated_cost_usd": round(cost, 6)
    }

# -------------------------------
# Orchestrator
# -------------------------------

def evaluate(chat_json: Dict, context_json: Dict) -> Dict:
    start = time.time()

    user_turn = [t for t in chat_json["conversation_turns"] if t["role"] == "User"][-1]
    ai_turn = [t for t in chat_json["conversation_turns"] if t["role"] == "AI/Chatbot"][-1]

    context_vectors = context_json["data"]["vector_data"]
    context_text = flatten_context(context_vectors)

    relevance = relevance_score(user_turn["message"], ai_turn["message"])
    completeness = completeness_score(user_turn["message"], ai_turn["message"])
    hallucination = hallucination_score(ai_turn["message"], context_text)

    metrics = latency_cost_metrics(start, tokens_used=450)

    return {
        "relevance_score": round(relevance, 2),
        "completeness_score": round(completeness, 2),
        "hallucination_analysis": hallucination,
        "latency_and_cost": metrics,
        "final_verdict": "FAIL"
        if hallucination["unsupported_claims"]
        else "PASS"
    }

# -------------------------------
# Example Execution
# -------------------------------

if __name__ == "__main__":
    with open("chat.json") as c, open("context.json") as v:
        result = evaluate(json.load(c), json.load(v))
    print(json.dumps(result, indent=2))

