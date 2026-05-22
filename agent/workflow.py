import json
import os
import re
from typing import TypedDict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END

from agent.prompts import CONTEXT_EXTRACTION_PROMPT, RECOMMENDATION_PROMPT
from rag.embedder import embed_single
from rag.vector_store import query_catalog


class StyleState(TypedDict):
    prompt: str
    user_context: dict
    candidates_tops: list[dict]
    candidates_bottoms: list[dict]
    recommendation: dict
    error: Optional[str]


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.4,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        text = match.group(1)
    return json.loads(text)


def parse_context_node(state: StyleState) -> StyleState:
    print("[agent] Parsing user context...")
    llm = _get_llm()
    prompt = CONTEXT_EXTRACTION_PROMPT.format(prompt=state["prompt"])

    response = llm.invoke(prompt)
    try:
        context = _parse_json_response(response.content)
    except Exception:
        context = {
            "existing_items": [],
            "occasion": "casual",
            "style_preferences": [],
            "budget_max": None,
            "dominant_color": None,
        }
    print(f"[agent] Context: {context}")
    return {**state, "user_context": context}


def retrieve_candidates_node(state: StyleState) -> StyleState:
    print("[agent] Querying vector database...")
    context = state["user_context"]

    query_text = (
        f"{state['prompt']} {context.get('occasion', '')} "
        f"{' '.join(context.get('style_preferences', []))} "
        f"color {context.get('dominant_color', '')}"
    )
    embedding = embed_single(query_text)
    max_price = context.get("budget_max")

    tops = query_catalog(embedding, n_results=8, category_filter="tops", max_price=max_price)
    bottoms = query_catalog(embedding, n_results=8, category_filter="bottoms", max_price=max_price)

    print(f"[agent] Retrieved {len(tops)} tops, {len(bottoms)} bottoms")
    return {**state, "candidates_tops": tops, "candidates_bottoms": bottoms}


def _format_items_for_prompt(items: list[dict]) -> str:
    lines = []
    for i, item in enumerate(items, 1):
        lines.append(
            f"{i}. {item['name']} | {item['price']} | Color: {item.get('color','?')} "
            f"| {item.get('description','')[:80]}"
        )
    return "\n".join(lines)


def generate_recommendation_node(state: StyleState) -> StyleState:
    print("[agent] Generating recommendation with Gemini...")
    llm = _get_llm()

    tops_text = _format_items_for_prompt(state["candidates_tops"])
    bottoms_text = _format_items_for_prompt(state["candidates_bottoms"])

    prompt = RECOMMENDATION_PROMPT.format(
        prompt=state["prompt"],
        context=json.dumps(state["user_context"], indent=2),
        tops=tops_text or "No tops available",
        bottoms=bottoms_text or "No bottoms available",
    )

    response = llm.invoke(prompt)
    try:
        recommendation = _parse_json_response(response.content)
    except Exception as e:
        print(f"[agent] JSON parse failed: {e}\nRaw: {response.content[:300]}")
        recommendation = {
            "recommended_items": [],
            "total_price": "$0.00",
            "stylist_note": "Unable to generate recommendation. Please try again.",
        }

    print(f"[agent] Recommendation: {len(recommendation.get('recommended_items', []))} items")
    return {**state, "recommendation": recommendation}


def build_graph():
    graph = StateGraph(StyleState)

    graph.add_node("parse_context", parse_context_node)
    graph.add_node("retrieve_candidates", retrieve_candidates_node)
    graph.add_node("generate_recommendation", generate_recommendation_node)

    graph.add_edge(START, "parse_context")
    graph.add_edge("parse_context", "retrieve_candidates")
    graph.add_edge("retrieve_candidates", "generate_recommendation")
    graph.add_edge("generate_recommendation", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_workflow(prompt: str) -> dict:
    graph = get_graph()
    initial_state: StyleState = {
        "prompt": prompt,
        "user_context": {},
        "candidates_tops": [],
        "candidates_bottoms": [],
        "recommendation": {},
        "error": None,
    }
    final_state = graph.invoke(initial_state)
    return final_state["recommendation"]
