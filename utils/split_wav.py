from boost_if_needed import boost_if_needed
from pathlib import Path
from pydub import AudioSegment
INPUT_DIR = Path(__file__).resolve().parent.parent / "recordings" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "db"
CHUNKS_DIR = INPUT_DIR / "chunks"
CHUNK_DURATION_MS = 60 * 1000  # 1 minute
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
def split_wav(file_path):
    print(f"🔪 Splitting: {file_path.name}")
    audio = AudioSegment.from_wav(file_path)
    chunks = []
    for i, start in enumerate(range(0, len(audio), CHUNK_DURATION_MS)):
        chunk = audio[start:start + CHUNK_DURATION_MS]
        chunk_name = f"{file_path.stem}_chunk{i:03d}.wav"
        chunk_path = CHUNKS_DIR / chunk_name
        chunk.export(chunk_path, format="wav")

        # 🧼 Prepare the chunk for BirdNET
        prepare_chunk_for_birdnet(chunk_path)

        chunks.append((chunk_path, i))
    print(f"🧩 Created {len(chunks)} chunks.\n")
    return chunks

def prepare_chunk_for_birdnet(input_path: Path):
    audio = AudioSegment.from_wav(input_path)
    audio = audio.set_channels(1)        # Mono
    audio = audio.set_sample_width(2)    # 16-bit
    audio = audio.set_frame_rate(32000)  # 32kHz
    audio = audio.normalize()            # Normalize volume
    audio.export(input_path, format="wav")  # Overwrite original
    boost_if_needed(input_path)  # 🔊 Conditionally boost volume