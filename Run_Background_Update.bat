@echo off
cd /d "%~dp0"
echo 🚀 Starting Background Scraper Update...
echo This window will close automatically when finished.
python auto_updater.py
timeout /t 5
