# AI Z — Quick Start Guide for Windows Laptop
# Run these commands one by one in order

# ════════════════════════════════════════════
# PHASE 1: Install WSL2 + Ubuntu
# ════════════════════════════════════════════
# Run this in PowerShell AS ADMINISTRATOR:

wsl --install -d Ubuntu-22.04
# Restart computer when prompted
# After restart, Ubuntu opens → create username + password (remember these)

# ════════════════════════════════════════════
# PHASE 2: Inside Ubuntu (WSL2) — Install tools
# ════════════════════════════════════════════
# Open Ubuntu from Start Menu, then run:

sudo apt update && sudo apt install -y curl git nano

# ════════════════════════════════════════════
# PHASE 3: Clone your project
# ════════════════════════════════════════════

# Option A — if you pushed to GitHub:
git clone https://github.com/YOUR_USERNAME/aiz-trading
cd aiz-trading

# Option B — if not on GitHub yet, access Windows folder from WSL2:
cd "/mnt/c/Users/SZABEERA/OneDrive - Capgemini/Desktop/Project/aiz-trading"

# ════════════════════════════════════════════
# PHASE 4: Configure your .env
# ════════════════════════════════════════════

cp .env.example .env
nano .env

# MINIMUM required values to fill in:
# SECRET_KEY=         → run: openssl rand -hex 32  (paste result)
# JWT_SECRET=         → run: openssl rand -hex 32  (paste result)
# POSTGRES_PASSWORD=  → any strong password e.g. MyDB@2026
# ADMIN_PASSWORD=     → your dashboard login password
# ADMIN_EMAIL=        → your email
# DUCKDNS_TOKEN=      → from duckdns.org after login
# DUCKDNS_DOMAIN=     → aiz-trade  (without .duckdns.org)

# Leave broker as: ACTIVE_BROKER=paper  (no API key needed yet)
# Leave: TRADING_MODE=paper

# Save: Ctrl+X → Y → Enter

# ════════════════════════════════════════════
# PHASE 5: Install K3s + Deploy AI Z
# ════════════════════════════════════════════

sudo bash scripts/bootstrap.sh

# This takes 10-15 minutes. Go get a coffee.
# When done you will see:
#   ════════════════════════════════════════
#   AI Z is deployed!
#   ════════════════════════════════════════

# ════════════════════════════════════════════
# PHASE 6: Access it on YOUR LAPTOP
# ════════════════════════════════════════════

# Find K3s external IP:
kubectl get svc traefik -n kube-system

# Then open browser on your laptop:
# http://localhost        OR
# http://127.0.0.1

# Login with: admin / (your ADMIN_PASSWORD from .env)

# ════════════════════════════════════════════
# PHASE 7: Access from phone on same WiFi
# ════════════════════════════════════════════

# Get your laptop's local WiFi IP:
hostname -I | awk '{print $1}'
# Example: 192.168.1.105

# On your phone (connected to same WiFi):
# Open browser → http://192.168.1.105
# Done!

# ════════════════════════════════════════════
# PHASE 8: Access from ANYWHERE (internet)
# ════════════════════════════════════════════

# Run the access setup script:
bash scripts/setup-access.sh

# Follow Option A (port forwarding) instructions it prints.
# Your router: open browser → 192.168.1.1 → Port Forwarding
# Add: External 443 → 192.168.1.105:443
# Add: External 80  → 192.168.1.105:80
# Then: https://aiz-trade.duckdns.org works from anywhere!
