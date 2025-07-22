import json
import os
def write_trainer_specs(IMAGE_SIZE, BATCH_SIZE, EPOCHS, history, class_names, best_epoch, best_val, results_dir, species_name):
    results_summary = {
        'species': 'american_toad',
        'image_size': IMAGE_SIZE,
        'batch_size': BATCH_SIZE,
        'epochs': EPOCHS,
        'final_train_accuracy': float(history.history['accuracy'][-1]),
        'final_val_accuracy': float(history.history['val_accuracy'][-1]),
        'class_names': class_names,
        'best_epoch': int(best_epoch + 1),
        'best_val_loss': float(best_val),
    }

    with open(os.path.join(results_dir, 'results_summary.json'), 'w') as f:
        json.dump(results_summary, f, indent=4)