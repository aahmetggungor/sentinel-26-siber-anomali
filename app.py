"""SENTINEL 26: ağ akışı anomali tespiti ve kayıtlı alarm demosu."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import json
import time

import numpy as np
import pandas as pd
import streamlit as st

from alert_log import LOG_FILE, read_alerts, record_alerts
from engine import ARTIFACTS, MODEL_FILE, SCORED_FILE, evaluate, explain_outlier, load_bundle


st.set_page_config(page_title="SENTINEL 26 · Siber Anomali Merkezi", page_icon="🛡️", layout="wide")
public_demo = not st.context.url.startswith(("http://localhost", "http://127.0.0.1"))
st.markdown("""
<style>
.stApp{background:radial-gradient(circle at 82% -18%,#173b47 0,transparent 38%),#08131e;color:#eaf4f5}
.block-container{max-width:1450px;padding-top:1.2rem;padding-bottom:4rem}
[data-testid="stSidebar"]{background:#0c1d2a;border-right:1px solid #244654}
button[data-testid="stBaseButton-header"]{display:none}
[data-testid="stMetric"]{background:#112735;border:1px solid #275466;border-radius:15px;padding:16px}
[data-testid="stMetricLabel"]{color:#99b5c1}
.stTabs [data-baseweb="tab-list"]{gap:14px;border-bottom:1px solid #2c4b5a}
.stTabs [data-baseweb="tab"]{padding:12px 17px;border-radius:9px 9px 0 0}
.hero{background:linear-gradient(110deg,#103240,#11283b 58%,#122034);border:1px solid #30657a;
border-radius:20px;padding:30px 36px;margin-bottom:20px;box-shadow:0 16px 46px #0003}
.eyebrow{color:#77dfce;font-size:12px;font-weight:800;letter-spacing:.15em;text-transform:uppercase}
.hero h1{color:#f3fbfb;margin:10px 0 10px;font-size:clamp(29px,3.5vw,44px);line-height:1.12;font-weight:800}
.hero p{color:#b4ccd4;margin:0;max-width:920px;font-size:15px;line-height:1.6}
.tagline{display:flex;gap:8px;flex-wrap:wrap;margin-top:19px}
.tagline span{border:1px solid #3b6e79;color:#b8e8e4;background:#1a4550;padding:5px 11px;border-radius:99px;font-size:12px;font-weight:700}
.small-note{color:#9fb8c3;font-size:13px;line-height:1.6}
div[data-testid="stDownloadButton"] button{width:100%}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
 <div class="eyebrow">SENTINEL 26 / Savunma amaçlı ağ analizi</div>
 <h1>Anomaliyi yakala. Alarmı açıkla. Kayda geçir.</h1>
 <p>UNSW-NB15 ağ akışlarından eğitilen yerel bir anomali modeli. Test kayıtlarını akış gibi oynat,
 yeni anomalileri anında gör ve her alarmın sıra dışı alan ipuçlarını kayıt dosyasında incele.</p>
 <div class="tagline"><span>◉ Anomali skoru</span><span>◈ Anlık demo alarmı</span>
 <span>▤ JSONL kayıt</span><span>◇ Etiketli karşılaştırma</span></div>
</div>
""", unsafe_allow_html=True)
if public_demo:
    st.warning("Çevrimiçi demo: yüklenen CSV sunucuda işlenir. Gerçek ağ kayıtları veya gizli veriler yerine "
               "sentetik örnekler kullanın. Alarmlar yalnızca mevcut oturumda tutulur.")

if not MODEL_FILE.exists() or not SCORED_FILE.exists():
    st.error("Model çıktıları bulunamadı. Önce proje klasöründe `.venv\\Scripts\\python.exe train.py` çalıştırın.")
    st.stop()


@st.cache_resource
def get_bundle():
    return load_bundle()


@st.cache_data
def get_scored():
    return pd.read_parquet(SCORED_FILE)


@st.cache_data
def get_metrics():
    return json.loads((ARTIFACTS / "metrics.json").read_text(encoding="utf-8"))


bundle = get_bundle()
scored = get_scored()
base_metrics = get_metrics()

with st.sidebar:
    st.title("◈ SENTINEL 26")
    st.caption("Ağ anomalisi ve tehdit analizi")
    st.divider()
    target_fpr_percent = st.slider("Normal doğrulama verisinde hedef yanlış alarm", 1, 20, 2, 1,
                                   help="Eşik, yalnızca eğitimden ayrılmış normal doğrulama kayıtlarıyla belirlenir.")
    target_fpr = target_fpr_percent / 100
    threshold = bundle.threshold(target_fpr)
    st.caption(f"Anomali eşik skoru: {threshold:.3f}")
    st.divider()
    st.caption("Bu ekran gerçek ağ paketlerini dinlemez. Resmi test ayrımındaki kayıtları akış gibi oynatır.")


evaluation = scored.loc[scored["unique_unseen"]]
current = evaluate(evaluation["label"].to_numpy(), evaluation["anomaly_score"].to_numpy(), threshold)
supervised_threshold = bundle.supervised_threshold(target_fpr)
supervised_current = evaluate(evaluation["label"].to_numpy(),
                              evaluation["supervised_probability"].to_numpy(), supervised_threshold)
main_tab, replay_tab, lab_tab, data_tab = st.tabs(
    ["⌂ Komuta merkezi", "▶ Akış simülasyonu", "◇ Model laboratuvarı", "▤ Veri ve log"])

with main_tab:
    st.subheader("Test ayrımında genel görünüm")
    st.caption("Eşik normal doğrulama verisinden seçildi. Ana sonuçlar eğitimde görülmeyen, "
               "tekilleştirilmiş test kayıtlarından hesaplandı.")
    a, b, c, d = st.columns(4)
    a.metric("Tekil/görülmemiş test akışı", f"{len(evaluation):,}")
    b.metric("Alarm", f"{current['tp'] + current['fp']:,}")
    c.metric("Saldırı yakalama", f"%{current['recall']*100:.1f}")
    d.metric("Yanlış alarm / 1000 normal", f"{current['alerts_per_1000_normal']:.1f}")
    st.divider()
    left, right = st.columns([1.1, .9], gap="large")
    with left:
        st.markdown("**Alarm karar tablosu**")
        matrix = pd.DataFrame({"Gerçek normal": [current["tn"], current["fp"]],
                               "Gerçek saldırı": [current["fn"], current["tp"]]},
                              index=["Normal kararı", "Alarm kararı"])
        st.dataframe(matrix, width="stretch")
        st.info("Hedef yanlış alarm oranı ile testte ölçülen oran aynı olmak zorunda değildir. "
                "Veri dağılımı değiştiğinde testteki yanlış alarmlar artabilir.")
    with right:
        st.markdown("**Saldırı türüne göre yakalama**")
        attacks = evaluation.loc[evaluation["label"] == 1].copy()
        attacks["alarm"] = attacks["anomaly_score"] >= threshold
        by_type = attacks.groupby("attack_cat").agg(kayıt=("label", "size"), yakalama=("alarm", "mean"))
        by_type["yakalama"] = (by_type["yakalama"] * 100).round(1)
        st.bar_chart(by_type["yakalama"], horizontal=True)
    st.warning("Bu veri kümesinde saldırı oranı yüksektir. Ölçülen precision değeri gerçek bir kurum ağındaki "
               "alarm isabetini doğrudan temsil etmez; tezde farklı saldırı prevalansları ayrıca incelenecek.")
    st.caption(f"Yayımlanmış test dosyası: {len(scored):,} satır · tekil ve eğitimde görülmemiş değerlendirme: "
               f"{len(evaluation):,} satır.")


@st.cache_data
def replay_sample():
    # Karışık akış için sabit örnek; eğitimde görülmüş/tekrarlı test satırları alınmaz.
    unseen = get_scored().loc[lambda frame: frame["unique_unseen"]]
    return unseen.sample(n=min(1200, len(unseen)), random_state=26).reset_index(drop=True)


def make_alert(row: pd.Series, position: int, score: float, threshold_value: float,
               run_id: str, mode: str) -> dict:
    validation = (bundle.normal_validation_scores if mode == "Etiketsiz anomali"
                  else bundle.supervised_normal_validation_scores)
    severity = "Kritik" if score >= np.quantile(validation, .995) else "Yüksek"
    return {
        "run_id": run_id, "event_index": position, "source_row_id": int(row["id"]),
        "model": mode,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "anomaly_score": round(score, 5), "threshold": round(threshold_value, 5),
        "severity": severity, "hints": explain_outlier(row, bundle.reference),
        "reference_label": int(row["label"]), "reference_attack_type": str(row["attack_cat"]),
    }


@st.fragment(run_every="1s")
def stream_panel(threshold_value: float, speed: int, mode: str):
    sample = replay_sample()
    if st.session_state.get("running", False):
        start = st.session_state["position"]
        end = min(start + speed, len(sample))
        if start < end:
            batch = sample.iloc[start:end]
            started = time.perf_counter()
            live_scores = (bundle.scores(batch) if mode == "Etiketsiz anomali" else
                           bundle.supervised.predict_proba(
                               bundle.preprocessor.transform(batch[bundle.columns]))[:, 1])
            st.session_state["last_latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
            new_alerts = [make_alert(row, start + offset, float(score), threshold_value,
                                     st.session_state["run_id"], mode)
                          for offset, (score, (_, row)) in enumerate(zip(live_scores, batch.iterrows()))
                          if score >= threshold_value]
            if public_demo:
                for event in new_alerts:
                    event.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
                st.session_state.setdefault("demo_alerts", []).extend(new_alerts)
            else:
                record_alerts(new_alerts)
            st.session_state["position"] = end
            st.session_state["alarm_count"] += len(new_alerts)
            recent = st.session_state.get("score_history", [])
            recent.extend({"Skor": float(score), "Eşik": threshold_value} for score in live_scores)
            st.session_state["score_history"] = recent[-160:]
            if new_alerts:
                st.toast(f"{len(new_alerts)} yeni alarm · {new_alerts[-1]['severity']}", icon="🚨")
        if end >= len(sample):
            st.session_state["running"] = False

    processed = st.session_state.get("position", 0)
    a, b, c, d = st.columns(4)
    a.metric("İşlenen akış", f"{processed:,} / {len(sample):,}")
    b.metric("Bu oturumdaki alarm", st.session_state.get("alarm_count", 0))
    c.metric("Durum", "AKIYOR" if st.session_state.get("running", False) else "BEKLEMEDE")
    d.metric("Son parti çıkarımı", f"{st.session_state.get('last_latency_ms', 0):.1f} ms")
    st.progress(processed / len(sample), text=f"Test akışı oynatma · %{processed / len(sample) * 100:.1f}")
    if st.session_state.get("score_history"):
        st.line_chart(pd.DataFrame(st.session_state["score_history"]), height=225)
    events = (list(reversed(st.session_state.get("demo_alerts", [])[-30:])) if public_demo else
              read_alerts(st.session_state.get("run_id"), limit=30))
    if events:
        table = pd.DataFrame([{
            "Zaman (UTC)": event["timestamp_utc"], "Akış": event["source_row_id"],
            "Skor": event["anomaly_score"], "Seviye": event["severity"],
            "Aykırılık ipuçları": " · ".join(event["hints"]),
            "Gerçek etiket (test)": event["reference_attack_type"],
        } for event in events])
        st.dataframe(table, width="stretch", hide_index=True)
    else:
        st.info("Akışı başlatınca tespit edilen anomaliler burada ve yerel JSONL logunda görünecek.")


with replay_tab:
    st.subheader("Test kayıtlarını akış gibi oynat")
    st.caption("Her saniye yeni kayıtlar modelden geçirilir. Bu bir veri kümesi simülasyonudur; canlı ağ dinleme değildir.")
    mode = st.radio("Alarm kaynağı", ["Etiketsiz anomali", "Etiketli referans"], horizontal=True,
                    help="Etiketsiz model yalnızca normal kayıtlarla; referans model saldırı etiketleriyle eğitildi.")
    if "run_id" not in st.session_state:
        st.session_state.update(run_id=uuid4().hex[:10], position=0, running=False,
                                alarm_count=0, score_history=[], replay_mode=mode)
    if st.session_state.get("replay_mode") != mode:
        st.session_state.update(run_id=uuid4().hex[:10], position=0, running=False,
                                alarm_count=0, score_history=[], replay_mode=mode)
    speed = st.select_slider("Akış hızı (kayıt/sn)", options=[1, 5, 10, 20, 50], value=10)
    x, y, z = st.columns([1, 1, 3])
    if x.button("▶ Başlat", type="primary", width="stretch"):
        if st.session_state["position"] >= len(replay_sample()):
            st.session_state.update(run_id=uuid4().hex[:10], position=0, alarm_count=0,
                                    score_history=[])
        st.session_state["running"] = True
        st.rerun()
    if y.button("Ⅱ Durdur", width="stretch"):
        st.session_state["running"] = False
        st.rerun()
    if z.button("↺ Yeni oturum", width="stretch"):
        st.session_state.update(run_id=uuid4().hex[:10], position=0, running=False,
                                alarm_count=0, score_history=[])
        st.rerun()
    replay_threshold = threshold if mode == "Etiketsiz anomali" else supervised_threshold
    stream_panel(replay_threshold, speed, mode)
    st.caption("Gerçek saldırı türü sütunu yalnızca test veri kümesinin etiketiyle karşılaştırma içindir; "
               "anomali modeli bu türü tahmin etmez.")

with lab_tab:
    st.subheader("İki yaklaşımı aynı test verisinde karşılaştır")
    st.caption("Isolation Forest yalnızca normal eğitim kayıtlarını gördü. Etiketli Random Forest referansı "
               "normal ve saldırı etiketleriyle eğitildi; amaç ikisinin farkını görünür kılmak.")
    comparison = pd.DataFrame([
        {"Model": "Etiketsiz anomali · Isolation Forest", "Precision": current["precision"],
         "Recall": current["recall"], "F1": current["f1"], "PR-AUC": current["average_precision"],
         "Test FPR": current["false_positive_rate"]},
        {"Model": "Etiketli referans · Random Forest", "Precision": supervised_current["precision"],
         "Recall": supervised_current["recall"], "F1": supervised_current["f1"],
         "PR-AUC": supervised_current["average_precision"],
         "Test FPR": supervised_current["false_positive_rate"]},
    ])
    st.dataframe(comparison.style.format({column: "{:.3f}" for column in comparison.columns if column != "Model"}),
                 width="stretch", hide_index=True)
    st.markdown("**Eşik değişirse ne olur?**")
    thresholds = [.01, .02, .05, .1, .15, .2]
    sweep = pd.DataFrame([{"Hedef yanlış alarm (%)": int(fpr * 100), **evaluate(
        evaluation["label"].to_numpy(), evaluation["anomaly_score"].to_numpy(), bundle.threshold(fpr))}
        for fpr in thresholds])
    st.line_chart(sweep.set_index("Hedef yanlış alarm (%)")[["precision", "recall", "f1"]], height=275)
    st.caption("Eşik için saldırı etiketleri kullanılmaz. Grafikteki sonuçlar test etiketleriyle sonradan ölçülür.")
    st.markdown("**Saldırı sıklığı değişirse alarm isabeti nasıl değişir?**")
    st.caption("Bu bir varsayım hesabıdır: testte ölçülen saldırı yakalama ve yanlış alarm oranları aynı "
               "kalırsa, farklı ağlardaki beklenen precision aşağıdaki gibi olur.")
    prevalence_rows = []
    for prevalence in [.001, .01, .05, .10, .25]:
        row = {"Varsayımsal saldırı oranı": f"%{prevalence * 100:g}"}
        for name, measured in [("Etiketsiz model", current), ("Etiketli referans", supervised_current)]:
            true_alarm = prevalence * measured["recall"]
            false_alarm = (1 - prevalence) * measured["false_positive_rate"]
            row[name] = true_alarm / (true_alarm + false_alarm) if true_alarm + false_alarm else 0.0
        prevalence_rows.append(row)
    prevalence_frame = pd.DataFrame(prevalence_rows).set_index("Varsayımsal saldırı oranı")
    st.dataframe(prevalence_frame.style.format("{:.1%}"), width="stretch")
    st.caption("Bu tablo yeni bir saha ölçümü değildir; başka ağda yakalama/FPR değişirse tahmin geçersiz olur.")
    with st.expander("Eğitim düzeni ve veri sızıntısı kontrolleri"):
        st.markdown(f"""
- Yayınlanmış eğitim/test ayrımı korunur; test içinde eğitimle aynı özelliklere sahip veya kendi içinde tekrarlı satırlar ana ölçümden çıkarılır: **{base_metrics['train_normal']:,} normal eğitim**, **{base_metrics['validation_normal']:,} normal eşik doğrulama**, **{len(evaluation):,} tekil/görülmemiş test**.
- `id`, `label`, `attack_cat` model girdilerinden çıkarılır.
- Eksik veri doldurma, log dönüşümü, ölçekleme ve kategorik kodlama yalnızca eğitim parçasında öğrenilir.
- Test verisinde eşik seçilmez; hedef oran normal doğrulama skorlarının yüzdeliğinden gelir.
- Aykırılık ipuçları normal veri yüzdelikleriyle hazırlanır; Isolation Forest için nedensel özellik açıklaması sayılmaz.
- Bu sonuçlar UNSW-NB15'in dağılımı ve ayrımına bağlıdır; başka ağlarda ayrıca ölçüm gerekir.
""")
    audit = base_metrics["data_audit"]
    st.info(f"Veri denetimi: eğitimde {audit['train_duplicate_rows']:,} tekrar, testte "
            f"{audit['test_duplicate_rows']:,} tekrar, eğitimde de görülen {audit['test_rows_seen_in_train']:,} "
            f"test satırı ve çelişkili etiket taşıyan {audit['conflicting_train_feature_groups']} özellik grubu bulundu.")

with data_tab:
    st.subheader("Veri, log ve kendi kayıtların")
    a, b, c, d = st.columns(4)
    a.metric("Eğitim satırı", "175.341")
    b.metric("Test satırı", "82.332")
    c.metric("Tekil/görülmemiş test", f"{len(evaluation):,}")
    d.metric("Model girdisi", len(bundle.columns))
    st.caption("Kaynak: UNSW-NB15 yayımlanmış eğitim/test CSV ayrımı. Tam paket akışı (PCAP) değil, "
               "önceden çıkarılmış ağ akışı özellikleri kullanılır.")
    st.markdown("**Bu oturumun alarm logu**" if public_demo else "**Yerel alarm logu**")
    if public_demo:
        st.caption("Bu oturumun alarm kayıtları sunucuya dosya olarak yazılmaz.")
        demo_alerts = st.session_state.get("demo_alerts", [])
        if demo_alerts:
            payload = "\n".join(json.dumps(event, ensure_ascii=False) for event in demo_alerts) + "\n"
            st.download_button("Bu oturumun JSONL alarm logunu indir", payload.encode("utf-8"),
                               file_name="sentinel26_alarms.jsonl", mime="application/x-ndjson")
    else:
        st.code(str(LOG_FILE), language=None)
    if not public_demo and LOG_FILE.is_file():
        st.download_button("JSONL alarm logunu indir", LOG_FILE.read_bytes(),
                           file_name="sentinel26_alarms.jsonl", mime="application/x-ndjson")
    st.divider()
    st.markdown("**UNSW-NB15 şemasında kendi CSV dosyanı puanla**")
    upload_mode = st.selectbox("Puanlama modeli", ["Etiketsiz anomali", "Etiketli referans"])
    upload = st.file_uploader("CSV seç (en fazla 10 MB)", type="csv", max_upload_size=10)
    if upload:
        try:
            frame = pd.read_csv(BytesIO(upload.getvalue()))
            missing = set(bundle.columns) - set(frame.columns)
            if missing:
                st.error("Eksik model alanları: " + ", ".join(sorted(missing)[:12]))
            elif len(frame) > 20_000:
                st.error("Demo sınırı 20.000 satırdır.")
            else:
                upload_scores = (bundle.scores(frame) if upload_mode == "Etiketsiz anomali" else
                                 bundle.supervised.predict_proba(
                                     bundle.preprocessor.transform(frame[bundle.columns]))[:, 1])
                upload_threshold = threshold if upload_mode == "Etiketsiz anomali" else supervised_threshold
                output = frame.copy()
                output["model_score"] = upload_scores
                output["alarm"] = upload_scores >= upload_threshold
                st.success(f"{len(frame):,} akış puanlandı · {int(output['alarm'].sum()):,} alarm")
                st.dataframe(output.sort_values("model_score", ascending=False).head(100),
                             hide_index=True, width="stretch")
                st.download_button("Puanlanmış CSV indir", output.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="sentinel26_puanlar.csv", mime="text/csv")
        except (ValueError, pd.errors.ParserError) as error:
            st.error(f"CSV okunamadı: {error}")
