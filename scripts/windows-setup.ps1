#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Z — Windows WSL2 Bootstrap
# Run this in PowerShell (as Administrator) to prepare your Windows machine.
# After this, run bootstrap.sh inside WSL2.
# ══════════════════════════════════════════════════════════════════════════════

Write-Host "AI Z — Windows Setup Script" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

# Step 1: Enable WSL2
Write-Host "`nStep 1: Enabling WSL2..." -ForegroundColor Yellow
wsl --install -d Ubuntu-22.04
Write-Host "WSL2 installed. Please restart if prompted." -ForegroundColor Green

# Step 2: Install Chocolatey (package manager)
Write-Host "`nStep 2: Installing Chocolatey..." -ForegroundColor Yellow
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Step 3: Install tools
Write-Host "`nStep 3: Installing kubectl, helm, git..." -ForegroundColor Yellow
choco install -y git kubectl helm docker-desktop vscode

Write-Host "`n==============================" -ForegroundColor Green
Write-Host "Windows setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "1. Restart your computer"
Write-Host "2. Open Ubuntu from Start Menu (WSL2)"
Write-Host "3. In Ubuntu terminal, run:"
Write-Host "   git clone https://github.com/YOUR_USERNAME/aiz-trading"
Write-Host "   cd aiz-trading"
Write-Host "   cp .env.example .env"
Write-Host "   nano .env   # Fill in your values"
Write-Host "   sudo bash scripts/bootstrap.sh"
Write-Host ""
Write-Host "See docs/MASTER.md for full step-by-step guide" -ForegroundColor Yellow
