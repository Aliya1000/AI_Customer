"""
DSPy / Systematic Prompt Optimization Module.
Allows automated iterative optimization of prompt instructions against eval metrics.
"""

from typing import List, Dict, Any, Callable


class PromptCandidate:
    def __init__(self, template: str, version: int = 1):
        self.template = template
        self.version = version
        self.scores: List[float] = []

    @property
    def average_score(self) -> float:
        return sum(self.scores) / len(self.scores) if self.scores else 0.0


class PromptOptimizer:
    def __init__(self, metric_fn: Optional[Callable[[str, str], float]] = None):
        self.metric_fn = metric_fn or (lambda expected, pred: 1.0 if expected in pred else 0.5)
        self.candidates: List[PromptCandidate] = []

    def register_candidate(self, template: str) -> PromptCandidate:
        candidate = PromptCandidate(template, version=len(self.candidates) + 1)
        self.candidates.append(candidate)
        return candidate

    def evaluate_candidate(
        self,
        candidate: PromptCandidate,
        eval_dataset: List[Dict[str, str]],
    ) -> float:
        """Runs candidate prompt through evaluation dataset and records metrics."""
        scores = []
        for example in eval_dataset:
            # Simulate prompt formatting & evaluation
            formatted = candidate.template.format(**example)
            score = self.metric_fn(example.get("target", ""), formatted)
            scores.append(score)

        candidate.scores.extend(scores)
        return candidate.average_score

    def get_best_prompt(self) -> Optional[PromptCandidate]:
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda c: c.average_score)
