#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Z — Complete Step-by-Step Deployment Guide
# Run this file's commands ONE BY ONE in order.
# This covers: GitHub push → new machine setup → application live
# ══════════════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════
# PART 1: PUSH TO GITHUB (on your Windows machine)
# ════════════════════════════════════════════

# Step 1.1 — Install Git for Windows if not already installed
# Download: https://git-scm.com/download/win → install with defaults

# Step 1.2 — Open PowerShell in the project folder
# In File Explorer: right-click "aiz-trading" folder → "Open in Terminal"
# OR in PowerShell:
#   cd "c:\Users\SZABEERA\OneDrive - Capgemini\Desktop\Project\aiz-trading"

# Step 1.3 — Create GitHub account (if you don't have one)
# Go to: https://github.com → Sign up (free)
# Repository name: aiz-trading
# Visibility: PRIVATE (important — keeps your code private)

# Step 1.4 — Initialize Git and push
#   cd "c:\Users\SZABEERA\OneDrive - Capgemini\Desktop\Project\aiz-trading"
#   git init
#   git add .
#   git commit -m "initial: AI Z trading platform v1.0"
#   git branch -M main
#   git remote add origin https://github.com/YOUR_GITHUB_USERNAME/aiz-trading.git
#   git push -u origin main

# GitHub will ask for your username + password (or personal access token).
# To create a token: github.com → Settings → Developer Settings → Personal Access Tokens → Generate New Token
# Give it: repo scope → copy token → use as password when prompted

# ════════════════════════════════════════════
# PART 2: SETUP ON NEW MACHINE (Ubuntu 22.04)
# Run these commands ON THE NEW MACHINE
# ════════════════════════════════════════════

# Step 2.1 — Install required tools
sudo apt update && sudo apt install -y curl git nano openssl

# Step 2.2 — Clone your project from GitHub
git clone https://github.com/YOUR_GITHUB_USERNAME/aiz-trading
cd aiz-trading

# Step 2.3 — Generate secure keys
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY"
echo "JWT_SECRET=$JWT_SECRET"
# COPY THESE VALUES — you'll paste them in the next step

# Step 2.4 — Create .env from template
cp .env.example .env
nano .env
# Fill in these values:
#   SECRET_KEY=          → paste from Step 2.3
#   JWT_SECRET=          → paste from Step 2.3
#   POSTGRES_PASSWORD=   → any strong password e.g. DbPass@2026
#   REDIS_PASSWORD=      → any strong password e.g. RedisPass@2026
#   ADMIN_PASSWORD=      → your AI Z dashboard login password
#   ADMIN_EMAIL=         → your email
#   ADMIN_USERNAME=      → admin (or your name)
#   GRAFANA_ADMIN_PASSWORD= → Grafana dashboard password
#   DUCKDNS_TOKEN=       → from duckdns.org (if using domain)
#   DUCKDNS_DOMAIN=      → aiz-trade (if using domain)
# Save: Ctrl+X → Y → Enter

# ════════════════════════════════════════════
# PART 3A: DEPLOY WITH K8s (Recommended — HA, production-grade)
# ════════════════════════════════════════════

# Step 3A.1 — Run bootstrap (localhost mode — no domain needed)
sudo bash scripts/bootstrap.sh --localhost

# This does everything automatically:
#   ✓ Installs K3s (Kubernetes)
#   ✓ Installs Helm
#   ✓ Installs ArgoCD
#   ✓ Creates namespace + secrets
#   ✓ Deploys PostgreSQL, Redis, Backend, ML Engine, Frontend
# Takes 10-15 minutes.

# Step 3A.2 — Verify all pods are running
kubectl get pods -n aiz
# All pods should show: Running
# If any show Pending/Error wait 2 min and check again

# Step 3A.3 — Check logs if something is wrong
kubectl logs -n aiz deployment/aiz-backend
kubectl logs -n aiz deployment/aiz-ml-engine

# Step 3A.4 — Access the application
# On same machine: http://localhost
# From another device on same WiFi:
#   YOUR_LOCAL_IP=$(hostname -I | awk '{print $1}')
#   echo "http://$YOUR_LOCAL_IP"

# ════════════════════════════════════════════
# PART 3B: DEPLOY WITH DOCKER COMPOSE (Simpler — Windows Docker Desktop)
# Use this if you just want to test quickly on Windows WITHOUT WSL2/K3s
# ════════════════════════════════════════════

# Prerequisites: Docker Desktop installed → https://www.docker.com/products/docker-desktop/

# Step 3B.1 — In PowerShell, go to project folder
#   cd "c:\Users\SZABEERA\OneDrive - Capgemini\Desktop\Project\aiz-trading"

# Step 3B.2 — Copy and fill .env
#   cp .env.example .env
#   notepad .env    (fill in the same values as above)

# Step 3B.3 — Start everything
#   docker compose -f docker-compose.dev.yml up -d

# Step 3B.4 — Access
#   Frontend: http://localhost:3000
#   Backend API docs: http://localhost:8000/api/docs

# Step 3B.5 — Stop everything
#   docker compose -f docker-compose.dev.yml down

# ════════════════════════════════════════════
# PART 4: VERIFY APPLICATION IS WORKING
# ════════════════════════════════════════════

# Step 4.1 — Open browser: http://localhost (K8s) or http://localhost:3000 (Docker)
# You should see: AI Z login screen with neural animation

# Step 4.2 — Login
# Username: admin
# Password: (what you set in ADMIN_PASSWORD)

# Step 4.3 — Check dashboard
# You should see: Portfolio stats, empty positions, bot status = LIVE

# Step 4.4 — Verify bot is running (K8s)
kubectl logs -n aiz deployment/aiz-ml-engine -f
# You should see lines like:
#   [AIZ] Fetching 3Y historical data for RELIANCE.NS...
#   [AIZ] Training XGBoost model...
#   [AIZ] Trading loop started. Mode: paper

# ════════════════════════════════════════════
# PART 5: AFTER APP IS WORKING — Optional steps
# ════════════════════════════════════════════

# Enable domain access (internet accessible):
bash scripts/setup-access.sh

# Add monitoring (Grafana + Prometheus):
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.adminPassword="$GRAFANA_ADMIN_PASSWORD"

# Access Grafana:
kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80
# Open: http://localhost:3001

# Add second machine to cluster:
bash scripts/add-node.sh

# ════════════════════════════════════════════
# PART 6: UPDATE CODE AND REDEPLOY
# ════════════════════════════════════════════

# After making any code changes:
git add .
git commit -m "update: describe your change"
git push origin main
# ArgoCD automatically picks up changes and redeploys (2-3 min)

# Or manually redeploy:
helm upgrade aiz ./helm/aiz --namespace aiz --values helm/aiz/values.localhost.yaml

# ════════════════════════════════════════════
# QUICK REFERENCE — Most Used Commands
# ════════════════════════════════════════════

# See all running pods:
#   kubectl get pods -n aiz

# Restart a service:
#   kubectl rollout restart deployment/aiz-backend -n aiz
#   kubectl rollout restart deployment/aiz-ml-engine -n aiz

# View live logs:
#   kubectl logs -n aiz deployment/aiz-backend -f
#   kubectl logs -n aiz deployment/aiz-ml-engine -f

# Check resource usage:
#   kubectl top pods -n aiz

# Connect to database:
#   kubectl exec -it -n aiz postgresql-0 -- psql -U aiz_user aiz_trading

# See all services/ports:
#   kubectl get svc -n aiz

# Full cleanup (WARNING: deletes all data):
#   helm uninstall aiz -n aiz
