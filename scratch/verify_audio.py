import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from faster_whisper import WhisperModel

audio_path = r"A:\processed_md\extracted_suspicious_audio.mp3"
model_size = "large-v3"
print("Loading model...")
model = WhisperModel(model_size, device="cuda", compute_type="float16")

print("Transcribing...")
segments, info = model.transcribe(audio_path, beam_size=5, language="zh", vad_filter=True)

print(f"Detected language '{info.language}' with probability {info.language_probability}")

out_txt = r"A:\processed_md\extracted_suspicious_audio_transcript.txt"
with open(out_txt, "w", encoding="utf-8") as f:
    for segment in segments:
        line = f"[{segment.start:.2f} -> {segment.end:.2f}] {segment.text}"
        f.write(line + "\n")
        
print("Transcription saved to " + out_txt)
