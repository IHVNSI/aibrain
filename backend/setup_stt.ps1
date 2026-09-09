# Speech-to-Text Setup Helper Script (Windows PowerShell)
# This script helps set up the required dependencies for speech-to-text functionality

Write-Host "================================"
Write-Host "Speech-to-Text Setup Helper (Windows)"
Write-Host "================================"
Write-Host ""

# Check if running from backend directory
if (-not (Test-Path "requirements.txt")) {
    Write-Host "❌ Error: Please run this script from the backend/ directory" -ForegroundColor Red
    Write-Host "  cd backend"
    Write-Host "  .\setup_stt.ps1"
    exit 1
}

# Check virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "⚠️  Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "📦 Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "📦 Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install Google Cloud Speech-to-Text
Write-Host ""
Write-Host "📦 Installing Google Cloud Speech-to-Text..." -ForegroundColor Cyan
pip install "google-cloud-speech>=2.21"

# Install OpenAI (for Whisper fallback)
Write-Host "📦 Installing OpenAI library..." -ForegroundColor Cyan
pip install "openai>=1.40"

# Ask if user wants to install local Whisper
Write-Host ""
Write-Host "Do you want to install local Whisper for offline support? (y/n)" -ForegroundColor Yellow
$response = Read-Host
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host "📦 Installing openai-whisper..." -ForegroundColor Cyan
    pip install openai-whisper
    
    Write-Host ""
    Write-Host "Which model size do you want?"
    Write-Host "  tiny   - Fastest, 39MB (lowest accuracy)"
    Write-Host "  base   - Fast, 74MB"
    Write-Host "  small  - Balanced, 244MB"
    Write-Host "  medium - Good accuracy, 769MB (RECOMMENDED for African languages)"
    Write-Host "  large  - Best accuracy, 2.9GB (very slow without GPU)"
    Write-Host ""
    $model = Read-Host "Choose model (default: medium)"
    if ([string]::IsNullOrWhiteSpace($model)) {
        $model = "medium"
    }
    
    Write-Host "📥 Downloading Whisper $model model..." -ForegroundColor Cyan
    & python -m whisper --model $model --help > $null
    Write-Host "✅ Whisper $model model downloaded to %USERPROFILE%\.cache\whisper\" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================"
Write-Host "✅ Installation Complete!" -ForegroundColor Green
Write-Host "================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Google Cloud Setup (RECOMMENDED):"
Write-Host "   - Follow docs/SPEECH_TO_TEXT_SETUP.md"
Write-Host "   - Set GOOGLE_CLOUD_STT_CREDENTIALS_PATH in .env"
Write-Host ""
Write-Host "2. Or use OpenAI Whisper (fallback):"
Write-Host "   - Already installed and configured via OPENAI_API_KEY"
Write-Host ""
Write-Host "3. Test the setup:"
Write-Host "   python run.py"
Write-Host "   # Upload audio in Multi-Chat interface"
Write-Host ""
Write-Host "4. Verify requirements are installed:"
Write-Host "   pip list | findstr 'google-cloud-speech openai whisper'"
Write-Host ""
