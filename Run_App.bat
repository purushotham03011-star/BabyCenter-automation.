@echo off
cd /d "%~dp0"
echo Starting Iron Niti Automation Scraper...
python -m streamlit run scraper_app.py
pause
