import os
import torch
import librosa
import numpy as np 
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
try:
    import whisper
except ImportError:
    import openai
    whisper = None

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN not set. Please add it to your .env file.")

hf_client = InferenceClient(
    model="meta-llama/Meta-Llama-3-8B-Instruct",
    token=HF_TOKEN
)
audio_path = r"Audio_Recording\Audio1.mp3"

def process_clinical_audio(audio_path, output_file="final_soap_note.txt"):
    """
    Simplified pipeline: 
    Audio -> Whisper (Transcribe) -> Ollama (SOAP) -> Text File
    (Removed diarization to avoid FFmpeg/torchcodec dependency issues)
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Could not find audio file at {audio_path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print(f"Device: {device.upper()}...")
    
    print("Transcribing audio (this may take a moment)...")
    model = whisper.load_model("base", device=device)
    
    audio_data = librosa.load(audio_path, sr=16000)[0]
    
    result = model.transcribe(audio_data)
    
    print("Formatting transcription...")
    transcript_lines = []
    for segment in result["segments"]:
        text = segment.get("text", "").strip()
        if text:
            transcript_lines.append(f"[{segment['start']:.1f}s] {text}")
        
    full_transcript = "\n".join(transcript_lines)
    print("\nTranscription Complete!")

    print("Generating Clinical SOAP Note via HuggingFace Inference API...")
    
    user_prompt = f"""
You are an expert clinical medical scribe. Your ONLY job is to read the provided transcript and extract a professional SOAP note.

CRITICAL RULES:
1. First, deduce which speaker is the Doctor and which is the Patient based on the context.
2. DO NOT write dialogue or continue the conversation.
3. Return ONLY the Subjective, Objective, Assessment, and Plan sections.
4. Be concise and use medical terminology where appropriate. If a section is empty, write "None reported".

TRANSCRIPT:
{full_transcript}

FORMAT:
SUBJECTIVE:
- 
OBJECTIVE:
- 
ASSESSMENT:
- 
PLAN:
- 
"""

    llm_response = hf_client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are an expert clinical medical scribe. Extract professional SOAP notes from medical conversation transcripts."
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        max_tokens=800,
        temperature=0.1
    )
    
    soap_note = llm_response.choices[0].message.content.strip()

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("--- RAW TRANSCRIPT ---\n")
        f.write(full_transcript + "\n\n")
        f.write("--- SOAP NOTE ---\n")
        f.write(soap_note)
        
    print(f"\nSuccess! Output saved to: {output_file}")
    print("\n" + soap_note)

if __name__ == "__main__":
    AUDIO_FILE = audio_path
    
    try:
        process_clinical_audio(AUDIO_FILE)
    except Exception as e:
        import traceback
        print(f"An error occurred: {e}")
        traceback.print_exc()