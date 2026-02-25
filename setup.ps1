#!/usr/bin/env pwsh
<#
.SYNOPSIS
    MedicTime Setup Script - Installs all dependencies in correct order
.DESCRIPTION
    Handles PyTorch installation based on platform, then installs other dependencies
#>

Write-Host "`n🏥 MedicTime Setup Script" -ForegroundColor Cyan
Write-Host "=" * 50

# Check Python version
$pythonVersion = python --version 2>&1
Write-Host "Python version: $pythonVersion" -ForegroundColor Green

# Create virtual environment if not exists
if (-not (Test-Path "venv")) {
    Write-Host "`n📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
} else {
    Write-Host "`n✅ Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "`n🔧 Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "`n⬆️  Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Detect platform and install PyTorch
Write-Host "`n🔥 Installing PyTorch..." -ForegroundColor Yellow
Write-Host "Choose your platform:" -ForegroundColor Cyan
Write-Host "  1. CUDA 11.8 (NVIDIA GPU)"
Write-Host "  2. CUDA 12.1 (NVIDIA GPU - Latest)"
Write-Host "  3. CPU only (No GPU)"
Write-Host "  4. Mac (Apple Silicon)"
$choice = Read-Host "Enter choice (1-4)"

switch ($choice) {
    "1" { 
        Write-Host "Installing PyTorch with CUDA 11.8..." -ForegroundColor Green
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    }
    "2" { 
        Write-Host "Installing PyTorch with CUDA 12.1..." -ForegroundColor Green
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    }
    "3" { 
        Write-Host "Installing PyTorch (CPU only)..." -ForegroundColor Green
        pip install torch torchvision torchaudio
    }
    "4" {
        Write-Host "Installing PyTorch for Mac..." -ForegroundColor Green
        pip install torch torchvision torchaudio
    }
    default { 
        Write-Host "Invalid choice, installing CPU version..." -ForegroundColor Red
        pip install torch torchvision torchaudio
    }
}

# Install core dependencies
Write-Host "`n📚 Installing core dependencies..." -ForegroundColor Yellow
pip install -r requirements-core.txt

# Check if installation was successful
Write-Host "`n🧪 Verifying installation..." -ForegroundColor Yellow
python -c "import torch; import whisper; import chromadb; import elevenlabs; print('✅ All core packages installed successfully!')" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Installation completed successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some packages may have issues. Please check manually." -ForegroundColor Yellow
}

# Check for .env file
Write-Host "`n🔐 Checking for .env file..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found!" -ForegroundColor Red
    Write-Host "Creating .env template..." -ForegroundColor Yellow
    @"
# API Keys and Tokens
HF_TOKEN=your_huggingface_token_here
ELEVEN_API_KEY=your_elevenlabs_api_key_here
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "✅ Created .env template. Please add your API keys!" -ForegroundColor Green
} else {
    Write-Host "✅ .env file found" -ForegroundColor Green
}

Write-Host "`n" + "=" * 50
Write-Host "🎉 Setup complete! Run 'python main.py' to start the server" -ForegroundColor Cyan
Write-Host "=" * 50 + "`n"
