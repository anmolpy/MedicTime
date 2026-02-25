import os
import numpy as np
import chromadb
import whisper
import sounddevice as sd
from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient
import pygame
import io
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── 1. Connect to your ChromaDB ──────────────────────────────
client = chromadb.PersistentClient(path="./medical_rag_store_v2")
collections = client.list_collections()
print("Collections found:", [c.name for c in collections])

collection = client.get_collection(collections[0].name)
print(f"Documents loaded: {collection.count()}")

# ── 2. Load embedding model ───────────────────────────────────
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# ── 3. Connect to HuggingFace Inference API ───────────────────
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN not set. Please add it to your .env file.")

hf_client = InferenceClient(
    model="meta-llama/Meta-Llama-3-8B-Instruct",
    token=HF_TOKEN
)

# ── 4. Connect to ElevenLabs API ──────────────────────────────
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

if not ELEVEN_API_KEY:
    raise ValueError("ELEVEN_API_KEY not set. Please add it to your .env file.")

eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)
pygame.mixer.init()

def speak(text: str):
    """Converts text to speech and plays it through speakers"""
    print(f"🔊 Speaking response...")
    
    audio_stream = eleven_client.text_to_speech.convert(
        voice_id="21m00Tcm4TlvDq8ikWAM",  # "Rachel" — professional, calm voice
        text=text,
        model_id="eleven_turbo_v2",        # fastest model, good for real-time
        voice_settings=VoiceSettings(
            stability=0.5,          # 0-1, higher = more consistent tone
            similarity_boost=0.75,  # 0-1, higher = closer to original voice
            style=0.0,
            use_speaker_boost=True
        )
    )
    
    # Load and play audio
    audio_bytes = b"".join(audio_stream)
    pygame.mixer.music.load(io.BytesIO(audio_bytes), "mp3")
    pygame.mixer.music.play()
    
    # Wait for playback to finish before recording again
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)

# ── 4. Load Whisper model ─────────────────────────────────────
# Options: "tiny", "base", "small" — "base" recommended
print("Loading Whisper model...")
whisper_model = whisper.load_model("base")
print("✅ Whisper ready")

# ── 5. RAG retrieval function ─────────────────────────────────
def get_context(patient_message: str, n=3) -> str:
    query_vector = embedder.encode(patient_message).tolist()
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=n
    )
    return "\n\n".join(results['documents'][0])

# ── 6. LLM response function ──────────────────────────────────
def receptionist_response(patient_message: str) -> str:
    context = get_context(patient_message)

    response = hf_client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": f"""You are a professional medical receptionist voice agent 
for a healthcare clinic. You help patients with appointments, scheduling, 
billing, and clinic policies. Be empathetic, clear, and concise since 
this is a voice call.

Use these similar past conversations as a reference:
{context}"""
            },
            {
                "role": "user",
                "content": patient_message
            }
        ],
        max_tokens=200,
        temperature=0.1
    )

    return response.choices[0].message.content.strip()

# ── 7. Voice input functions ──────────────────────────────────
def record_audio(duration=5, sample_rate=16000):
    print(f"🎙️  Listening... (speak for up to {duration} seconds)")

    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32
    )
    sd.wait()
    print("✅ Recording complete")

    # Return audio array directly instead of saving to file
    return audio.flatten(), sample_rate

def transcribe_audio(audio_data, sample_rate) -> str:
    print("📝 Transcribing...")
    # Pass audio array directly to Whisper (no ffmpeg needed)
    result = whisper_model.transcribe(audio_data, fp16=False)
    text = result["text"].strip()
    print(f"🗣️  Patient said: {text}")
    return text

# ── 8. Full pipeline ──────────────────────────────────────────
def listen_and_respond(duration=5):
    audio_data, sample_rate = record_audio(duration=duration)
    patient_message = transcribe_audio(audio_data, sample_rate)

    if not patient_message:
        print("❌ Couldn't hear anything, please try again")
        return

    print("🤔 Thinking...")
    response = receptionist_response(patient_message)
    print(f"\n👩‍⚕️  Receptionist: {response}\n")
    speak(response)
    return response

# ── 9. Run the agent ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n🏥 Medical Receptionist Voice Agent Started")
    print("Press ENTER to speak, Ctrl+C to quit\n")

    while True:
        try:


            input("Press ENTER to speak...")
            listen_and_respond(duration=5)
            print("-" * 60)
        except KeyboardInterrupt:
            print("\n👋 Voice agent stopped.")
            break