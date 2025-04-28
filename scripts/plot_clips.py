import matplotlib.pyplot as plt
import numpy as np
from pydub import AudioSegment
import os

def plot_clips(wav_path, clip_times):
    sound = AudioSegment.from_wav(wav_path)
    samples = np.array(sound.get_array_of_samples())
    duration = len(samples) / sound.frame_rate
    times = np.linspace(0, duration, num=len(samples))

    plt.figure(figsize=(15, 5))
    plt.plot(times, samples, alpha=0.6)
    plt.title(f"Waveform and Clip Locations - {os.path.basename(wav_path)}")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Amplitude")

    # Draw rectangles or vertical bars for each clip
    for i, (start_ms, end_ms) in enumerate(clip_times):
        start_sec = start_ms / 1000.0
        end_sec = end_ms / 1000.0
        plt.axvspan(start_sec, end_sec, color='green', alpha=0.3)
        plt.text((start_sec + end_sec) / 2, max(samples) * 0.8, str(i), 
                 horizontalalignment='center', color='black', fontsize=8)

    plt.tight_layout()
    plt.show()

