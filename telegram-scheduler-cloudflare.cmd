@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON_BIN=%ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON_BIN%" (
  set "PYTHON_BIN=python"
)

if defined PYTHONPATH (
  set "PYTHONPATH=%ROOT%apps\server;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%ROOT%apps\server"
)

"%PYTHON_BIN%" -m scheduler_app.dev.tunnel --provider cloudflare %*
