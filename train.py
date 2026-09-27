"""python train.py - resmi UNSW-NB15 ayrımıyla modeli eğit ve çıktıları kaydet."""

from engine import save_artifacts, train_model


if __name__ == "__main__":
    bundle, scored, metrics = train_model()
    save_artifacts(bundle, scored, metrics)
    print(f"Normal eğitim: {metrics['train_normal']:,} | Doğrulama: {metrics['validation_normal']:,}")
    print(f"Test: {metrics['test_records']:,} | Eşsiz/görülmemiş: {metrics['evaluation_records']:,} | "
          f"Eğitim: {metrics['training_seconds']} sn | Test skoru: {metrics['inference_seconds']} sn")
    print(f"Hedef FPR %2: precision={metrics['precision']:.3f}, recall={metrics['recall']:.3f}, "
          f"F1={metrics['f1']:.3f}, test FPR={metrics['false_positive_rate']:.3f}")
    print(f"Model: {bundle.model.__class__.__name__} | çıktılar: artifacts/")
    print(f"Etiketli referans: precision={metrics['supervised']['precision']:.3f}, "
          f"recall={metrics['supervised']['recall']:.3f}, F1={metrics['supervised']['f1']:.3f}")
