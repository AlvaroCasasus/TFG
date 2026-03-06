import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from config import GEMMA_MODEL_NAME, GEMMA_DTYPE, GEMMA_MAX_CONTEXT, GEMMA_MAX_NEW_TOKENS, GEMMA_TEMPERATURE

_tokenizer = None
_model = None

def get_gemma():
    global _tokenizer, _model
    if _model is None:
        print(f"Cargando {GEMMA_MODEL_NAME}...")
        _tokenizer = AutoTokenizer.from_pretrained(GEMMA_MODEL_NAME, trust_remote_code=True)
        _model = AutoModelForCausalLM.from_pretrained(
            GEMMA_MODEL_NAME,
            device_map="auto",
            torch_dtype=GEMMA_DTYPE,   # ← 'dtype' está deprecado, usar 'torch_dtype'
            trust_remote_code=True
        )
        print("Gemma cargado.")
    return _tokenizer, _model

def generate(prompt: str) -> str:
    tokenizer, model = get_gemma()
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    prompt_len = inputs["input_ids"].shape[1]
    max_new = min(GEMMA_MAX_NEW_TOKENS, GEMMA_MAX_CONTEXT - prompt_len)

    if max_new <= 0:
        raise ValueError(f"Prompt demasiado largo: {prompt_len} tokens.")

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new,
            temperature=GEMMA_TEMPERATURE,
            do_sample=True  # consistente con temperature > 1.0
        )

    # ✅ Cortamos por índice de tokens, no por longitud de string
    new_tokens = output[0][prompt_len:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
