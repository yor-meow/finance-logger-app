@echo off
title BouncyFinance App
echo ===================================================
echo   Starting BouncyFinance Logger & Deals Tracker...
echo ===================================================
cd /d "%~dp0"
python server.py
pause
