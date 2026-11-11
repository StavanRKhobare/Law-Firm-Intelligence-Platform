"""
Crime Type Classification Model
Predicts crime types using Random Forest and XGBoost
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.feature_extraction.text import TfidfVectorizer
import xgboost as xgb
import joblib
from collections import Counter
from typing import Dict, List, Tuple
import warnings

warnings.filterwarnings("ignore")


class CrimeTypeClassifier:
    def __init__(self, model_type: str = "random_forest", model_dir: str = "models/classifier"):
        self.model_type = model_type
        self.model_dir = model_dir
        self.model = None

        self.label_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=100, stop_words="english"
        )

        self.feature_names = []
        self.class_names = []

        # Used ONLY for XGBoost
        self.xgb_class_mapping = None
        self.xgb_reverse_mapping = None

    # ------------------------------------------------------------------
    # FEATURE PREPARATION
    # ------------------------------------------------------------------
    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        df = df.copy()

        df["primary_crime_type"] = (
            df["crime_types"].fillna("Unknown").str.split("|").str[0]
        )
        df = df[df["primary_crime_type"] != "Unknown"]

        dt = pd.to_datetime(df["date_occ"])
        df["hour"] = dt.dt.hour
        df["day_of_week"] = dt.dt.dayofweek
        df["day_of_month"] = dt.dt.day
        df["month"] = dt.dt.month
        df["quarter"] = dt.dt.quarter
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

        df["city_encoded"] = LabelEncoder().fit_transform(df["city"].fillna("Unknown"))
        df["district_encoded"] = LabelEncoder().fit_transform(
            df["district"].fillna("Unknown")
        )

        df["evidence_count"] = df["evidence_count"].fillna(0)
        df["suspect_count"] = df["suspect_count"].fillna(0)
        df["victim_count"] = df["victim_count"].fillna(0)
        df["report_delay"] = df["report_delay_days"].fillna(0)

        status_map = {"Filed": 0, "Hearing": 1, "Disposed": 2, "Pending": 3}
        df["status_encoded"] = df["status"].map(status_map).fillna(0)

        tfidf = self.tfidf_vectorizer.fit_transform(
            df["crime_description"].fillna("")
        ).toarray()

        tfidf_df = pd.DataFrame(
            tfidf,
            columns=[f"tfidf_{i}" for i in range(tfidf.shape[1])],
            index=df.index,
        )

        df = pd.concat([df, tfidf_df], axis=1)

        feature_cols = [
            "hour",
            "day_of_week",
            "day_of_month",
            "month",
            "quarter",
            "is_weekend",
            "city_encoded",
            "district_encoded",
            "evidence_count",
            "suspect_count",
            "victim_count",
            "report_delay",
            "status_encoded",
        ] + list(tfidf_df.columns)

        self.feature_names = feature_cols

        X = df[feature_cols]
        y = df["primary_crime_type"]

        return X, y

    # ------------------------------------------------------------------
    # TRAINING
    # ------------------------------------------------------------------
    def train(self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2):
        # Encode labels FIRST
        y_encoded = self.label_encoder.fit_transform(y)
        self.class_names = self.label_encoder.classes_

        class_counts = Counter(y_encoded)
        rare_classes = [c for c, n in class_counts.items() if n < 2]

        stratify = None if rare_classes else y_encoded

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y_encoded,
            test_size=test_size,
            random_state=42,
            stratify=stratify,
        )

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # ---------------- RANDOM FOREST ----------------
        if self.model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
            self.model.fit(X_train_scaled, y_train)

            y_pred = self.model.predict(X_test_scaled)

        # ---------------- XGBOOST (FIXED) ----------------
        elif self.model_type == "xgboost":
            # 🔥 Make labels contiguous
            unique_classes = np.unique(y_train)
            self.xgb_class_mapping = {
                old: new for new, old in enumerate(unique_classes)
            }
            self.xgb_reverse_mapping = {
                v: k for k, v in self.xgb_class_mapping.items()
            }

            y_train_fixed = np.array(
                [self.xgb_class_mapping[y] for y in y_train]
            )

            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=10,
                learning_rate=0.1,
                objective="multi:softprob",
                num_class=len(unique_classes),
                eval_metric="mlogloss",
                random_state=42,
                n_jobs=-1,
            )

            self.model.fit(X_train_scaled, y_train_fixed)

            y_pred_fixed = self.model.predict(X_test_scaled)
            y_pred = np.array(
                [
                    self.xgb_reverse_mapping[p]
                    for p in y_pred_fixed
                    if p in self.xgb_reverse_mapping
                ]
            )
            y_test = y_test[: len(y_pred)]

        # ---------------- EVALUATION ----------------
        print("\n=== Model Evaluation ===")
        print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
        print(
            f"F1 Score (weighted): {f1_score(y_test, y_pred, average='weighted'):.4f}"
        )

        labels = np.unique(y_test)
        print(
            classification_report(
                y_test,
                y_pred,
                labels=labels,
                target_names=self.label_encoder.inverse_transform(labels),
                zero_division=0,
            )
        )

        return {
            "accuracy": accuracy_score(y_test, y_pred),
            "f1_score": f1_score(y_test, y_pred, average="weighted"),
        }

    # ------------------------------------------------------------------
    # PREDICTION
    # ------------------------------------------------------------------
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        X_scaled = self.scaler.transform(X)

        if self.model_type == "xgboost":
            preds_fixed = self.model.predict(X_scaled)
            preds = [self.xgb_reverse_mapping[p] for p in preds_fixed]
            return self.label_encoder.inverse_transform(preds)

        preds = self.model.predict(X_scaled)
        return self.label_encoder.inverse_transform(preds)

    # ------------------------------------------------------------------
    # SAVE / LOAD
    # ------------------------------------------------------------------
    def save_model(self, filepath: str = None):
        if filepath is None:
            filepath = f"{self.model_dir}/crime_classifier_{self.model_type}.pkl"

        joblib.dump(
            {
                "model": self.model,
                "label_encoder": self.label_encoder,
                "scaler": self.scaler,
                "tfidf_vectorizer": self.tfidf_vectorizer,
                "feature_names": self.feature_names,
                "class_names": self.class_names,
                "model_type": self.model_type,
                "xgb_class_mapping": self.xgb_class_mapping,
                "xgb_reverse_mapping": self.xgb_reverse_mapping,
            },
            filepath,
        )
        print(f"Model saved to {filepath}")


    def load_model(self, filepath: str):
        data = joblib.load(filepath)
        self.model = data["model"]
        self.label_encoder = data["label_encoder"]
        self.scaler = data["scaler"]
        self.tfidf_vectorizer = data["tfidf_vectorizer"]
        self.feature_names = data["feature_names"]
        self.class_names = data["class_names"]
        self.model_type = data["model_type"]
        self.xgb_class_mapping = data["xgb_class_mapping"]
        self.xgb_reverse_mapping = data["xgb_reverse_mapping"]
        print(f"Model loaded from {filepath}")
