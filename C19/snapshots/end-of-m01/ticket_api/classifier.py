import time
from dataclasses import dataclass

KEYWORDS = {
    "billing": ("invoice", "charged", "refund", "payment"),
    "login": ("password", "sign in", "log in", "two-factor", "locked out"),
    "shipping": ("parcel", "delivery", "courier", "tracking"),
    "account": ("account", "company name", "user"),
}
URGENT_WORDS = ("cannot", "locked out", "charged twice", "lost")


class ClassifierUnavailable(Exception):
    """The classifier cannot answer now. The request may work later."""


@dataclass(frozen=True)
class Prediction:
    category: str
    priority: int
    confidence: float


class KeywordClassifier:
    """A deterministic stand-in for a trained model: the same text always
    gives the same prediction."""

    version = "keywords-1.0"

    def predict(self, text: str) -> Prediction:
        lowered = text.lower()
        scores = {
            category: sum(word in lowered for word in words)
            for category, words in KEYWORDS.items()
        }
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return Prediction(category="other", priority=3, confidence=0.2)
        urgent = any(word in lowered for word in URGENT_WORDS)
        confidence = min(0.5 + 0.2 * scores[best], 0.95)
        return Prediction(
            category=best, priority=1 if urgent else 2, confidence=round(confidence, 2)
        )


class UnavailableClassifier:
    """Simulates a classifier that is down."""

    version = "unavailable"

    def predict(self, text: str) -> Prediction:
        raise ClassifierUnavailable("the classifier is not available")


class SlowClassifier(KeywordClassifier):
    """Simulates a classifier that takes too long to answer."""

    version = "slow"

    def predict(self, text: str) -> Prediction:
        time.sleep(5)
        return super().predict(text)


def make_classifier(mode: str) -> KeywordClassifier | UnavailableClassifier:
    classifiers = {
        "keywords": KeywordClassifier,
        "unavailable": UnavailableClassifier,
        "slow": SlowClassifier,
    }
    if mode not in classifiers:
        raise ValueError(f"unknown CLASSIFIER_MODE {mode!r}")
    return classifiers[mode]()
