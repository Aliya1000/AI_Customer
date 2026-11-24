import json
import re
from typing import Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from backend.app.schemas.agent_outputs import AgentOutputs
from backend.app.schemas.report import CoachingReportCreate


def _get_field(obj: Any, key: str, default: Any = "") -> Any:
    """Helper to extract a field from a dict or object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def extract_json_from_response(text: str) -> str:
    """
    Extracts raw JSON string from an LLM response.
    Handles markdown code fences (```json ... ``` or ``` ... ```) as well as
    bare JSON surrounded by explanatory text.
    """
    if not text:
        return ""
    text = text.strip()
    
    # 1. Match code fence ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    
    # 2. Match outer curly braces {...}
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()
    
    return text


def format_conversation_history(messages: Optional[List[Any]]) -> str:
    """Formats a list of message objects or dicts into a readable transcript."""
    if not messages:
        return "(No prior conversation messages. Customer has initiated the interaction.)"
    
    lines = []
    for msg in messages:
        sender = _get_field(msg, "sender") or _get_field(msg, "role", "unknown")
        text = _get_field(msg, "message_text") or _get_field(msg, "text") or _get_field(msg, "content", "")
        role_label = "Customer" if sender.lower() == "customer" else "Employee"
        lines.append(f"[{role_label}]: {text}")
    
    return "\n".join(lines)


def format_rag_context(rag_chunks: Optional[List[Any]]) -> str:
    """Formats retrieved RAG chunks into structured documentation context."""
    if not rag_chunks:
        return "(No relevant knowledge base documentation retrieved for this turn.)"
    
    formatted = []
    for idx, chunk in enumerate(rag_chunks, start=1):
        source = _get_field(chunk, "source", "knowledge_base")
        score = _get_field(chunk, "score", 0.0)
        try:
            score_val = float(score)
        except (ValueError, TypeError):
            score_val = 0.0
        content = _get_field(chunk, "content") or _get_field(chunk, "snippet", "")
        formatted.append(f"Document {idx} [Source: {source} | Score: {score_val:.2f}]:\n{content}")
    
    return "\n\n".join(formatted)


def get_turn_guidance(persona: Optional[str], emotional_progression: Optional[str], turn_number: int) -> str:
    """Generates turn-specific posture guidance for the customer simulator."""
    prog = (emotional_progression or "stable").lower()
    p = (persona or "Standard").capitalize()

    if prog == "escalating_to_calm":
        if turn_number <= 1:
            return "Express strong initial frustration, skepticism, or confusion. State your issue firmly."
        elif turn_number == 2:
            return "Begin to soften. Acknowledge the representative's assistance, but remain cautious."
        else:
            return "Fully de-escalated and cooperative. Express appreciation for the clear resolution."
    elif prog == "calm_to_frustrated":
        if turn_number <= 1:
            return "Start polite, calm, and reasonable. Inquire about resolving the issue."
        elif turn_number == 2:
            return "Show noticeable impatience or irritation. Note that you expected a quicker resolution."
        else:
            return "Highly frustrated and demanding. Threaten escalation or request an immediate refund/replacement."
    else:  # stable or default
        if p == "Angry":
            return "Maintain a firm, demanding, and indignant tone. Insist on prompt resolution."
        elif p == "Impatient":
            return "Keep answers brief, concise, and hurried. Push for quick answers without long diagnostics."
        elif p == "Confused":
            return "Express uncertainty, confusion about technical steps, and ask for simple step-by-step guidance."
        elif p == "Patient":
            return "Be courteous, polite, and cooperative. Follow suggestions step by step with thanks."
        else:
            return "Be straightforward, reasonable, and clear about your needs."


# Parsers
agent_outputs_parser = PydanticOutputParser(pydantic_object=AgentOutputs)
coaching_report_parser = PydanticOutputParser(pydantic_object=CoachingReportCreate)


# AgentOutputs Prompt
AGENT_OUTPUTS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are an expert AI customer support supervisor and coaching engine.\n"
        "You analyze customer support interactions in real time to guide support agents.\n"
        "You synthesize session metadata, product catalog details, retrieved knowledge documentation, "
        "and conversation history into a unified 6-agent structured analysis.\n\n"
        "You MUST return a single valid JSON object strictly matching the required schema.\n"
        "Do not include any conversational filler, markdown formatting, or text outside the JSON object."
    )),
    ("user", (
        "### Session Details:\n"
        "- Interaction Mode: {interaction_mode}\n"
        "- Product Name: {product_name}\n"
        "- Product Context: {product_context}\n"
        "- Customer Scenario: {customer_scenario}\n"
        "- Customer Persona: {persona}\n"
        "- Emotional Progression: {emotional_progression}\n\n"
        "### Product Catalog Information:\n"
        "- Category: {product_category}\n"
        "- Description: {product_description}\n\n"
        "### Retrieved Knowledge Base Context (RAG):\n"
        "{rag_context}\n\n"
        "### Conversation Transcript:\n"
        "{conversation_history}\n\n"
        "### Schema Format Instructions:\n"
        "{format_instructions}\n\n"
        "Respond with the JSON object:"
    )),
])


# Customer Simulator Prompt
SIMULATOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a customer communicating with a customer support representative.\n"
        "Roleplay strictly as the customer with the assigned persona, scenario, and emotional progression.\n"
        "Stay completely in character. Do NOT explain that you are an AI or simulator.\n"
        "Respond naturally as a human customer would in a live chat interaction.\n\n"
        "Persona Definitions:\n"
        "- Patient: Polite, cooperative, willing to try troubleshooting steps, appreciative of help.\n"
        "- Impatient: Hurried, curt, avoids lengthy diagnostics, wants an immediate fix or replacement.\n"
        "- Confused: Non-technical, overwhelmed by jargon, misinterprets technical terms, asks for clarification.\n"
        "- Angry: Highly frustrated, upset about defects or poor quality, demands immediate action or compensation.\n"
        "- Standard: Reasonable, balanced, direct, polite everyday consumer."
    )),
    ("user", (
        "### Customer Profile:\n"
        "- Product: {product_name}\n"
        "- Scenario: {customer_scenario}\n"
        "- Persona: {persona}\n"
        "- Progression: {emotional_progression}\n"
        "- Current Turn: {turn_number}\n"
        "- Emotional Posture: {turn_guidance}\n\n"
        "### Conversation History:\n"
        "{conversation_history}\n\n"
        "Write your next reply as the customer to the representative's latest message:"
    )),
])


# Coaching Report Prompt
COACHING_REPORT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a senior customer experience quality auditor and coaching director.\n"
        "Analyze the entire transcript of a customer support conversation.\n"
        "Evaluate the employee's empathy, problem-solving, adherence to policy, clarity, and de-escalation.\n\n"
        "You MUST return a single valid JSON object strictly matching the required schema.\n"
        "Do not include any text or markdown wrappers outside the JSON object."
    )),
    ("user", (
        "### Session Context:\n"
        "- Session ID: {session_id}\n"
        "- Product: {product_name}\n"
        "- Customer Scenario: {customer_scenario}\n"
        "- Customer Persona: {persona}\n\n"
        "### Conversation Transcript:\n"
        "{conversation_history}\n\n"
        "### Schema Format Instructions:\n"
        "{format_instructions}\n\n"
        "Respond with the coaching evaluation JSON object:"
    )),
])
