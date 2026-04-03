@echo off
echo ========================================
echo  AbhayaRaksha - Setup Script (Windows)
echo ========================================

echo.
echo [1/4] Setting up Python backend...
cd backend
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
echo.
echo  >> Edit backend\.env with your API keys and DB URL before starting!
echo.

echo [2/4] Setting up Frontend...
cd ..\frontend
npm install

echo.
echo [3/4] Training ML models...
cd ..
python ml\train_risk_model.py
python ml\train_fraud_model.py

echo.
echo ========================================
echo  Setup complete!
echo.
echo  NEXT STEPS:
echo  1. Edit backend\.env if needed (optional - SQLite works out of the box)
echo  2. Start backend:  cd backend ^& venv\Scripts\activate ^& uvicorn app.main:app --reload
echo  3. Seed data:      cd backend ^& python seed.py
echo  4. Start frontend: cd frontend ^& npm run dev
echo  5. Open: http://localhost:3000
echo ========================================
