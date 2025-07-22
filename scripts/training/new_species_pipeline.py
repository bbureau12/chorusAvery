# import datetime
# import os
# import random
# import shutil
# import sqlite3
# import sys
# from pydub import AudioSegment
# import numpy as np
# import matplotlib
# import json
# from tqdm import tqdm

# matplotlib.use('Agg')

# # === Import project utilities
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# sys.path.insert(0, project_root)
# from utils.generate_spectogram import generate_mel_spectrogram, get_spectrogram_settings
# from utils.model_spec_writer import SpecWriter

# TARGET_DURATION_MS = 2500  # Standard duration of 2.5s

# def search_species(cursor, query):
#     cursor.execute("SELECT id, name FROM Species")
#     return [(id_, name) for id_, name in cursor.fetchall() if query.lower() in name.lower()]

# def standardize_duration(audio):
#     duration = len(audio)
#     if duration >= TARGET_DURATION_MS:
#         return audio[:TARGET_DURATION_MS]
#     pad_ms = TARGET_DURATION_MS - duration
#     silence = AudioSegment.silent(duration=pad_ms)
#     return audio + silence

# def polarize_volume(audio, boost_db=12):
#     if audio.max_dBFS < -20:
#         boosted = audio + min(boost_db, 15)
#     else:
#         boosted = None
#     if audio.max_dBFS > -35:
#         reduced = audio - min(boost_db, 15)
#     else:
#         print(f"\U0001F6AB Skipping reduction: clip too quiet (peak {audio.max_dBFS:.1f} dBFS)")
#         reduced = None
#     return boosted, reduced

# def overlay_noise(clip, noise, target_dbfs=None):
#     if target_dbfs is not None and noise.dBFS > target_dbfs:
#         diff_db = noise.dBFS - target_dbfs + 5
#         noise = noise - diff_db
#     return clip.overlay(noise)

# def split_data(clips, train_ratio=0.7, val_ratio=0.2):
#     random.shuffle(clips)
#     total = len(clips)
#     train_end = int(train_ratio * total)
#     val_end = train_end + int(val_ratio * total)
#     return clips[:train_end], clips[train_end:val_end], clips[val_end:]

# def main():
#     db_path = "./db/chorusAvery.db"
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()

#     species_name = input("\U0001F50E Species name: ").strip()
#     matches = search_species(cursor, species_name)
#     if not matches:
#         print("❌ No matching species found.")
#         return
#     if len(matches) > 1:
#         for idx, (_, name) in enumerate(matches):
#             print(f"{idx+1}. {name}")
#         sel = int(input("Choose species number: ")) - 1
#         species_id, species_name = matches[sel]
#     else:
#         species_id, species_name = matches[0]
#     print(f"✅ Selected species: {species_name} (ID {species_id})")

#     slug = species_name.lower().replace(" ", "_")
#     base_dir = f"./recordings/model/{slug}"
#     train_dir = os.path.join(base_dir, "train", str(species_id))
#     val_dir = os.path.join(base_dir, "validation", str(species_id))
#     test_dir = os.path.join(base_dir, "test", str(species_id))
#     for d in [train_dir, val_dir, test_dir]:
#         os.makedirs(d, exist_ok=True)

#     # New: Smart sampling of mixed + solo
#     cursor.execute("""
#         SELECT Clips.clip_path, COUNT(ClipAnnotations.species_id) as species_count
#         FROM Clips
#         JOIN ClipAnnotations ON Clips.id = ClipAnnotations.clip_id
#         GROUP BY Clips.id
#         HAVING SUM(ClipAnnotations.species_id = ?) > 0
#     """, (species_id,))
#     all_results = cursor.fetchall()
#     random.shuffle(all_results) 
#     solo_clips = [path for path, count in all_results if count == 1]
#     mixed_clips = [path for path, count in all_results if count > 1]
#     n_mixed = min(len(mixed_clips), len(solo_clips) // 4)
#     selected_mixed = random.sample(mixed_clips, n_mixed)
#     clips = solo_clips + selected_mixed
#     print(f"\U0001F3A7 Using {len(solo_clips)} solo and {n_mixed} mixed clips. Total: {len(clips)}")

#     noises = []
#     for f in os.listdir("./recordings/augmentation_noise"):
#         if f.endswith('.wav'):
#             noises.append(AudioSegment.from_file(os.path.join("./recordings/augmentation_noise", f)))
#     print(f"\U0001F3BC Loaded {len(noises)} noise files for augmentation.")

#     processed_clips = []
#     for clip_file in tqdm(clips, desc="\U0001F3A8 Processing clips"):
#         clip_path = os.path.join("./recordings/training_data", clip_file)
#         clip = AudioSegment.from_file(clip_path).set_channels(1).set_frame_rate(16000)
#         clip = standardize_duration(clip)
#         clip_basename = os.path.splitext(os.path.basename(clip_file))[0]

