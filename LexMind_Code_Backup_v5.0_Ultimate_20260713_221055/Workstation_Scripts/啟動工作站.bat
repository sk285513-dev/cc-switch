@echo off
title LexMind-Omni Launcher
echo [INFO] Preparing environment...
cd /d C:\LocalAI_Workstation
echo [INFO] Starting Streamlit server on port 8501...
echo ==========================================
python -m streamlit run app.py --server.port 8501
pause
