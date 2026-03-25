import torch

WHISPER_MODEL_NAME = "turbo"
WHISPER_DEVICE = "cuda"

GEMMA_MODEL_NAME = "google/gemma-3-4b-it"
GEMMA_DTYPE = torch.bfloat16
GEMMA_MAX_CONTEXT = 8192
GEMMA_MAX_NEW_TOKENS = 256
GEMMA_TEMPERATURE = 0.1   # >0 con do_sample=True, o 1.0 con do_sample=False

LOG_FILE = "logs_sos.jsonl"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
AUDIO_MAX_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_AUDIO_EXTENSIONS = {".ogg", ".wav", ".mp3", ".flac"}

# Robot
ROBOT_IP = "10.27.41.52"   # cambiarlo a ip robot
ROBOT_PORT = 8888
ROBOT_AUDIO_ENDPOINT = "/robot/audio/play"
