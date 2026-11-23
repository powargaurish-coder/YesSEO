import json, os, re
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

MODEL_ID = "ai4bharat/indic-parler-tts"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

print(f"Loading {MODEL_ID} on {DEVICE} ({DTYPE})")
model = ParlerTTSForConditionalGeneration.from_pretrained(
    MODEL_ID,
    torch_dtype=DTYPE,
).to(DEVICE)
model.eval()

prompt_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
desc_tokenizer = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)

VOICE = (
    "Vasudha speaks in a warm, calm, devotional and empathetic tone, "
    "slightly slow-paced for clarity, with careful Sanskrit pronunciation. "
    "The recording is clean, intimate, and has no background noise or music."
)

def slug(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_")

with open(ROOT / "mantras.json", "r", encoding="utf-8") as f:
    items = json.load(f)

desc = desc_tokenizer(VOICE, return_tensors="pt").to(DEVICE)

for item in items:
    text = item["text"]
    prompt = prompt_tokenizer(text, return_tensors="pt").to(DEVICE)
    with torch.inference_mode():
        generation = model.generate(
            input_ids=desc.input_ids,
            attention_mask=desc.attention_mask,
            prompt_input_ids=prompt.input_ids,
            prompt_attention_mask=prompt.attention_mask,
        )
    audio = generation.cpu().float().numpy().squeeze()
    peak = float(np.abs(audio).max()) if audio.size else 0.0
    if peak > 1.0:
        audio = audio / peak
    path = OUT / f'{item["id"]}_{slug(item["name"])}.wav'
    sf.write(path, audio, model.config.sampling_rate, subtype="PCM_16")
    print(f"Wrote {path} @ {model.config.sampling_rate} Hz")
