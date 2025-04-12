# utils/audio_boost.py
from pydub import AudioSegment

TARGET_DBFS = -20.0  # Desired average loudness threshold
MIN_BOOST_THRESHOLD = -35.0  # Only boost files quieter than this


def boost_if_needed(audio_path):
    """
    Boosts the audio file if it's too quiet. Overwrites in place.
    """
    audio = AudioSegment.from_wav(audio_path)
    current_dbfs = audio.dBFS

    if current_dbfs < MIN_BOOST_THRESHOLD:
        gain = TARGET_DBFS - current_dbfs
        print(f"🔊 Boosting {audio_path.name} by {gain:.2f} dB")
        audio = audio.apply_gain(gain)
        audio.export(audio_path, format="wav")
    else:
        print(f"✅ {audio_path.name} is loud enough ({current_dbfs:.2f} dBFS). No boost needed.")
