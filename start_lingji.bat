@echo off
cd /d "%~dp0"
echo Starting LingJi PEMIS v5...
start /B python start_lingji.py
echo LingJi started in background. Check logs/lingji_service.log
