"""
Pass 2 — machine-learning message classifier.

A scikit-learn pipeline that fuses three views of each message:

  1. word TF-IDF (1-2 grams) on de-obfuscated text   -> vocabulary/slang
  2. char TF-IDF (3-5 grams, char_wb)                 -> survives obfuscation
                                                          & catches Hinglish
  3. engineered numeric features (rule score, price,
     bot command, obfuscation score, ...)             -> behaviour/structure

Classifier: L2 logistic regression (class-balanced). It gives calibrated-ish
probabilities, handles the sparse high-dim TF-IDF space natively, trains in
seconds on CPU, and its coefficients stay inspectable — important for a tool
whose output may support a legal request.

Trained on weak labels (rule engine) + synthetic data + any hand labels, so it
generalizes beyond the hand-written rules.
"""

from __future__ import annotations

import numpy as np

from ..config import ML_MODEL_FILE, MODEL_DIR
from ..processing import deobfuscate
from ..features.engineer import message_features, numeric_vector


# --- module-level transformers (must be importable for pickling) -------------

def _numeric_matrix(texts):
    return np.array(
        [numeric_vector(message_features(t)) for t in texts], dtype=float
    )


def _build_pipeline():
    from sklearn.pipeline import Pipeline, FeatureUnion
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import FunctionTransformer, MaxAbsScaler
    from sklearn.linear_model import LogisticRegression

    features = FeatureUnion([
        ("word", TfidfVectorizer(
            preprocessor=deobfuscate, ngram_range=(1, 2),
            min_df=1, sublinear_tf=True,
        )),
        ("char", TfidfVectorizer(
            preprocessor=deobfuscate, analyzer="char_wb",
            ngram_range=(3, 5), min_df=1,
        )),
        ("num", Pipeline([
            ("extract", FunctionTransformer(_numeric_matrix)),
            ("scale", MaxAbsScaler()),
        ])),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(
            max_iter=2000, class_weight="balanced", C=4.0,
        )),
    ])


class MLClassifier:
    def __init__(self, pipeline=None):
        self.pipeline = pipeline

    # -- training -------------------------------------------------------------
    def fit(self, texts: list, labels: list) -> "MLClassifier":
        self.pipeline = _build_pipeline()
        self.pipeline.fit(texts, labels)
        return self

    def cross_val_report(self, texts: list, labels: list, folds: int = 5) -> dict:
        from sklearn.model_selection import cross_val_predict
        from sklearn.metrics import precision_recall_fscore_support, roc_auc_score

        pipe = _build_pipeline()
        y = np.asarray(labels)
        proba = cross_val_predict(
            pipe, texts, y, cv=folds, method="predict_proba"
        )[:, 1]
        pred = (proba >= 0.5).astype(int)
        p, r, f, _ = precision_recall_fscore_support(
            y, pred, average="binary", zero_division=0
        )
        try:
            auc = roc_auc_score(y, proba)
        except ValueError:
            auc = float("nan")
        return {
            "precision": round(float(p), 3),
            "recall": round(float(r), 3),
            "f1": round(float(f), 3),
            "roc_auc": round(float(auc), 3),
            "n": len(y),
            "positives": int(y.sum()),
        }

    # -- inference ------------------------------------------------------------
    def predict_proba(self, texts):
        if self.pipeline is None:
            raise RuntimeError("Model not trained/loaded. Run training first.")
        single = isinstance(texts, str)
        arr = [texts] if single else list(texts)
        proba = self.pipeline.predict_proba(arr)[:, 1]
        return float(proba[0]) if single else proba

    # -- persistence ----------------------------------------------------------
    def save(self, path=None):
        import joblib
        path = path or ML_MODEL_FILE
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path)
        return path

    @classmethod
    def load(cls, path=None):
        import joblib
        path = path or ML_MODEL_FILE
        return cls(pipeline=joblib.load(path))

    @classmethod
    def exists(cls, path=None) -> bool:
        path = path or ML_MODEL_FILE
        return path.exists()
