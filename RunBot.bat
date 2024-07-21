@echo off

title Discord Payment Bot

set "program_name=python.exe"
set "script_path=%~dp0DiscordPaymentBot.py"
set "log_file=%~dp0DiscordPaymentBot.log"

tasklist | findstr /i "%program_name%" > nul

if %errorlevel% neq 0 (
  echo Server is not running. Starting the server...
  start "" python "%script_path%" > "%log_file%" 2>&1
) else (
  echo Server is already running.
)