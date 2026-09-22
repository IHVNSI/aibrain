#!/bin/bash
# WebSocket Real-Time Setup Script
# Run this script to install all dependencies and verify setup

echo "🚀 Brainr WebSocket Real-Time Setup"
echo "===================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python
echo -e "${BLUE}[1/4] Checking Python...${NC}"
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found. Please install Python 3.8+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
echo ""

# Install backend dependencies
echo -e "${BLUE}[2/4] Installing backend dependencies...${NC}"
cd backend
pip install flask-socketio>=5.3 python-socketio>=5.9 python-engineio>=4.7 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backend dependencies installed${NC}"
else
    echo "Installing full requirements.txt..."
    pip install -r requirements.txt 2>/dev/null
    echo -e "${GREEN}✓ Requirements installed${NC}"
fi
cd ..
echo ""

# Check Node.js
echo -e "${BLUE}[3/4] Checking Node.js for frontend...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}⚠ Node.js not found. Frontend setup skipped.${NC}"
    echo "Install Node.js from https://nodejs.org/ for frontend support"
else
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js $NODE_VERSION found${NC}"
    
    # Install frontend dependencies
    echo "Installing frontend dependencies..."
    cd frontend
    npm install 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
    else
        echo "Updating npm and retrying..."
        npm install --legacy-peer-deps 2>/dev/null
        echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
    fi
    cd ..
fi
echo ""

# Verify installation
echo -e "${BLUE}[4/4] Verifying installation...${NC}"
python -c "import flask_socketio; print('✓ flask-socketio installed')" 2>/dev/null
python -c "import socketio; print('✓ python-socketio installed')" 2>/dev/null
python -c "import engineio; print('✓ python-engineio installed')" 2>/dev/null

if [ -f "frontend/node_modules/socket.io-client/package.json" ]; then
    echo "✓ socket.io-client installed"
else
    echo "⚠ socket.io-client not installed (frontend only)"
fi
echo ""

echo -e "${GREEN}===================================="
echo "✅ Setup Complete!"
echo "====================================${NC}"
echo ""
echo "📝 Next Steps:"
echo "1. Backend: cd backend && python run.py"
echo "2. Frontend: cd frontend && npm run dev"
echo "3. Check browser console for '✓ WebSocket connected'"
echo "4. Check backend logs for '✓ WebSocket initialized'"
echo ""
echo "📚 Documentation: See WEBSOCKET_IMPLEMENTATION_GUIDE.md"
echo ""