#         out_wav = f"{clip_basename}.wav"
#         out_path = os.path.join(base_dir, out_wav)
#         clip.export(out_path, format="wav")
#         generate_mel_spectrogram(clip, out_path.replace('.wav', '.png'))
#         processed_clips.append(out_path)

#         boosted, reduced = polarize_volume(clip, boost_db=10)
#         if boosted:
#             boosted_out = f"{clip_basename}_boosted.wav"
#             boosted_path = os.path.join(base_dir, boosted_out)
#             boosted.export(boosted_path, format="wav")
#             generate_mel_spectrogram(boosted, boosted_path.replace('.wav', '.png'))
#             processed_clips.append(boosted_path)
#         if reduced:
#             reduced_out = f"{clip_basename}_reduced.wav"
#             reduced_path = os.path.join(base_dir, reduced_out)
#             reduced.export(reduced_path, format="wav")
#             generate_mel_spectrogram(reduced, reduced_path.replace('.wav', '.png'))
#             processed_clips.append(reduced_path)

#         for i in range(3):
#             noise = random.choice(noises)
#             augmented = overlay_noise(clip, noise, clip.dBFS)
#             aug_out = f"{clip_basename}_aug{i}.wav"
#             aug_path = os.path.join(base_dir, aug_out)
#             augmented.export(aug_path, format="wav")
#             generate_mel_spectrogram(augmented, aug_path.replace('.wav', '.png'))
#             processed_clips.append(aug_path)

#     train, val, test = split_data(processed_clips, train_ratio=0.7, val_ratio=0.2)
#     for dataset, folder in [(train, train_dir), (val, val_dir), (test, test_dir)]:
#         for f in dataset:
#             dest_wav = os.path.join(folder, os.path.basename(f))
#             shutil.move(f, dest_wav)
#             dest_png = dest_wav.replace('.wav', '.png')
#             shutil.move(f.replace('.wav', '.png'), dest_png)
#             os.remove(dest_wav)

#     print(f"✅ Positives split: {len(train)} train, {len(val)} validation, {len(test)} test.")
#     generate_negatives(cursor, base_dir, len(train), len(val), len(test))
#     conn.close()

#     spec_writer = SpecWriter(
#         clip_length_ms=TARGET_DURATION_MS,
#         spectrogram_settings=get_spectrogram_settings(),
#         audio_settings=SpecWriter.default_audio_settings(),
#         augmentations={"boost_db": 10, "noise_overlays": 3}
#     )
#     spec_writer.save(base_dir)
#     print("\n🏍️ Full dataset preparation complete!")

# def generate_negatives(cursor, base_dir, train_count, val_count, test_count):
#     neg_train_dir = os.path.join(base_dir, "train", "0")
#     neg_val_dir = os.path.join(base_dir, "validation", "0")
#     neg_test_dir = os.path.join(base_dir, "test", "0")
#     for d in [neg_train_dir, neg_val_dir, neg_test_dir]:
#         os.makedirs(d, exist_ok=True)

#     neg_clips = []
#     cursor.execute("""
#         SELECT clip_path FROM Clips
#         WHERE id NOT IN (SELECT clip_id FROM ClipAnnotations)
#     """)
#     neg_clips += [row[0] for row in cursor.fetchall()]

#     cursor.execute("SELECT id FROM Species")
#     all_species = [row[0] for row in cursor.fetchall()]
#     for sid in all_species:
#         cursor.execute("""
#             SELECT clip_path FROM Clips
#             JOIN ClipAnnotations ON Clips.id=ClipAnnotations.clip_id
#             WHERE ClipAnnotations.species_id!=?
#         """, (sid,))
#         neg_clips += [row[0] for row in cursor.fetchall()]

#     random.shuffle(neg_clips)

#     for split_name, folder, num_samples in [
#         ("train", neg_train_dir, train_count),
#         ("validation", neg_val_dir, val_count),
#         ("test", neg_test_dir, test_count)
#     ]:
#         for i in range(num_samples):
#             neg_clip = neg_clips.pop() if neg_clips else None
#             if not neg_clip:
#                 print(f"⚠️ Ran out of negatives for {split_name}.")
#                 break
#             clip_full_path = os.path.join("./recordings/training_data", neg_clip)
#             if not os.path.exists(clip_full_path):
#                 print(f"⚠️ Missing negative clip: {clip_full_path}")
#                 continue
#             clip = AudioSegment.from_file(clip_full_path).set_channels(1).set_frame_rate(16000)
#             clip = standardize_duration(clip)
#             out_name = f"neg_{split_name}_{i:04d}.wav"
#             out_path = os.path.join(folder, out_name)
#             clip.export(out_path, format="wav")
#             generate_mel_spectrogram(clip, out_path.replace('.wav', '.png'))
#             os.remove(out_path)

# if __name__ == "__main__":
#     main()
