@echo off
setlocal

set "BASE_URL=%~1"
if "%BASE_URL%"=="" set "BASE_URL=http://127.0.0.1:8000"

python "%~dp0demo_user_scenario.py" "%BASE_URL%"
