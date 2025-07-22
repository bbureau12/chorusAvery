
from mixed_species_evaluator import MixedSpeciesEvaluator

def main():
    # 🔍 Let user select model + species info from results_summary.json
    model_slug, species_name, species_id = MixedSpeciesEvaluator.select_model_slug_from_results()

    # 📂 Set up evaluator
    evaluator = MixedSpeciesEvaluator(
        db_path="./db/chorusAvery.db",
        results_root="./models/results",
        model_slug=model_slug,
        species_name=species_name
    )
    evaluator.species_id = species_id  # Override internal lookup if necessary

    # 🧠 Load model
    evaluator.load_model()

    # 🎧 Get clips
    mixed_clips, solo_clips = evaluator.get_clip_paths()

    # 🎨 Generate spectrograms
    mixed_imgs = evaluator.create_spectrograms(mixed_clips, f"./temp/{model_slug}_mixed")
    solo_imgs = evaluator.create_spectrograms(solo_clips, f"./temp/{model_slug}_solo")

    # 🤖 Inference
    y_true_mixed, y_pred_mixed, conf_mixed = evaluator.infer_clipset(mixed_imgs, label_index=1)
    y_true_solo, y_pred_solo, conf_solo = evaluator.infer_clipset(solo_imgs, label_index=1)

    # 📊 Confusion matrices and outlier logging
    label_names = ["Negative", "Species"]
    evaluator.plot_confusion(y_true_mixed, y_pred_mixed, label_names,
                             "Mixed Confusion", f"./results/{model_slug}_mixed_cm.png")
    evaluator.plot_confusion(y_true_solo, y_pred_solo, label_names,
                             "Solo Confusion", f"./results/{model_slug}_solo_cm.png")

    evaluator.log_outliers(conf_mixed, label_index=1, class_names=label_names,
                           out_path=f"./results/{model_slug}_mixed_outliers.txt")

    print("✅ Evaluation complete.")

if __name__ == "__main__":
    main()
