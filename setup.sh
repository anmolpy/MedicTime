#!/bin/bash
# MedicTime Setup Script - Installs all dependencies in correct order

echo ""
echo "🏥 MedicTime Setup Script"
echo "=================================================="

# Check Python version
python_version=$(python3 --version 2>&1)
echo "Python version: $python_version"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo ""
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Detect platform and install PyTorch
echo ""
echo "🔥 Installing PyTorch..."
echo "Choose your platform:"
echo "  1. CUDA 11.8 (NVIDIA GPU)"
echo "  2. CUDA 12.1 (NVIDIA GPU - Latest)"
echo "  3. CPU only (No GPU)"
echo "  4. Mac (Apple Silicon)"
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo "Installing PyTorch with CUDA 11.8..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        ;;
    2)
        echo "Installing PyTorch with CUDA 12.1..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
        ;;
    3)
        echo "Installing PyTorch (CPU only)..."
        pip install torch torchvision torchaudio
        ;;
    4)
        echo "Installing PyTorch for Mac..."
        pip install torch torchvision torchaudio
        ;;
    *)
        echo "Invalid choice, installing CPU version..."
        pip install torch torchvision torchaudio
        ;;
esac

# Install core dependencies
echo ""
echo "📚 Installing core dependencies..."
pip install -r requirements-core.txt

# Check if installation was successful
echo ""
echo "🧪 Verifying installation..."
if python -c "import torch; import whisper; import chromadb; import kokoro_onnx; print('✅ All core packages installed successfully!')" 2>/dev/null; then
    echo "✅ Installation completed successfully!"
else
    echo "⚠️  Some packages may have issues. Please check manually."
fi

# Download Kokoro model files
echo ""
echo "🎤 Downloading Kokoro TTS model files..."
if [ ! -f "kokoro-v1.0.onnx" ]; then
    echo "Downloading kokoro-v1.0.onnx..."
    wget -q https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
    echo "✅ Downloaded kokoro-v1.0.onnx"
else
    echo "✅ kokoro-v1.0.onnx already exists"
fi

if [ ! -f "voices-v1.0.bin" ]; then
    echo "Downloading voices-v1.0.bin..."
    wget -q https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
    echo "✅ Downloaded voices-v1.0.bin"
else
    echo "✅ voices-v1.0.bin already exists"
fi

# Check for .env file
echo ""
echo "🔐 Checking for .env file..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env template..."
    cat > .env << 'EOF'
# API Keys and Tokens
HF_TOKEN=your_huggingface_token_here
EOF
    echo "✅ Created .env template. Please add your HuggingFace API key!"
else
    echo "✅ .env file found"
fi

echo ""
echo "=================================================="
echo "🎉 Setup complete! Run 'python main.py' to start the server"
echo "=================================================="
echo ""
