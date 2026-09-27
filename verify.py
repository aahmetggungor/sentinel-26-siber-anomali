"""Kayıtlı model ve raporun veri ayrımı/ölçüm tutarlılığını yeniden denetle."""

import json

import numpy as np
import pandas as pd
from pandas.util import hash_pandas_object

from engine import ARTIFACTS, SCORED_FILE, evaluate, feature_columns, load_bundle, load_data


def main() -> None:
    train, test = load_data()
    columns, _, _ = feature_columns(train)
    scored = pd.read_parquet(SCORED_FILE)
    metrics = json.loads((ARTIFACTS / "metrics.json").read_text(encoding="utf-8"))
    bundle = load_bundle()

    train_hashes = set(hash_pandas_object(train[columns], index=False))
    test_hashes = hash_pandas_object(test[columns], index=False)
    expected_unseen = (~test_hashes.isin(train_hashes)) & (~test_hashes.duplicated())
    assert np.array_equal(scored["unique_unseen"].to_numpy(), expected_unseen.to_numpy())
    assert int(expected_unseen.sum()) == metrics["evaluation_records"] == 52_644
    sample = scored.loc[scored["unique_unseen"]].sample(n=50, random_state=26)
    assert np.allclose(bundle.scores(sample), sample["anomaly_score"].to_numpy(), atol=1e-12)
    assert np.allclose(bundle.supervised.predict_proba(
        bundle.preprocessor.transform(sample[bundle.columns]))[:, 1],
        sample["supervised_probability"].to_numpy(), atol=1e-12)

    unseen = scored.loc[scored["unique_unseen"]]
    for key, scores, threshold in [
        ("main", unseen["anomaly_score"].to_numpy(), bundle.threshold(.02)),
        ("supervised", unseen["supervised_probability"].to_numpy(), bundle.supervised_threshold(.02)),
    ]:
        calculated = evaluate(unseen["label"].to_numpy(), scores, threshold)
        published = metrics if key == "main" else metrics["supervised"]
        for name, value in calculated.items():
            assert np.isclose(value, published[name]), (key, name, value, published[name])
    print("OK: test ayrımı, 50 model skoru ve iki modelin bütün ana metrikleri tutarlı.")


if __name__ == "__main__":
    main()
