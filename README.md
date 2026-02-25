<<<<<<< HEAD
# MedicTime - AI Medical Assistant

A virtual assistant that helps doctors take notes, track patient records, and generate properly formatted SOAP notes (Subjective, Objective, Assessment, Plan).

## Features

- 🎙️ **Voice Chat**: RAG-powered medical receptionist assistant
- 📝 **SOAP Note Generation**: Automatic clinical documentation from audio
- 🏥 **Medical Database**: ChromaDB vector store with 24k+ medical conversations
- 🤖 **AI Models**: Meta-Llama-3-8B via HuggingFace, Whisper for transcription, Kokoro for TTS

---

## Setup Instructions

### Prerequisites
- Python 3.9 - 3.11 (recommended: 3.11)
- 8GB+ RAM
- (Optional) NVIDIA GPU for faster processing

---

## 🚀 Quick Setup (Recommended)

### **Method 1: Automated Setup Script** ⭐

**Windows:**
```powershell
.\setup.ps1
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

This script will:
1. Create virtual environment
2. Install PyTorch (with GPU support if available)
3. Install all dependencies in correct order
4. Create `.env` template
5. Verify installation

---

## 📦 Manual Installation

### **Method 2: Conda (Best for avoiding conflicts)** ⭐

```bash
# Install Miniconda/Anaconda first, then:
conda env create -f environment.yml
conda activate medictime
```

### **Method 3: Step-by-Step pip**

#### 1. Clone Repository
```bash
git clone <your-repo-url>
cd MedicTime
```

#### 2. Create Virtual Environment
```bash
python -m venv venv

# Activate:
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

#### 3. Install PyTorch First (Critical!)

**Choose based on your system:**

```bash
# CPU Only
pip install torch torchvision torchaudio

# NVIDIA GPU (CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# NVIDIA GPU (CUDA 12.1 - Latest)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Mac Apple Silicon
pip install torch torchvision torchaudio
```

See: https://pytorch.org/get-started/locally/ for more options

#### 4. Install Core Dependencies
```bash
pip install -r requirements-core.txt
```

---

## 🔐 Configure API Keys

Create a `.env` file in the root directory:
```env
HF_TOKEN=your_huggingface_token_here
```

**Get your token:**
- HuggingFace: https://huggingface.co/settings/tokens

---

## 🎤 Download TTS Model Files

Kokoro TTS requires model files to be downloaded:

```bash
cd MedicTime
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

**Or manually download:**
1. Download `kokoro-v1.0.onnx` from https://github.com/thewh1teagle/kokoro-onnx/releases
2. Download `voices-v1.0.bin` from the same releases page
3. Place both files in the MedicTime project root directory

---

## 🗄️ Set Up ChromaDB Vector Store

**Option A: Download Pre-built Database** (Recommended)
```bash
# Download from Google Drive (if provided)
# Extract to: ./medical_rag_store_v2/
```

**Option B: Build from Source Data**
```bash
# Download medical conversation dataset
# Links: https://drive.google.com/file/d/1WnuqQUIYRaF2D1YdnM8XY-75kCpFCYFg/view
# Place in ./data/ folder
# Then run:
python scripts/build_rag_store.py
```

### 6. Run the Server
```bash
python main.py
```

Server will start on http://localhost:8000

---

## Usage

### Web Interface
Open http://localhost:8000 in your browser

### API Endpoints

**Generate SOAP Note:**
```bash
POST /api/soap-from-audio
Content-Type: multipart/form-data
Body: audio file
```

**Chat with Assistant:**
```bash
POST /api/chat
Content-Type: application/json
Body: {"message": "Your question"}
```

**Voice Chat:**
```bash
POST /api/voice
Content-Type: multipart/form-data
Body: audio file
```

---

## Project Structure
```
MedicTime/
├── main.py                    # FastAPI server
├── Load_llama.py              # Voice assistant logic
├── rag_system.py              # SOAP note generator
├── .env                       # API keys (not in Git)
├── static/                    # Frontend files
│   └── index.html
├── medical_rag_store_v2/      # ChromaDB database (not in Git)
└── venv/                      # Virtual environment (not in Git)
```

---

## Important Notes

⚠️ **Database Not Included**: The ChromaDB vector store (182 MB) is not included in Git. You must either:
- Download it separately from the provided link
- Rebuild it from source medical conversation data

🎤 **TTS Model Files Required**: You need to download Kokoro ONNX model files (see setup section above)

🔒 **API Key Required**: You need a free HuggingFace account for the LLM

---

## 🐛 Troubleshooting

### Dependency Conflicts

**Problem:** `pip install` fails with version conflicts

**Solutions:**
1. Use **conda** instead: `conda env create -f environment.yml`
2. Use **automated script**: `./setup.ps1` or `./setup.sh`
3. Install PyTorch **separately first**, then other packages
4. Downgrade NumPy: `pip install "numpy<2.0"`

### PyTorch Installation Issues

**Problem:** PyTorch not detecting GPU / CUDA errors

**Solutions:**
1. Check CUDA compatibility: `nvidia-smi`
2. Install correct PyTorch version from https://pytorch.org/
3. For CPU only: `pip install torch torchvision torchaudio`

### FFmpeg Not Found

**Problem:** `RuntimeWarning: Couldn't find ffmpeg`

**Solutions:**
- Already included! `imageio-ffmpeg` provides FFmpeg binaries
- Warning is harmless and can be ignored
- FFmpeg is working if audio transcription succeeds

### ChromaDB Loading Errors

**Problem:** `Collection not found` or database errors

**Solutions:**
1. Download the pre-built database from provided link
2. Extract `medical_rag_store_v2/` folder to project root
3. Verify folder structure: `./medical_rag_store_v2/chroma.sqlite3` exists

### Import Errors

**Problem:** `ModuleNotFoundError` or import failures

**Solutions:**
1. Verify virtual environment is activated
2. Re-run installation: `pip install -r requirements-core.txt`
3. Check Python version: Must be 3.9-3.11

### Port 8000 Already in Use

**Problem:** `Address already in use` error

**Solutions (Windows):**
```powershell
# Find and kill process using port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
Stop-Process -Id <PID> -Force
```

**Solutions (Linux/Mac):**
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9
```

### API Token Errors

**Problem:** `Invalid token` or `Unauthorized` errors

**Solutions:**
1. Verify `.env` file exists in project root
2. Check token format (no quotes, no spaces)
3. Get new token if expired:
   - HuggingFace: https://huggingface.co/settings/tokens

### Kokoro TTS Model Not Found

**Problem:** `FileNotFoundError: Voices file not found`

**Solutions:**
1. Download model files to project root:
   ```bash
   wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
   wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
   ```
2. Verify both files exist in project root directory
3. Check file permissions

---

## 📝 Additional Files Explained

- **requirements.txt** - Full pip freeze (may have conflicts - use with caution)
- **requirements-core.txt** - Minimal dependencies (recommended for pip)
- **environment.yml** - Conda environment file (best for avoiding conflicts)
- **setup.ps1 / setup.sh** - Automated installation scripts

---

## Dataset Sources

Medical conversation data from:
- https://drive.google.com/file/d/1WnuqQUIYRaF2D1YdnM8XY-75kCpFCYFg/view
- https://drive.google.com/file/d/1--HS5l8zDoutCoAwx4qgzKHqZldoTyzW/view

Place downloaded files in `./data/` folder

=======
# MedicTime
A RAG based Virtual Assistant that helps doctors take SOAP notes.
>>>>>>> fd908617a77918a559e0675f45c7774d7acc1cf7
