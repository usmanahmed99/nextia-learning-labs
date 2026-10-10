import time
from dataclasses import dataclass

KEYWORDS = {
    "billing": ("invoice", "charged", "refund", "payment"),
    "login": ("password", "sign in", "log in", "two-factor", "locked out"),
    "shipping": ("parcel", "delivery", "courier", "tracking"),
    "account": ("account", "company name", "user"),
}
URGENT_WORDS = ("cannot", "locked out", "charged twice", "lost")

# keywords-1.1: more words for each category, found in the evaluation set's
# development cases. Login words are checked before "account", so "I cannot
# log in to my account" is a login ticket.
KEYWORDS_1_1 = {
    "billing": KEYWORDS["billing"] + ("bill", "overcharged", "receipt", "subscription"),
    "login": KEYWORDS["login"] + ("reset link", "verification code", "2fa", "can't sign"),
    "shipping": KEYWORDS["shipping"] + ("package", "arrived", "delivered", "shipment"),
    "account": KEYWORDS["account"] + ("email address", "profile", "delete my"),
}
URGENT_WORDS_1_1 = URGENT_WORDS + ("can't sign", "never arrived", "urgent")

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
    keywords = KEYWORDS
    urgent_words = URGENT_WORDS

    def predict(self, text: str) -> Prediction:
        lowered = text.lower()
        scores = {
            category: sum(word in lowered for word in words)
            for category, words in self.keywords.items()
        }
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return Prediction(category="other", priority=3, confidence=0.2)
        urgent = any(word in lowered for word in self.urgent_words)
        confidence = min(0.5 + 0.2 * scores[best], 0.95)
        return Prediction(
            category=best, priority=1 if urgent else 2, confidence=round(confidence, 2)
        )


class KeywordClassifier11(KeywordClassifier):
    """keywords-1.1: the same method with more words."""

    version = "keywords-1.1"
    keywords = KEYWORDS_1_1
    urgent_words = URGENT_WORDS_1_1


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


def make_classifier(
    mode: str, version: str = "1.0"
) -> KeywordClassifier | UnavailableClassifier:
    if mode == "keywords":
        versions = {"1.0": KeywordClassifier, "1.1": KeywordClassifier11}
        if version not in versions:
            raise ValueError(f"unknown CLASSIFIER_VERSION {version!r}")
        return versions[version]()
    classifiers = {
        "unavailable": UnavailableClassifier,
        "slow": SlowClassifier,
    }
    if mode not in classifiers:
        raise ValueError(f"unknown CLASSIFIER_MODE {mode!r}")
    return classifiers[mode]()
