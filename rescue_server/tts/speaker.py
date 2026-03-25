import asyncio
import tempfile
import edge_tts

VOICE = "es-ES-AlvaroNeural"  # Hombre español natural
# Alternativas: "es-ES-ElviraNeural", "es-MX-JorgeNeural"

async def _text_to_audio_async(text: str, output_path: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)

def text_to_audio(text: str) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp.name
    tmp.close()
    asyncio.run(_text_to_audio_async(text, tmp_path))
    return tmp_path
