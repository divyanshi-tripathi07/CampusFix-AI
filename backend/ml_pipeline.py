"""Small, explainable ML pipeline for complaint classification and duplicate detection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

TRAINING_ROWS = [
    ("wifi disconnects in the engineering building", "Wi-Fi & Network", "High"),
    ("internet is unavailable in the computer lab", "Wi-Fi & Network", "High"),
    ("projector is not displaying the lecture", "Classrooms", "Medium"),
    ("classroom board is damaged", "Classrooms", "Low"),
    ("lights are flickering in the corridor", "Electricity", "High"),
    ("power outage in the south wing", "Electricity", "Critical"),
    ("tap is leaking outside the laboratory", "Water Supply", "High"),
    ("drinking water filter is empty", "Water Supply", "Medium"),
    ("washroom has no soap", "Washrooms", "Low"),
    ("restroom is blocked and unsafe", "Washrooms", "High"),
    ("trash bins are overflowing", "Cleanliness", "Medium"),
    ("dust and garbage near the student centre", "Cleanliness", "Low"),
    ("desktop computer will not start", "Computer Labs", "High"),
    ("printer is broken in the lab", "Computer Labs", "Medium"),
    ("fire alarm is sounding in the hostel", "Other Facilities", "Critical"),
    ("broken bench near the garden", "Other Facilities", "Low"),
]

@dataclass
class Models:
    category_vectorizer: Any
    category_model: Any
    priority_vectorizer: Any
    priority_model: Any


def train_models() -> Models:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    texts = [row[0] for row in TRAINING_ROWS]
    categories = [row[1] for row in TRAINING_ROWS]
    priorities = [row[2] for row in TRAINING_ROWS]
    category_vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
    priority_vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
    category_model = LogisticRegression(max_iter=500, random_state=7).fit(category_vectorizer.fit_transform(texts), categories)
    priority_model = LogisticRegression(max_iter=500, random_state=7).fit(priority_vectorizer.fit_transform(texts), priorities)
    return Models(category_vectorizer, category_model, priority_vectorizer, priority_model)


def evaluate_models() -> dict[str, float | int]:
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split

    texts = [row[0] for row in TRAINING_ROWS]
    categories = [row[1] for row in TRAINING_ROWS]
    priorities = [row[2] for row in TRAINING_ROWS]
    train_texts, test_texts, train_categories, test_categories = train_test_split(texts, categories, test_size=0.5, random_state=7, stratify=categories)
    vectorizer = __import__("sklearn.feature_extraction.text", fromlist=["TfidfVectorizer"]).TfidfVectorizer(ngram_range=(1, 2))
    model = __import__("sklearn.linear_model", fromlist=["LogisticRegression"]).LogisticRegression(max_iter=500, random_state=7)
    model.fit(vectorizer.fit_transform(train_texts), train_categories)
    category_accuracy = float(accuracy_score(test_categories, model.predict(vectorizer.transform(test_texts))))
    return {"training_examples": len(TRAINING_ROWS), "category_accuracy": category_accuracy, "priority_labels": len(set(priorities))}


def predict(text: str, models: Models | None = None) -> dict[str, Any]:
    try:
        models = models or train_models()
        category_features = models.category_vectorizer.transform([text])
        priority_features = models.priority_vectorizer.transform([text])
        category_probabilities = models.category_model.predict_proba(category_features)[0]
        priority_probabilities = models.priority_model.predict_proba(priority_features)[0]
        category_index = int(category_probabilities.argmax())
        priority_index = int(priority_probabilities.argmax())
        return {"category": str(models.category_model.classes_[category_index]), "priority": str(models.priority_model.classes_[priority_index]), "confidence": round(float(category_probabilities[category_index]), 3), "source": "tfidf-logistic-regression"}
    except (ImportError, ValueError, AttributeError):
        return {"category": "Other Facilities", "priority": "Medium", "confidence": 0.0, "source": "rule-based-fallback"}


def find_duplicate(text: str, existing_texts: Sequence[str], threshold: float = 0.62) -> dict[str, Any] | None:
    if not existing_texts:
        return None
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform([text, *existing_texts])
        scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
        best_index = int(scores.argmax())
        best_score = float(scores[best_index])
        return {"index": best_index, "score": round(best_score, 3)} if best_score >= threshold else None
    except (ImportError, ValueError):
        return None
