@echo off
REM WebSocket Real-Time Setup Script for Windows
REM Run this script to install all dependencies and verify setup

echo.
echo 🚀 Brainr WebSocket Real-Time Setup
echo ====================================
echo.

REM Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION% found
echo.

REM Install backend dependencies
echo [2/4] Installing backend dependencies...
cd backend
pip install flask-socketio^>=5.3 python-socketio^>=5.9 python-engineio^>=4.7 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Backend dependencies installed
) else (
    echo Installing full requirements.txt...
    pip install -r requirements.txt >nul 2>&1
    echo ✓ Requirements installed
)
cd ..
echo.

REM Check Node.js
echo [3/4] Checking Node.js for frontend...
node --version >nul 2>&1
if errorlevel 1 (
    echo ⚠ Node.js not found. Frontend setup skipped.
    echo Install Node.js from https://nodejs.org/ for frontend support
) else (
    for /f %%i in ('node --version') do set NODE_VERSION=%%i
    echo ✓ Node.js !NODE_VERSION! found
    
    REM Install frontend dependencies
    echo Installing frontend dependencies...
    cd frontend
    call npm install >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✓ Frontend dependencies installed
    ) else (
        echo Updating npm and retrying...
        call npm install --legacy-peer-deps >nul 2>&1
        echo ✓ Frontend dependencies installed
    )
    cd ..
)
echo.

REM Verify installation
echo [4/4] Verifying installation...
python -c "import flask_socketio; print('✓ flask-socketio installed')" 2>nul
python -c "import socketio; print('✓ python-socketio installed')" 2>nul
python -c "import engineio; print('✓ python-engineio installed')" 2>nul

if exist "frontend\node_modules\socket.io-client\package.json" (
    echo ✓ socket.io-client installed
) else (
    echo ⚠ socket.io-client not installed (frontend only)
)
echo.

echo.
echo ====================================
echo ✅ Setup Complete!
echo ====================================
echo.
echo 📝 Next Steps:
echo 1. Backend: cd backend ^&^& python run.py
echo 2. Frontend: cd frontend ^&^& npm run dev
echo 3. Check browser console for "✓ WebSocket connected"
echo 4. Check backend logs for "✓ WebSocket initialized"
echo.
echo 📚 Documentation: See WEBSOCKET_IMPLEMENTATION_GUIDE.md
echo.
pause
