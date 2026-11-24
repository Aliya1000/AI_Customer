import re
from typing import Any, List, Optional

from backend.app.schemas.agent_outputs import (
    AgentOutputs,
    Article,
    EvaluationAndCoachingOutput,
    FAQ,
    KnowledgeRetrievalOutput,
    ProductInformationOutput,
    QueryAnalysisOutput,
    ResponseGenerationOutput,
    SupervisorOutput,
)
from backend.app.schemas.report import CoachingReportResponse


def _get_field(obj: Any, key: str, default: Any = "") -> Any:
    """Helper to extract a field from a dict or object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _detect_intent(text: str) -> str:
    """Detects primary customer intent based on key vocabulary."""
    t = text.lower()
    if re.search(r"\b(refund|money back|billing|charge|charged|cost|receipt|invoice|price|fee)\b", t):
        return "Billing / Refund Request"
    if re.search(r"\b(crack|cracked|buzz|buzzing|broken|defect|defective|damaged|hardware|snapped|physical|earcup|port|hinge|button)\b", t):
        return "Hardware Defect / Replacement"
    if re.search(r"\b(battery|drain|firmware|update|bluetooth|disconnect|pair|pairing|software|app|sync|crash|reboot)\b", t):
        return "Software / Connectivity Issue"
    if re.search(r"\b(setup|install|manual|configure|instructions|start|guide|how to)\b", t):
        return "Product Setup / Usage Guidance"
    return "General Product Inquiries / Support"


def _detect_sentiment(persona: str, progression: str, turn: int, text: str) -> str:
    """Determines sentiment accounting for persona, emotional progression, and current turn."""
    p = (persona or "Standard").capitalize()
    prog = (progression or "stable").lower()
    t = text.lower()

    if prog == "escalating_to_calm":
        if turn <= 1:
            return "Frustrated / Highly Urgent"
        elif turn == 2:
            return "De-escalating / Reassured"
        else:
            return "Calm / Cooperative"
    elif prog == "calm_to_frustrated":
        if turn <= 1:
            return "Calm / Inquiring"
        elif turn == 2:
            return "Impatient / Irritated"
        else:
            return "Outraged / Escalated"
    else:  # stable or default
        if p == "Angry" or any(w in t for w in ["angry", "unacceptable", "terrible", "outraged", "furious"]):
            return "Frustrated / Highly Urgent"
        if p == "Impatient" or any(w in t for w in ["hurry", "quick", "asap", "wait", "long time"]):
            return "Impatient / Demanding"
        if p == "Confused" or any(w in t for w in ["confused", "don't understand", "lost", "where"]):
            return "Confused / Uncertain"
        if p == "Patient":
            return "Calm / Cooperative"
        return "Neutral / Inquiring"


def generate_mock_agent_outputs(
    session: Any,
    messages: Optional[List[Any]] = None,
    rag_context: Optional[List[Any]] = None,
    product: Optional[Any] = None,
) -> AgentOutputs:
    """
    Deterministically generates context-rich AgentOutputs matching all M1 Pydantic constraints.
    Analyzes session metadata, dialogue history, and retrieved knowledge context.
    """
    product_name = _get_field(session, "product_name") or "Product"
    product_context = _get_field(session, "product_context") or ""
    customer_scenario = _get_field(session, "customer_scenario") or "General product inquiry"
    persona = _get_field(session, "persona") or "Patient"
    progression = _get_field(session, "emotional_progression") or "stable"

    # Count turns and locate the latest message
    msgs = messages or []
    employee_turns = sum(1 for m in msgs if (_get_field(m, "sender") or _get_field(m, "role", "")).lower() == "employee")
    latest_msg_text = ""
    latest_employee_text = ""

    for m in reversed(msgs):
        sender = (_get_field(m, "sender") or _get_field(m, "role", "")).lower()
        txt = _get_field(m, "message_text") or _get_field(m, "text") or _get_field(m, "content", "")
        if not latest_msg_text and txt:
            latest_msg_text = txt
        if not latest_employee_text and sender == "employee" and txt:
            latest_employee_text = txt

    reference_text = latest_msg_text or customer_scenario
    intent = _detect_intent(reference_text)
    sentiment = _detect_sentiment(persona, progression, employee_turns, reference_text)

    # 1. Supervisor Output
    supervisor = SupervisorOutput(
        status="Completed",
        active_pattern="Context-Aware LLM + RAG Retrieval",
        agents_completed=6,
    )

    # 2. Query Analysis Output
    snippet = reference_text.replace("\n", " ")
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."
    query_analysis = QueryAnalysisOutput(
        summary=f"Customer inquiry regarding {product_name}: '{snippet}'. Intent identified as {intent} with {sentiment} sentiment.",
        intent=intent,
        sentiment=sentiment,
    )

    # 3. Knowledge Retrieval Output
    articles: List[Article] = []
    if rag_context:
        for chunk in rag_context:
            title = _get_field(chunk, "title") or _get_field(chunk, "source") or f"{product_name} Knowledge Resource"
            source = _get_field(chunk, "source") or "knowledge_base/document"
            raw_score = _get_field(chunk, "score", 0.85)
            try:
                score_val = min(max(float(raw_score), 0.0), 1.0)
            except (ValueError, TypeError):
                score_val = 0.85
            raw_snippet = _get_field(chunk, "content") or _get_field(chunk, "snippet", "")
            clean_snippet = raw_snippet.strip()[:240] or f"Documentation relating to {product_name} operation and warranty coverage."
            articles.append(Article(
                title=title,
                source=source,
                relevance_score=score_val,
                snippet=clean_snippet,
            ))
    
    if not articles:
        articles = [
            Article(
                title=f"{product_name} Support & Hardware Replacement Policy",
                source="knowledge_base/warranty_policy.pdf",
                relevance_score=0.92,
                snippet=f"Standard warranty for {product_name} covers physical and functional defects within 1 year of purchase. Express replacements are dispatched within 48 hours for verified claims.",
            ),
            Article(
                title=f"{product_name} Troubleshooting & Diagnostic Procedures",
                source="knowledge_base/troubleshooting_guide.md",
                relevance_score=0.85,
                snippet=f"Step-by-step diagnostic guide for resetting {product_name}, verifying firmware updates, and resolving audio or connection anomalies.",
            ),
        ]

    faqs = [
        FAQ(
            question=f"What is the warranty and return policy for {product_name}?",
            answer=f"Customers are eligible for full warranty replacement or return within 30 days of delivery. Return shipping is prepaid for hardware defects.",
        ),
        FAQ(
            question=f"How long does express replacement dispatch take for {product_name}?",
            answer="Once the support agent initiates the RMA request, replacement tracking is emailed within 24 hours, and delivery arrives in 2 business days.",
        ),
    ]

    troubleshooting_steps = [
        f"Acknowledge the customer's experience with {product_name} and validate order / serial number.",
        f"Perform quick verification of symptoms (e.g. power cycle or 10-second factory reset).",
        f"If the issue persists, provide immediate resolution options (prepaid RMA shipping or expedited replacement).",
    ]

    knowledge_retrieval = KnowledgeRetrievalOutput(
        summary=f"Retrieved relevant knowledge articles, warranty guidelines, and troubleshooting procedures for {product_name}.",
        articles=articles,
        faqs=faqs,
        troubleshooting_steps=troubleshooting_steps,
    )

    # 4. Product Information Output
    if product:
        prod_name = _get_field(product, "product_name") or product_name
        prod_cat = _get_field(product, "product_category") or "Audio & Electronics"
        prod_desc = _get_field(product, "product_description") or product_context or f"Premium {product_name}."
    else:
        prod_name = product_name
        prod_cat = "Audio & Electronics"
        prod_desc = product_context or f"High-performance {product_name} equipped with active noise cancellation and ergonomic fit."

    product_information = ProductInformationOutput(
        product_name=prod_name,
        product_category=prod_cat,
        product_description=prod_desc,
        warranty_status="Active — Covered under 1-Year Limited Warranty (Eligible for Replacement)",
    )

    # 5. Response Generation Output
    if intent == "Hardware Defect / Replacement":
        suggested = (
            f"I am truly sorry to hear that your {product_name} has a defect. "
            f"That is certainly not the standard of quality we aim to provide. "
            f"I would be glad to arrange a replacement for you immediately under our express warranty. "
            f"Could you please confirm your order number and current shipping address so I can generate a prepaid return label?"
        )
    elif intent == "Billing / Refund Request":
        suggested = (
            f"I completely understand your concern regarding billing for your {product_name}. "
            f"I can review your transaction right away and initiate a full refund. "
            f"Could you please share your order or invoice number so I can pull up the account?"
        )
    elif intent == "Software / Connectivity Issue":
        suggested = (
            f"Thank you for contacting support regarding your {product_name}. "
            f"Connectivity issues can be frustrating, but we can often fix this with a 10-second factory reset. "
            f"Let's walk through the reset together, or if you prefer, I can verify your firmware version."
        )
    elif intent == "Product Setup / Usage Guidance":
        suggested = (
            f"Hello! I would be delighted to guide you through setting up your {product_name}. "
            f"Let's take it step by step. To begin, have you plugged the device in until the indicator turns solid white?"
        )
    else:
        suggested = (
            f"Hello! Thank you for reaching out to customer support. "
            f"I would be more than happy to help you with your {product_name}. "
            f"Could you provide your order number or tell me a bit more about what you need assistance with today?"
        )

    response_generation = ResponseGenerationOutput(
        suggested_response=suggested,
    )

    # 6. Evaluation and Coaching Output
    # Evaluate employee response if present, else baseline readiness
    base_score = 75
    tips: List[str] = []

    if latest_employee_text:
        emp_lower = latest_employee_text.lower()
        has_empathy = any(w in emp_lower for w in ["sorry", "apologize", "understand", "pleasure", "glad", "hear that"])
        has_action = any(w in emp_lower for w in ["replace", "refund", "order", "label", "steps", "tracking", "verify", "check", "fix"])
        
        if has_empathy:
            base_score += 10
            tips.append("Excellent empathetic phrasing demonstrated.")
        else:
            base_score -= 5
            tips.append("Incorporate an explicit apology or empathy statement to acknowledge the customer's frustration.")
            
        if has_action:
            base_score += 10
            tips.append("Clear actionable resolution steps provided.")
        else:
            tips.append("Specify clear next steps and timeline for the customer.")
    else:
        base_score = 80
        tips = [
            "Greet the customer warmly and validate their concerns immediately.",
            "Offer a proactive resolution timeline to minimize anxiety.",
        ]

    evaluation_score = min(max(base_score, 0), 100)
    evaluation_and_coaching = EvaluationAndCoachingOutput(
        evaluation_score=evaluation_score,
        tips=tips,
    )

    return AgentOutputs(
        supervisor=supervisor,
        query_analysis=query_analysis,
        knowledge_retrieval=knowledge_retrieval,
        product_information=product_information,
        response_generation=response_generation,
        evaluation_and_coaching=evaluation_and_coaching,
    )


def generate_mock_customer_reply(
    session: Any,
    messages: Optional[List[Any]] = None,
) -> str:
    """
    Deterministically generates simulated customer replies matching persona,
    scenario, emotional progression, and current turn count.
    """
    msgs = messages or []
    product_name = _get_field(session, "product_name") or "product"
    persona = (_get_field(session, "persona") or "Standard").capitalize()
    progression = (_get_field(session, "emotional_progression") or "stable").lower()
    
    # Calculate customer turn based on number of employee messages
    employee_turns = sum(1 for m in msgs if (_get_field(m, "sender") or _get_field(m, "role", "")).lower() == "employee")
    current_turn = max(employee_turns, 1)

    if persona == "Angry":
        if progression == "escalating_to_calm":
            if current_turn <= 1:
                return f"I am extremely upset about this! I paid full price and my {product_name} arrived defective. My order number is #ORD-98421—how quickly can you send a replacement?"
            elif current_turn == 2:
                return "Well, thank you for the apology and offering to replace it without hassle. That's reassuring. Do I need to send the defective one back first?"
            else:
                return "That sounds very fair and reasonable. Thank you for resolving this so efficiently. Please confirm the replacement tracking once it's on the way!"
        elif progression == "calm_to_frustrated":
            if current_turn <= 1:
                return f"Hello, I received my {product_name} today, but something seems wrong with the hardware. Here is my order number #ORD-98421. Can you help me look into it?"
            elif current_turn == 2:
                return "I've already tried basic diagnostics and this is taking way too long. I needed this working for an important project today!"
            else:
                return "This is completely ridiculous! I am done jumping through hoops. If this isn't replaced or refunded immediately, I'm filing a dispute with my bank!"
        else:  # stable or default
            if current_turn <= 1:
                return f"This is completely unacceptable! The {product_name} is broken right out of the box. My order number is #ORD-98421. What are you going to do about it?"
            elif current_turn == 2:
                return "I don't have time for long delays or excuses. Just make sure the replacement unit is thoroughly inspected before shipping so I don't go through this again."
            else:
                return "Fine, send over the prepaid return label. Please make sure the replacement ships via expedited delivery today."

    elif persona == "Impatient":
        if progression == "calm_to_frustrated":
            if current_turn <= 1:
                return f"Need help with order #ORD-77123 for my {product_name}. Can we get this sorted quickly?"
            elif current_turn == 2:
                return "I really don't have time for a lengthy back-and-forth diagnostic. Can you just send the replacement or not?"
            else:
                return "This is taking too long. Cancel the order and refund my card immediately."
        else:  # stable or escalating_to_calm
            if current_turn <= 1:
                return f"I'm in a rush. Order #ORD-77123. Can you skip the questionnaire and just send out a replacement {product_name}?"
            elif current_turn == 2:
                return "Understood. How soon will the replacement arrive? I need it before Friday."
            else:
                return "Great, thanks for expediting that. Please email me the tracking confirmation right away."

    elif persona == "Confused":
        if current_turn <= 1:
            return f"Hello... I'm really confused by the instructions for the {product_name}. The lights don't match the booklet and I'm not sure which button to press. My order is #ORD-55412."
        elif current_turn == 2:
            return "Wait, do I press the top button or the side button? The light is blinking amber now—is that supposed to happen?"
        else:
            return "Oh, I see it now! That worked! Thank you so much for walking me through it step-by-step, I really appreciate your patience."

    elif persona == "Patient":
        if current_turn <= 1:
            return f"Good day! Thank you for assisting me today. My order number is #ORD-12390 for the {product_name}. Please let me know what troubleshooting steps you'd like me to try."
        elif current_turn == 2:
            return "Thank you for the clear instructions. I have completed those steps, but the indicator still isn't turning green. What should we try next?"
        else:
            return "Everything looks resolved on my end now. Thank you so much for your outstanding support and courtesy!"

    else:  # Standard
        if current_turn <= 1:
            return f"Hello, I need assistance with my {product_name}. It seems to have an issue. My order number is #ORD-66201."
        elif current_turn == 2:
            return "Thank you for that information. That makes sense, I will proceed with those steps."
        else:
            return "That answered all my questions and fixed the issue. Thank you for your help today!"


def generate_mock_coaching_report(
    session: Any,
    messages: Optional[List[Any]] = None,
) -> CoachingReportResponse:
    """
    Deterministically generates a complete CoachingReportResponse matching all 10 schema fields.
    Evaluates employee empathy, policy adherence, and resolution clarity across the transcript.
    """
    msgs = messages or []
    session_id = str(_get_field(session, "session_id") or "sess-default")
    product_name = _get_field(session, "product_name") or "Product"
    customer_scenario = _get_field(session, "customer_scenario") or "Customer support interaction"
    persona = (_get_field(session, "persona") or "Standard").capitalize()
    progression = (_get_field(session, "emotional_progression") or "stable").lower()

    # Generate deterministic report ID
    short_id = session_id.split("-")[-1] if "-" in session_id else session_id[:8]
    report_id = f"REP-{short_id.upper()}"

    # Analyze employee messages
    employee_msgs = [
        (_get_field(m, "message_text") or _get_field(m, "text") or _get_field(m, "content", "")).lower()
        for m in msgs
        if (_get_field(m, "sender") or _get_field(m, "role", "")).lower() == "employee"
    ]

    base_score = 82
    has_empathy = any(any(w in text for w in ["sorry", "apologize", "understand", "pleasure", "glad to help"]) for text in employee_msgs)
    has_resolution = any(any(w in text for w in ["replace", "refund", "tracking", "label", "order", "processed", "rma"]) for text in employee_msgs)
    has_sla = any(any(w in text for w in ["business days", "hours", "today", "timeline", "expedited", "2 days"]) for text in employee_msgs)

    if has_empathy:
        base_score += 6
    if has_resolution:
        base_score += 6
    if has_sla:
        base_score += 4

    evaluation_score = min(max(base_score, 0), 100)

    # Customer sentiment progression
    if persona == "Angry":
        sentiment = "Frustrated -> De-escalated / Calm" if progression == "escalating_to_calm" else "Frustrated / Demanding"
    elif persona == "Confused":
        sentiment = "Confused -> Clarified / Reassured"
    elif persona == "Impatient":
        sentiment = "Impatient -> Expedited / Satisfied"
    elif persona == "Patient":
        sentiment = "Cooperative / Highly Satisfied"
    else:
        sentiment = "Neutral -> Satisfied"

    summary = (
        f"Support interaction concerning {product_name} addressing the scenario: '{customer_scenario}'. "
        f"Conversation spanned {len(msgs)} total messages between employee and {persona} customer."
    )

    evaluation = (
        f"The employee demonstrated a high level of professionalism and active listening while addressing "
        f"the customer's inquiries regarding {product_name}. Responses maintained positive customer service standards, "
        f"adhered to company warranty protocols, and provided clear, actionable next steps."
    )

    strengths = [
        "Prompt acknowledgment and sincere empathy toward customer situation",
        f"Accurate knowledge of {product_name} warranty guidelines and replacement policy",
        "Clear and structured communication of immediate next steps",
    ]

    areas_for_improvement = [
        "Explicitly state express replacement shipping delivery timelines earlier in dialogue",
        "Proactively offer tracking notification confirmation before closing the inquiry",
    ]

    recommendations = [
        "Utilize the Dead-On-Arrival (DOA) fast-track replacement macro for damaged goods",
        "Offer customer self-service order tracking link via email",
    ]

    recommended_replies = [
        f"Thank you for contacting customer support regarding your {product_name}. Your replacement order has been submitted and will arrive in 2 business days. Please let us know if we can assist you with anything else!",
    ]

    return CoachingReportResponse(
        report_id=report_id,
        session_id=session_id,
        conversation_summary=summary,
        customer_sentiment=sentiment,
        evaluation_score=evaluation_score,
        employee_evaluation=evaluation,
        strengths=strengths,
        areas_for_improvement=areas_for_improvement,
        recommendations=recommendations,
        recommended_replies=recommended_replies,
    )
