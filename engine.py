"""UNSW-NB15 üzerinde etiket kullanmadan anomali modeli ve ölçüm yardımcıları."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd
from pandas.util import hash_pandas_object
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, RobustScaler


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ARTIFACTS = ROOT / "artifacts"
TRAIN_CSV = DATA / "UNSW_NB15_training-set.csv"
TEST_CSV = DATA / "UNSW_NB15_testing-set.csv"
MODEL_FILE = ARTIFACTS / "isolation_forest.joblib"
SCORED_FILE = ARTIFACTS / "test_scored.parquet"
FORBIDDEN = {"id", "label", "attack_cat"}
SEED = 26


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not TRAIN_CSV.is_file() or not TEST_CSV.is_file():
        raise FileNotFoundError("UNSW-NB15 eğitim ve test CSV dosyalarını data/ klasörüne koyun.")
    train = pd.read_csv(TRAIN_CSV)
    test = pd.read_csv(TEST_CSV)
    needed = {"label", "attack_cat", "proto", "service", "state"}
    if not needed.issubset(train.columns) or set(train.columns) != set(test.columns):
        raise ValueError("Eğitim/test CSV şemaları beklenen UNSW-NB15 biçiminde değil.")
    if not set(train["label"].unique()).issubset({0, 1}) or not set(test["label"].unique()).issubset({0, 1}):
        raise ValueError("İkili etiketler 0/1 olmalı.")
    return train, test


def feature_columns(frame: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    columns = [column for column in frame.columns if column not in FORBIDDEN]
    categorical = [column for column in columns if not pd.api.types.is_numeric_dtype(frame[column])]
    numerical = [column for column in columns if column not in categorical]
    return columns, categorical, numerical


def _nonnegative_log(values):
    return np.log1p(np.clip(values, 0, None))


def make_preprocessor(categorical: list[str], numerical: list[str]) -> ColumnTransformer:
    numeric = Pipeline([
        ("missing", SimpleImputer(strategy="median")),
        ("log", FunctionTransformer(_nonnegative_log, feature_names_out="one-to-one")),
        ("scale", RobustScaler()),
    ])
    nominal = Pipeline([
        ("missing", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
    ])
    return ColumnTransformer([("numeric", numeric, numerical), ("categorical", nominal, categorical)],
                             sparse_threshold=0.3)


def evaluate(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    predicted = (scores >= threshold).astype(int)
    tn, fp, fn, tp = [int(item) for item in confusion_matrix(labels, predicted, labels=[0, 1]).ravel()]
    precision, recall, f1, _ = precision_recall_fscore_support(labels, predicted, average="binary", zero_division=0)
    return {
        "threshold": float(threshold), "precision": float(precision), "recall": float(recall),
        "f1": float(f1), "average_precision": float(average_precision_score(labels, scores)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
        "alerts_per_1000_normal": float(fp / (fp + tn) * 1000) if fp + tn else 0.0,
    }


def normal_reference(frame: pd.DataFrame, categorical: list[str], numerical: list[str]) -> dict:
    numeric = {}
    for column in numerical:
        values = pd.to_numeric(frame[column], errors="coerce").dropna()
        numeric[column] = {
            "p01": float(values.quantile(.01)), "median": float(values.median()),
            "p99": float(values.quantile(.99)),
        }
    categories = {}
    for column in categorical:
        categories[column] = frame[column].astype(str).value_counts(normalize=True).to_dict()
    return {"numeric": numeric, "categorical": categories}


def explain_outlier(row: pd.Series | dict, reference: dict, limit: int = 3) -> list[str]:
    """Normal dağılımla farkları gösterir; modelin nedensel açıklaması değildir."""
    hints: list[tuple[float, str]] = []
    for column, stats in reference["numeric"].items():
        try:
            value = float(row[column])
        except (ValueError, TypeError, KeyError):
            continue
        width = max(abs(stats["p99"] - stats["median"]), 1.0)
        if value > stats["p99"]:
            distance = (value - stats["p99"]) / width
            hints.append((distance + 1, f"{column}: normal %99 sınırının üstünde ({value:.2g})"))
        elif value < stats["p01"]:
            distance = (stats["p01"] - value) / width
            hints.append((distance + 1, f"{column}: normal %1 sınırının altında ({value:.2g})"))
    for column, frequencies in reference["categorical"].items():
        value = str(row.get(column, ""))
        frequency = frequencies.get(value, 0.0)
        if frequency < .01:
            hints.append((3 if frequency == 0 else 1.5, f"{column}: normal trafikte seyrek ({value})"))
    hints.sort(key=lambda pair: pair[0], reverse=True)
    return [text for _, text in hints[:limit]] or ["Tek bir alan çok ayrışmıyor; birleşik akış örüntüsü aykırı."]


@dataclass
class Bundle:
    preprocessor: ColumnTransformer
    model: IsolationForest
    columns: list[str]
    categorical: list[str]
    numerical: list[str]
    normal_validation_scores: np.ndarray
    reference: dict
    metadata: dict
    supervised: RandomForestClassifier | None = None
    supervised_normal_validation_scores: np.ndarray | None = None

    def scores(self, frame: pd.DataFrame) -> np.ndarray:
        transformed = self.preprocessor.transform(frame[self.columns])
        return -self.model.score_samples(transformed)

    def threshold(self, target_fpr: float) -> float:
        if not 0 < target_fpr < 1:
            raise ValueError("Hedef yanlış alarm oranı 0 ile 1 arasında olmalı.")
        return float(np.quantile(self.normal_validation_scores, 1 - target_fpr))

    def supervised_threshold(self, target_fpr: float) -> float:
        if self.supervised_normal_validation_scores is None:
            raise ValueError("Etiketli referans doğrulama skorları yok.")
        return float(np.quantile(self.supervised_normal_validation_scores, 1 - target_fpr))


def train_model() -> tuple[Bundle, pd.DataFrame, dict]:
    train, test = load_data()
    columns, categorical, numerical = feature_columns(train)
    train_hash = hash_pandas_object(train[columns], index=False)
    test_hash = hash_pandas_object(test[columns], index=False)
    label_counts = pd.DataFrame({"hash": train_hash, "label": train["label"]}).groupby("hash")["label"].nunique()
    conflicting = set(label_counts.loc[label_counts > 1].index)
    clean_train = train.loc[~train_hash.isin(conflicting)].drop_duplicates(subset=columns)
    normal = clean_train.loc[clean_train["label"] == 0]
    normal_train, normal_val = train_test_split(normal, test_size=.2, random_state=SEED)
    started = time.perf_counter()
    preprocessor = make_preprocessor(categorical, numerical)
    transformed = preprocessor.fit_transform(normal_train[columns])
    model = IsolationForest(n_estimators=180, max_samples=512, contamination="auto",
                            random_state=SEED, n_jobs=-1)
    model.fit(transformed)
    train_seconds = time.perf_counter() - started
    val_scores = -model.score_samples(preprocessor.transform(normal_val[columns]))
    bundle = Bundle(preprocessor, model, columns, categorical, numerical, val_scores,
                    normal_reference(normal_train, categorical, numerical),
                    {"train_normal": len(normal_train), "validation_normal": len(normal_val),
                     "train_supervised": len(clean_train), "test_records": len(test),
                     "feature_count": len(columns),
                     "training_seconds": round(train_seconds, 2), "seed": SEED,
                     "dataset": "UNSW-NB15 published train/test split"})
    test_started = time.perf_counter()
    scores = bundle.scores(test)
    inference_seconds = time.perf_counter() - test_started
    scored = test.copy()
    scored["anomaly_score"] = scores
    scored["unique_unseen"] = (~test_hash.isin(set(train_hash))) & (~test_hash.duplicated())

    # Etiketleri kullanan karşılaştırma modeli; anomali modelinden ayrı tutulur.
    baseline_started = time.perf_counter()
    supervised = RandomForestClassifier(n_estimators=120, max_depth=18, min_samples_leaf=2,
                                        class_weight="balanced_subsample", random_state=SEED, n_jobs=-1)
    supervised_train = clean_train.drop(index=normal_val.index)
    supervised.fit(preprocessor.transform(supervised_train[columns]), supervised_train["label"].to_numpy())
    baseline_train_seconds = time.perf_counter() - baseline_started
    supervised_val = supervised.predict_proba(preprocessor.transform(normal_val[columns]))[:, 1]
    probability = supervised.predict_proba(preprocessor.transform(test[columns]))[:, 1]
    scored["supervised_probability"] = probability
    bundle.supervised = supervised
    bundle.supervised_normal_validation_scores = supervised_val
    supervised_default_threshold = bundle.supervised_threshold(.02)
    scored["supervised_alert_default"] = probability >= supervised_default_threshold
    default_threshold = bundle.threshold(.02)
    scored["alert_default"] = scores >= default_threshold
    unseen = scored.loc[scored["unique_unseen"]]
    metrics = evaluate(unseen["label"].to_numpy(), unseen["anomaly_score"].to_numpy(), default_threshold)
    metrics.update(bundle.metadata)
    metrics["inference_seconds"] = round(inference_seconds, 2)
    metrics["target_validation_fpr"] = .02
    metrics["evaluation_records"] = len(unseen)
    metrics["full_test"] = evaluate(test["label"].to_numpy(), scores, default_threshold)
    metrics["data_audit"] = {
        "train_duplicate_rows": int(train_hash.duplicated().sum()),
        "test_duplicate_rows": int(test_hash.duplicated().sum()),
        "test_rows_seen_in_train": int(test_hash.isin(set(train_hash)).sum()),
        "conflicting_train_feature_groups": len(conflicting),
    }
    metrics["attack_recall_by_type"] = {
        str(category): round(float(group["alert_default"].mean()), 4)
        for category, group in unseen.loc[unseen["label"] == 1].groupby("attack_cat")
    }
    metrics["supervised"] = evaluate(unseen["label"].to_numpy(), unseen["supervised_probability"].to_numpy(),
                                     supervised_default_threshold)
    metrics["supervised"]["training_seconds"] = round(baseline_train_seconds, 2)
    metrics["supervised_full_test"] = evaluate(test["label"].to_numpy(), probability, supervised_default_threshold)
    return bundle, scored, metrics


def save_artifacts(bundle: Bundle, scored: pd.DataFrame, metrics: dict) -> None:
    import json
    ARTIFACTS.mkdir(exist_ok=True)
    joblib.dump(bundle, MODEL_FILE, compress=3)
    scored.to_parquet(SCORED_FILE, index=False)
    (ARTIFACTS / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")


def load_bundle() -> Bundle:
    # Joblib dosyası yalnızca bu proje tarafından üretilmiş güvenilir yerel dosyadan yüklenir.
    return joblib.load(MODEL_FILE)
