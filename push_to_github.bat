@echo off
title Push CampusMate AI to GitHub
echo ===================================================
echo   CampusMate AI - GitHub Repository Pusher
echo ===================================================
echo.
echo Checking Git status...
git add .
git commit -m "Bootstrap CampusMate AI: FastAPI backend with native bcrypt, Glassmorphic Landing page, and complete Offline Sandbox mode." 2>nul

echo.
echo Pushing code to https://github.com/251801390006-blip/campusmate-ai.git...
git push -u origin main --force

if %errorlevel% neq 0 (
    echo.
    echo ---------------------------------------------------
    echo ERROR: Push failed.
    echo ---------------------------------------------------
    echo It looks like the repository "campusmate-ai" does not exist yet
    echo on your GitHub account: https://github.com/251801390006-blip
    echo.
    echo ACTION REQUIRED:
    echo 1. Go to https://github.com/new
    echo 2. Name your repository: "campusmate-ai"
    echo 3. Click "Create repository" (leave it empty)
    echo 4. Rerun this script to push all files successfully!
) else (
    echo.
    echo ---------------------------------------------------
    echo SUCCESS: Pushed successfully to GitHub!
    echo ---------------------------------------------------
    echo Your repository is live at:
    echo https://github.com/251801390006-blip/campusmate-ai
)
echo.
pause
