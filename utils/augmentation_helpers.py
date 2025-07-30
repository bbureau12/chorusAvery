import random
from pydub import AudioSegment

def pad_audio(audio, pad_ms=500):
    silence_segment = AudioSegment.silent(duration=pad_ms)
    return random.choice([silence_segment + audio, audio + silence_segment])

def overlay_noise(clip, noise, target_dbfs=None):
    if target_dbfs is not None and noise.dBFS > target_dbfs:
        diff_db = noise.dBFS - target_dbfs + 5  # keep noise slightly under
        noise = noise - diff_db
    return clip.overlay(noise)

def polarize_volume(audio, target_dbfs, factor=1.3):
    diff = target_dbfs - audio.dBFS
    adjustment = diff * factor
    # Optional: limit extremes to avoid distortion/silence
    adjustment = max(min(adjustment, 20), -20)
    if abs(adjustment) < 1.0:
        return None
    return audio + adjustment

def split_data(clips, train_ratio=0.7, val_ratio=0.2):
    random.shuffle(clips)
    total = len(clips)
    train_end = int(train_ratio * total)
    val_end = train_end + int(val_ratio * total)
    return clips[:train_end], clips[train_end:val_end], clips[val_end:]