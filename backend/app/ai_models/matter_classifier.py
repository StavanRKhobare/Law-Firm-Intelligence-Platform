"""
Matter-type classifier.

Predicts one of five matter types (Criminal, Civil, Family, Corporate,
Constitutional) from a free-text description of a matter. The whole pipeline
(TF-IDF + classifier) is saved as one joblib file, so inference uses exactly
the vocabulary and weights fitted at training time.

Training data: ml_data/matter_types.csv (see ml_data/build_matter_dataset.py).
"""

import os
from typing import Dict, List

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DATA = os.path.join(BACKEND_DIR, "ml_data", "matter_types.csv")
DEFAULT_MODEL = os.path.join(BACKEND_DIR, "models", "classifier", "matter_classifier.pkl")


def _candidates() -> Dict[str, object]:
    return {
        "logistic_regression": LogisticRegression(max_iter=2000, C=10, class_weight="balanced"),
        "linear_svm": CalibratedClassifierCV(LinearSVC(C=0.5, class_weight="balanced"), cv=3),
        "random_forest": RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1),
    }


def _pipeline(clf) -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9,
                                  max_features=30000, sublinear_tf=True, stop_words="english")),
        ("clf", clf),
    ])


class MatterTypeClassifier:
    def __init__(self, model_path: str = DEFAULT_MODEL):
        self.model_path = model_path
        self.pipeline = None
        self.metrics: Dict = {}

    def train(self, data_path: str = DEFAULT_DATA, test_size: float = 0.2) -> Dict:
        """Fit every candidate on the same split and keep the best by macro F1."""
        df = pd.read_csv(data_path).dropna(subset=["text", "matter_type"])
        X_train, X_test, y_train, y_test = train_test_split(
            df["text"], df["matter_type"], test_size=test_size,
            stratify=df["matter_type"], random_state=42,
        )

        results, best_name, best_f1 = {}, None, -1.0
        for name, clf in _candidates().items():
            pipe = _pipeline(clf).fit(X_train, y_train)
            y_pred = pipe.predict(X_test)
            f1 = f1_score(y_test, y_pred, average="macro")
            results[name] = {"accuracy": round(accuracy_score(y_test, y_pred), 4), "f1_macro": round(f1, 4)}
            print(f"  {name:20s} accuracy={results[name]['accuracy']:.4f}  f1_macro={f1:.4f}")
            if f1 > best_f1:
                best_name, best_f1, self.pipeline, best_pred = name, f1, pipe, y_pred

        print(f"\nBest: {best_name}\n")
        print(classification_report(y_test, best_pred))
        self.metrics = {
            "best_model": best_name,
            "candidates": results,
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "class_counts": df["matter_type"].value_counts().to_dict(),
            "report": classification_report(y_test, best_pred, output_dict=True),
        }
        return self.metrics

    def save(self) -> str:
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({"pipeline": self.pipeline, "metrics": self.metrics}, self.model_path)
        return self.model_path

    def load(self) -> "MatterTypeClassifier":
        data = joblib.load(self.model_path)
        self.pipeline, self.metrics = data["pipeline"], data.get("metrics", {})
        return self

    @property
    def classes(self) -> List[str]:
        return list(self.pipeline.classes_)

    def predict(self, text: str, threshold: float = 0.5) -> Dict:
        proba = self.pipeline.predict_proba([text])[0]
        ranked = sorted(zip(self.pipeline.classes_, proba), key=lambda p: p[1], reverse=True)
        top, conf = ranked[0]
        return {
            "prediction": str(top),
            "confidence": round(float(conf), 4),
            "is_confident": bool(conf >= threshold),
            "top_3_predictions": [{"matter_type": str(c), "probability": round(float(p), 4)} for c, p in ranked[:3]],
        }
