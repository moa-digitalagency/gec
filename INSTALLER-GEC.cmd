@echo off
rem GEC - installation rapide sur Windows Server : double-cliquer sur ce fichier.
rem Python et PostgreSQL sont installes automatiquement si absents.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\windows\installation-rapide-gec.ps1" %*
