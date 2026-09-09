#!/bin/bash
# Speech-to-Text Setup Helper Script
# This script helps set up the required dependencies for speech-to-text functionality

set -e

echo "================================"
echo "Speech-to-Text Setup Helper"
echo "================================"
echo ""

# Check if running from backend directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the backend/ directory"
    echo "  cd backend"
    echo "  ./setup_stt.sh"
    exit 1
fi

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python -m venv venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Google Cloud Speech-to-Text
echo ""
echo "📦 Installing Google Cloud Speech-to-Text..."
pip install google-cloud-speech>=2.21

# Install OpenAI (for Whisper fallback)
echo "📦 Installing OpenAI library..."
pip install openai>=1.40

# Ask if user wants to install local Whisper
echo ""
read -p "Do you want to install local Whisper for offline support? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 Installing openai-whisper..."
    pip install openai-whisper
    
    echo ""
    echo "Which model size do you want?"
    echo "  tiny   - Fastest, 39MB (lowest accuracy)"
    echo "  base   - Fast, 74MB"
    echo "  small  - Balanced, 244MB"
    echo "  medium - Good accuracy, 769MB (RECOMMENDED for African languages)"
    echo "  large  - Best accuracy, 2.9GB (very slow without GPU)"
    echo ""
    read -p "Choose model (default: medium): " model
    model=${model:-medium}
    
    echo "📥 Downloading Whisper $model model (~769MB)..."
    python -m whisper --model "$model" --help > /dev/null
    echo "✅ Whisper $model model downloaded to ~/.cache/whisper/"
fi

echo ""
echo "================================"
echo "✅ Installation Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Google Cloud Setup (RECOMMENDED):"
echo "   - Follow docs/SPEECH_TO_TEXT_SETUP.md"
echo "   - Set GOOGLE_CLOUD_STT_CREDENTIALS_PATH in .env"
echo ""
echo "2. Or use OpenAI Whisper (fallback):"
echo "   - Already installed and configured via OPENAI_API_KEY"
echo ""
echo "3. Test the setup:"
echo "   python run.py"
echo "   # Upload audio in Multi-Chat interface"
echo ""
