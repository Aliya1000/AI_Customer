"""Deterministic offline LLM mock service for hermetic testing."""

from typing import Dict, Any, List, Optional


class DeterministicMockLLMService:
    """Provides deterministic, schema-compliant responses without external network access."""

    @staticmethod
    def generate_agent_outputs(
        product_name: str = "AeroSound Pro ANC Headphones",
        product_category: str = "Audio Hardware",
        product_description: str = "Wireless Bluetooth 5.3 over-ear headphones with ANC.",
        warranty_status: str = "Active (1-Year Hardware Warranty)",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return {
            "supervisor": {
                "status": "Completed (Mock)",
                "active_pattern": "Context-Aware LLM + RAG Retrieval",
                "agents_completed": 6,
            },
            "query_analysis": {
                "summary": "Customer reported audio defect with buzzing sound in ANC mode.",
                "intent": "Hardware Defect / Troubleshooting",
                "sentiment": "Frustrated / Urgent",
            },
            "knowledge_retrieval": {
                "summary": "Retrieved hardware reset instructions and ANC calibration steps.",
                "articles": [
                    {
                        "title": "AeroSound Pro User Guide",
                        "source": "knowledge-docs/manual.pdf",
                        "relevance_score": 0.94,
                        "snippet": "To reset ANC calibration, hold both volume buttons for 5 seconds.",
                    }
                ],
                "faqs": [
                    {
                        "question": "What causes buzzing in ANC mode?",
                        "answer": "Microphone acoustic feedback due to uncalibrated firmware.",
                    }
                ],
                "troubleshooting_steps": [
                    "Perform factory reset (hold power 10s)",
                    "Check ear cushion seal",
                    "Recalibrate ANC via mobile app",
                ],
            },
            "product_information": {
                "product_name": product_name,
                "product_category": product_category,
                "product_description": product_description,
                "warranty_status": warranty_status,
            },
            "response_generation": {
                "suggested_response": "I understand how frustrating that buzzing noise is. Let's perform a quick 10-second factory reset to resolve it.",
            },
            "evaluation_and_coaching": {
                "evaluation_score": 88,
                "tips": [
                    "Acknowledge the customer's frustration immediately",
                    "Offer the factory reset step before suggesting warranty replacement",
                ],
            },
        }

    @staticmethod
    def generate_customer_reply(
        persona: Optional[str] = "Patient",
        message_history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        persona_lower = (persona or "patient").lower()
        if "angry" in persona_lower:
            return "This is completely unacceptable! I followed your steps and the buzzing is even louder now!"
        elif "impatient" in persona_lower:
            return "Can we skip to replacing this? I don't have all day to reset my headphones."
        elif "confused" in persona_lower:
            return "Which button is the power button? The manual shows two different buttons."
        elif "patient" in persona_lower:
            return "Thank you for the steps. I held the power button and the LED flashed blue. What should I check next?"
        return "I tried the instructions you provided. What is the next step?"

    @staticmethod
    def generate_coaching_report(session_id: str, message_count: int = 2) -> Dict[str, Any]:
        suffix = session_id[-4:] if len(session_id) >= 4 else "0001"
        return {
            "report_id": f"REP-MOCK-{suffix}",
            "session_id": session_id,
            "conversation_summary": "Customer experienced ANC buzzing; employee walked through reset protocol.",
            "customer_sentiment": "Resolved / Calm",
            "evaluation_score": 86,
            "employee_evaluation": "The employee demonstrated strong empathy and followed technical troubleshooting guidelines effectively.",
            "strengths": [
                "Immediate empathy statement",
                "Clear numbered troubleshooting steps",
                "Prompt response time",
            ],
            "areas_for_improvement": [
                "Could have confirmed warranty coverage earlier in the dialogue",
            ],
            "recommendations": [
                "Reference the specific knowledge base article title when suggesting firmware updates",
            ],
            "recommended_replies": [
                "I see your device is covered under warranty until December, so if this reset doesn't help, we will ship a replacement right away.",
            ],
        }
