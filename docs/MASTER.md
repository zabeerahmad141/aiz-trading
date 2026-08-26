# AI Z — Master Documentation
# The Complete Encyclopedia of the AI Z Trading Platform

---

## TABLE OF CONTENTS

1. [Project Vision & Goals](#1-project-vision--goals)  
2. [How the AI Trading Bot Works](#2-how-the-ai-trading-bot-works)  
3. [Complete Architecture](#3-complete-architecture)  
4. [Technologies Used](#4-technologies-used)  
5. [Project Structure Explained](#5-project-structure-explained)  
6. [How This Project Was Created](#6-how-this-project-was-created)  
7. [Windows Machine Setup (WSL2 + K3s)](#7-windows-machine-setup)  
8. [AngelOne SmartAPI — Step by Step](#8-angelone-smartapi-setup)  
9. [DuckDNS — Free Domain Setup](#9-duckdns-free-domain-setup)  
10. [Cloudflare Tunnel — Access from Anywhere](#10-cloudflare-tunnel-setup)  
11. [Deploying the Full Application](#11-deploying-the-full-application)  
12. [User Management & Multi-User Access](#12-user-management)  
13. [Security Architecture](#13-security-architecture)  
14. [Paper Trading → Live Trading](#14-switching-to-live-trading)  
15. [Adding a Second Machine (HA Cluster)](#15-adding-a-second-machine)  
16. [Monitoring — Grafana + Prometheus](#16-monitoring)  
17. [Backup & Recovery](#17-backup--recovery)  
18. [Moving to Another Machine](#18-moving-to-another-machine)  
19. [Adding New Brokers](#19-adding-new-brokers)  
20. [Adding New ML Models](#20-adding-new-ml-models)  
21. [Upgrading to Custom Domain](#21-upgrading-to-custom-domain)  
22. [Troubleshooting](#22-troubleshooting)  
23. [Glossary](#23-glossary)  

---

## 1. Project Vision & Goals

**AI Z** is a fully automated AI-powered trading platform built to:

- Analyze historical market data using machine learning
- Predict stock price movements with confidence scoring
- Execute trades automatically without human intervention
- Provide a professional web dashboard accessible from anywhere
- Run on a single laptop or scale to multi-machine HA cluster
- Cost zero to run (all free tools and services)
- Serve multiple users (multi-tenant SaaS-ready architecture)

**Primary market**: NSE (National Stock Exchange, India)  
**Default assets**: Nifty 50 intraday stocks  
**Default broker**: AngelOne SmartAPI (free)  
**Default mode**: Paper trading (simulated, no real money)

---

## 2. How the AI Trading Bot Works

```
STEP 1 — DATA COLLECTION
  yfinance + AngelOne API
    ↓ Downloads 3 years of OHLCV data for Nifty 50 stocks
    ↓ Updates with live 5-minute bars during market hours

STEP 2 — FEATURE ENGINEERING
  24 Technical Indicators computed:
    RSI, MACD, EMA 9/21/50, Bollinger Bands,
    Stochastic, ATR, OBV, Volume Ratio, Momentum, ROC,
    EMA Cross, BB%, HL%, CO%, Gap%, Price/EMA ratio

STEP 3 — ML MODEL TRAINING
  XGBoost Classifier (primary) + LSTM (optional)
    ↓ Trained on 3 years of data
    ↓ TimeSeriesSplit cross-validation (prevents look-ahead bias)
    ↓ Target: Did price increase >0.5% in next bar?
    ↓ Retrained every morning at 8:00 AM

STEP 4 — SIGNAL GENERATION (every 60 seconds during market hours)
  For each stock in watchlist:
    ↓ Fetch latest 5-min bars
    ↓ Compute features
    ↓ Run through ML model
    ↓ Output: BUY (>65% confidence) / SELL (<35%) / HOLD

STEP 5 — RISK MANAGEMENT (every signal goes through this)
  ✓ Confidence ≥ 65%?
  ✓ Daily loss limit not reached?
  ✓ Max positions not exceeded?
  ✓ No existing position in same stock?
  ✓ Enough capital?
  → Position size = (Capital × 2%) / Stop-loss distance

STEP 6 — ORDER EXECUTION
  Paper mode: Simulated order, recorded in database
  Live mode:  Real order via AngelOne/Zerodha API

STEP 7 — MONITORING & EXIT
  ✓ Stop-loss hit → Auto-exit
  ✓ Target price hit → Auto-exit
  ✓ Market closing (3:25 PM) → Force exit all intraday positions
  ✓ Daily loss circuit breaker → Stop trading for the day

STEP 8 — REPORTING
  All trades logged to PostgreSQL
  Live P&L streamed to dashboard via WebSocket
  Daily reports generated
```

---

## 3. Complete Architecture

```
Internet
   │
   ▼
Cloudflare Tunnel (free, no port forwarding needed)
   │
   ▼
DuckDNS: aiz-trade.duckdns.org
   │ HTTPS (Let's Encrypt, auto-renew)
   ▼
K3s Kubernetes Cluster (your laptop/machine)
   │
   ├── NAMESPACE: aiz
   │     ├── frontend     (React, 2 pods, nginx)
   │     ├── backend      (FastAPI, 2 pods)
   │     ├── ml-engine    (Python trading bot, 1 pod)
   │     ├── postgresql   (TimescaleDB, 1 StatefulSet)
   │     ├── redis        (Cache + pub/sub, 1 pod)
   │     └── mlflow       (ML experiment tracking)
   │
   ├── NAMESPACE: monitoring
   │     ├── prometheus   (metrics collection)
   │     └── grafana      (dashboards)
   │
   └── NAMESPACE: argocd
         └── argocd-server (GitOps CD — auto-deploys from Git)

External connections:
  ml-engine  ──→  AngelOne API  (market data + orders)
  ml-engine  ──→  yfinance      (historical data, free)
  duckdns-updater → duckdns.org (every 5 minutes)
```

---

## 4. Technologies Used

### Frontend
| Technology | What it is | Why we use it |
|---|---|---|
| **React 18** | JavaScript UI library by Meta | Fast, component-based, huge ecosystem |
| **TypeScript** | JavaScript + static types | Catches bugs at compile time, better IDE support |
| **TailwindCSS** | Utility-first CSS framework | Rapid UI development, fully customizable |
| **Vite** | Next-gen build tool | 10x faster than webpack, instant hot reload |
| **Zustand** | Lightweight state management | Simpler than Redux, perfect for auth state |
| **TanStack Query** | Data fetching/caching library | Auto-refreshes data, handles loading/error states |
| **Axios** | HTTP client | Cleaner than fetch, interceptor support for auth |
| **Lightweight Charts** | TradingView charting library (free) | Professional candlestick charts |
| **Recharts** | Chart library built on D3 | Portfolio and P&L charts |
| **React Router v6** | Client-side routing | SPA navigation |
| **Lucide React** | Icon library | Clean, consistent icons |
| **React Hot Toast** | Notification library | Trade alert popups |
| **Nginx** | Web server | Serves built React app, proxies API |

### Backend
| Technology | What it is | Why we use it |
|---|---|---|
| **FastAPI** | Modern Python web framework | Fastest Python framework, auto API docs, native WebSocket |
| **SQLAlchemy 2** | ORM (Object Relational Mapper) | Safe database queries, prevents SQL injection |
| **Asyncpg** | Async PostgreSQL driver | Non-blocking DB queries |
| **Alembic** | Database migration tool | Version-controlled schema changes |
| **Pydantic v2** | Data validation library | Validates all API inputs automatically |
| **Redis** | In-memory cache + message broker | Fast caching of market data, pub/sub |
| **Python-jose** | JWT implementation | Secure token generation/validation |
| **Passlib + bcrypt** | Password hashing | Secure password storage |
| **Loguru** | Logging library | Beautiful, structured logs |
| **Prometheus Instrumentator** | Metrics exporter | Exposes /metrics for Prometheus |

### ML Engine
| Technology | What it is | Why we use it |
|---|---|---|
| **XGBoost** | Gradient boosting ML library | State-of-the-art accuracy on tabular data |
| **TensorFlow/Keras** | Deep learning framework | LSTM for sequence modeling (optional) |
| **scikit-learn** | ML utility library | Data splitting, scaling, metrics |
| **pandas** | Data manipulation library | OHLCV data processing |
| **numpy** | Numerical computing | Fast array operations |
| **ta (technical-analysis)** | Technical indicator library | 60+ indicators computed in one call |
| **yfinance** | Yahoo Finance data library (free) | Historical OHLCV data for any stock |
| **MLflow** | ML experiment tracking | Logs model versions, accuracy, parameters |
| **schedule** | Python job scheduler | Runs model retraining at 8 AM daily |

### Database
| Technology | What it is | Why we use it |
|---|---|---|
| **PostgreSQL 16** | Relational database | Reliable, ACID-compliant, great for financial data |
| **TimescaleDB** | PostgreSQL extension for time-series | Fast queries on time-series market data |

### Infrastructure
| Technology | What it is | Why we use it |
|---|---|---|
| **K3s** | Lightweight Kubernetes | Full K8s API, uses 512MB RAM, perfect for single machine |
| **Helm** | Kubernetes package manager | Deploy all services with one command |
| **ArgoCD** | GitOps continuous delivery | Auto-deploys when you push to Git |
| **cert-manager** | SSL certificate manager | Auto-issues + renews Let's Encrypt SSL |
| **Traefik** | Ingress controller (K3s default) | Routes external traffic to services |
| **DuckDNS** | Free dynamic DNS | Free domain that auto-updates when IP changes |
| **Cloudflare Tunnel** | Secure tunneling (free) | Expose app without static IP or port forwarding |
| **GitHub Actions** | CI/CD platform | Builds Docker images on every Git push |
| **Docker** | Container runtime | Packages each service into portable containers |

### Broker APIs
| Technology | What it is | Why we use it |
|---|---|---|
| **AngelOne SmartAPI** | Free broker API | Free live trading, NSE/BSE, Python SDK |
| **Kite Connect** | Zerodha's paid API | Industry standard, well documented |
| **yfinance** | Yahoo Finance (data only) | Free historical data, no API key needed |

---

## 5. Project Structure Explained

```
aiz-trading/
├── .env.example          ← Template for all config values (copy to .env)
├── .gitignore            ← Files excluded from Git (secrets, build artifacts)
├── .github/
│   └── workflows/
│       └── ci.yml        ← GitHub Actions: builds Docker images on push
├── argocd/
│   └── application.yaml  ← ArgoCD: auto-deploys from Git to K8s
├── backend/              ← FastAPI Python backend
│   ├── Dockerfile        ← How to build the backend container
│   ├── requirements.txt  ← Python dependencies
│   └── app/
│       ├── main.py       ← App entry point, middleware, router registration
│       ├── config.py     ← All config from .env, type-safe
│       ├── database.py   ← Async DB connection + session management
│       ├── models/       ← SQLAlchemy DB models (tables)
│       │   ├── user.py   ← User, roles, MFA
│       │   └── trade.py  ← Trade, Position tables
│       ├── routers/      ← API endpoints (one file per domain)
│       │   ├── auth.py       ← /api/auth/* (login, users)
│       │   ├── trading.py    ← /api/trading/* (orders, positions, history)
│       │   ├── market.py     ← /api/market/* (quotes, OHLCV)
│       │   ├── portfolio.py  ← /api/portfolio/* (summary, P&L chart)
│       │   ├── users.py      ← /api/users/* (admin: manage users)
│       │   └── websocket.py  ← /ws/live (real-time market data stream)
│       ├── services/
│       │   └── broker/   ← Broker integrations (pluggable)
│       │       ├── base.py        ← Abstract interface all brokers implement
│       │       ├── paper_trader.py← Default: simulated trading, yfinance data
│       │       ├── angelone.py    ← AngelOne SmartAPI integration
│       │       └── zerodha.py     ← Zerodha Kite Connect integration
│       └── core/
│           ├── security.py  ← JWT, password hashing, role-based auth
│           └── startup.py   ← Creates admin user on first boot
├── ml-engine/            ← Python trading bot + ML models
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py       ← Entry point: runs trading loop + scheduler
│       ├── data/
│       │   ├── fetcher.py  ← Downloads historical + live data (yfinance)
│       │   └── features.py ← 24 technical indicators (feature engineering)
│       ├── models/
│       │   ├── xgboost_model.py  ← Primary ML model (train + predict)
│       │   └── lstm_model.py     ← Optional deep learning model
│       └── trading/
│           ├── signal_generator.py ← Generates BUY/SELL/HOLD signals
│           ├── risk_manager.py     ← Validates trades, position sizing
│           └── executor.py         ← Places approved orders via backend
├── frontend/             ← React + TypeScript web app
│   ├── Dockerfile        ← Multi-stage: build + nginx serve
│   ├── nginx.conf        ← Nginx config: SPA routing, API proxy
│   ├── index.html        ← HTML entry point
│   ├── package.json      ← npm dependencies
│   ├── vite.config.ts    ← Build config + dev proxy
│   ├── tailwind.config.js← Design tokens (colors, fonts, animations)
│   └── src/
│       ├── main.tsx      ← React app bootstrap
│       ├── App.tsx       ← Routes definition
│       ├── index.css     ← Global styles + TailwindCSS
│       ├── pages/        ← Full-page components
│       │   ├── Login.tsx     ← Login page with neural background
│       │   ├── Dashboard.tsx ← Main dashboard (stats, positions, trades)
│       │   ├── Markets.tsx   ← Live charts with AI overlay
│       │   ├── TradeHistory.tsx ← Complete trade log
│       │   ├── AIEngine.tsx  ← Model performance, retrain controls
│       │   ├── Settings.tsx  ← Config: broker, risk, watchlist
│       │   └── Users.tsx     ← Admin: user management
│       ├── components/   ← Reusable UI components
│       │   ├── Layout.tsx    ← Sidebar + topbar shell
│       │   ├── TickerTape.tsx← Scrolling stock ticker at top
│       │   └── LiveClock.tsx ← IST clock updating every second
│       ├── store/
│       │   └── auth.ts   ← Zustand: stores JWT token, username, role
│       └── lib/
│           └── api.ts    ← All API calls + Axios interceptors
├── helm/
│   └── aiz/              ← Helm chart: deploys everything to K8s
│       ├── Chart.yaml    ← Chart metadata
│       ├── values.yaml   ← Default config (override per environment)
│       └── templates/    ← K8s manifest templates
│           ├── backend.yaml     ← Backend Deployment + Service
│           ├── frontend.yaml    ← Frontend Deployment + Service + Ingress
│           ├── postgresql.yaml  ← PostgreSQL StatefulSet + Service
│           └── configmap.yaml   ← Namespace + ConfigMap + Secrets
├── scripts/
│   ├── bootstrap.sh       ← Full install on Ubuntu: K3s + all services
│   ├── add-node.sh        ← Add second machine to K3s cluster
│   └── windows-setup.ps1  ← Windows: install WSL2, kubectl, helm
└── docs/
    └── MASTER.md          ← This file
```

---

## 6. How This Project Was Created

This project was designed and generated in 2026 as an AI-assisted development project.

**Design Philosophy:**
- Broker-agnostic: new brokers added by implementing one interface class
- Environment-driven: all config in `.env`, no hardcoded values
- GitOps: entire deployment state lives in Git
- Security-first: JWT auth, bcrypt passwords, HTTPS-only, K8s network policies
- Cost-zero: every component is open source or has a free tier

**Technology choices rationale:**
- FastAPI over Django: async-native, 3x faster, auto-generates API docs
- XGBoost over simple moving averages: learned patterns vs rule-based
- K3s over full K8s: identical API but runs in 512MB vs 2GB+ RAM
- TimescaleDB over plain PostgreSQL: 10-100x faster time-series queries
- DuckDNS over paid domain: free, reliable, programmatically updatable

---

## 7. Windows Machine Setup

### Prerequisites
- Windows 10/11 with admin rights
- 16GB RAM (minimum 8GB)
- 50GB free disk space

### Step 1: Enable WSL2 + Install Ubuntu
Open PowerShell as Administrator:
```powershell
# Enable WSL2
wsl --install -d Ubuntu-22.04

# Restart your computer when prompted
```
After restart, Ubuntu will open automatically. Create a username + password.

### Step 2: Inside Ubuntu (WSL2)
```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install tools
sudo apt install -y curl git wget nano unzip

# Install Docker (inside WSL2)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Verify
docker --version
```

### Step 3: Clone and configure the project
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/aiz-trading
cd aiz-trading
cp .env.example .env
nano .env   # Fill in your values (see sections 8-9 below)
```

### Step 4: Run the bootstrap script
```bash
sudo bash scripts/bootstrap.sh
```
This takes 10-15 minutes and sets up everything automatically.

### Step 5: Access the dashboard
Open your browser and go to: `https://aiz-trade.duckdns.org`  
Login with the username/password you set in `.env`

---

## 8. AngelOne SmartAPI Setup

**Time required:** 10 minutes  
**Cost:** Free  
**What you get:** API key for live market data + order placement

### Step 1: Open AngelOne Account
1. Go to: https://www.angelone.in
2. Click "Open Free Account"
3. Fill in: PAN card number, Aadhaar number, bank account details
4. Complete e-sign (digital signature via Aadhaar OTP)
5. Account activated within same day or next business day

### Step 2: Get SmartAPI Key
1. Go to: https://smartapi.angelone.in
2. Login with your AngelOne credentials
3. Click "Create New App"
4. Fill in:
   - App Name: `AIZ Trading Bot`
   - App Type: `Trading`
   - Redirect URL: `http://localhost`
5. Click "Submit"
6. You will see:
   - `API Key` — copy this
   - `Client ID` — this is your AngelOne login ID

### Step 3: Set up TOTP (Time-based OTP)
AngelOne uses TOTP for API authentication (same as Google Authenticator).
1. In the SmartAPI portal, find "TOTP Secret" or generate it
2. Install Google Authenticator on your phone
3. Add account → Enter TOTP secret manually
4. This generates a 6-digit code every 30 seconds

### Step 4: Add to .env
```bash
ACTIVE_BROKER=angelone
ANGEL_API_KEY=your-api-key-here
ANGEL_CLIENT_ID=your-client-id-here
ANGEL_PASSWORD=your-trading-password-here
ANGEL_TOTP_SECRET=your-totp-secret-here
```

### Step 5: Test connection
```bash
# In WSL2
cd aiz-trading
python -c "
from SmartApi import SmartConnect
import pyotp
api = SmartConnect(api_key='YOUR_KEY')
totp = pyotp.TOTP('YOUR_TOTP_SECRET').now()
session = api.generateSession('YOUR_CLIENT_ID', 'YOUR_PASSWORD', totp)
print('Connected!' if session['status'] else 'Failed:', session)
"
```

---

## 9. DuckDNS Free Domain Setup

**Time required:** 5 minutes  
**Cost:** Free forever  
**Result:** `https://aiz-trade.duckdns.org`

### Step 1: Create DuckDNS account
1. Go to: https://www.duckdns.org
2. Click "Sign in with Google" (or GitHub)
3. No credit card, no email verification needed

### Step 2: Register your subdomain
1. In the "Sub Domain" box, type: `aiz-trade`
2. Click "Add Domain"
3. Your URL is now: `https://aiz-trade.duckdns.org`

### Step 3: Get your token
- After login, your token is displayed at the top of the page
- It looks like: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### Step 4: Add to .env
```bash
DUCKDNS_TOKEN=your-token-here
DUCKDNS_DOMAIN=aiz-trade
```

### How auto-update works
The bootstrap script creates a Kubernetes CronJob that runs every 5 minutes:
```
curl "https://www.duckdns.org/update?domains=aiz-trade&token=YOUR_TOKEN&ip="
```
This automatically updates DuckDNS with your current IP, so even if your
internet IP changes, `aiz-trade.duckdns.org` always points to your machine.

---

## 10. Web Access Setup (No Cloudflare Needed)

> **Note:** Cloudflare Tunnel requires your domain to be managed on Cloudflare's
> nameservers. Since `duckdns.org` is DuckDNS's own domain, Cloudflare Tunnel
> does not work here. Use one of the two free options below instead.

---

### Option A: Router Port Forwarding + DuckDNS (Recommended)

**Time required:** 10 minutes  
**Cost:** Free  
**Result:** `https://aiz-trade.duckdns.org` accessible from any device, anywhere

**How it works:**
```
Any browser anywhere
        ↓ HTTPS (port 443)
Your Router (port forwarding rule)
        ↓
Your Laptop (K3s + Traefik on port 443)
        ↓
AI Z Dashboard
```

#### Step 1: Find your laptop's local IP
In WSL2 Ubuntu:
```bash
hostname -I | awk '{print $1}'
# Example output: 192.168.1.105
```

#### Step 2: Set up port forwarding on your router
1. Open browser → go to your router admin page:
   - Try `http://192.168.1.1` or `http://192.168.0.1`
   - Login credentials are usually on a sticker on your router
   - Common brands: TP-Link → `tplinkwifi.net`, Jio → `http://192.168.29.1`

2. Find **Port Forwarding** (also called "Virtual Server" or "NAT Forwarding")

3. Add these two rules:

| Name | External Port | Internal IP | Internal Port | Protocol |
|---|---|---|---|---|
| AIZ-HTTPS | 443 | `192.168.1.105` (your laptop IP) | 443 | TCP |
| AIZ-HTTP | 80 | `192.168.1.105` (your laptop IP) | 80 | TCP |

4. Save and apply.

#### Step 3: Assign a static local IP to your laptop (optional but recommended)
Without this, your laptop's local IP may change after restart.

In router admin → **DHCP Reservations** (or "Address Reservation"):
- Add your laptop's MAC address → assign fixed IP `192.168.1.105`

To find your MAC address in WSL2:
```bash
ip link show eth0 | grep ether | awk '{print $2}'
```

#### Step 4: Test it
```bash
# From any other device (phone, another laptop):
curl -I https://aiz-trade.duckdns.org
# Should return: HTTP/2 200
```

#### What if my ISP blocks port 80/443?
Some ISPs (especially mobile broadband like Jio, Airtel 4G) block incoming
connections on ports 80/443. If port forwarding doesn't work, use Option B below.

---

### Option B: Tailscale VPN (No Port Forwarding Needed — Free)

**Time required:** 10 minutes  
**Cost:** Free (up to 3 users/devices)  
**Result:** Access AI Z from any device that has Tailscale installed  
**Limitation:** Not publicly accessible — only VPN-connected devices can reach it

**How it works:**
```
Your phone/laptop (Tailscale installed)
        ↓ Encrypted VPN tunnel (outbound from both sides)
Tailscale coordination server (just passes keys)
        ↓
Your AI Z laptop (Tailscale installed)
        ↓
AI Z Dashboard
```

No router config, no port forwarding, works behind any NAT or firewall.

#### Step 1: Install Tailscale on your AI Z laptop (WSL2 Ubuntu)
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Opens a URL in terminal → open it in browser → sign in with Google/GitHub
```

#### Step 2: Get your Tailscale IP
```bash
tailscale ip -4
# Example: 100.64.0.1
```

#### Step 3: Install Tailscale on every device you want access from
- iPhone/Android: App Store / Play Store → "Tailscale" → sign in with same account
- Another laptop: https://tailscale.com/download → install → sign in

#### Step 4: Access AI Z
On any Tailscale-connected device:
```
http://100.64.0.1        ← HTTP (use your actual Tailscale IP)
```

Or use Tailscale MagicDNS (auto hostname):
```
http://your-laptop-name  ← if MagicDNS enabled in Tailscale admin panel
```

#### Enable Tailscale auto-start
```bash
sudo systemctl enable --now tailscaled
```

#### Adding more users (up to 3 free):
- Share your node in Tailscale admin panel → invite their email
- They install Tailscale → connect → can access your AI Z

---

### Which Option Should I Choose?

| Situation | Recommendation |
|---|---|
| Home broadband (Jio Fiber, Airtel, BSNL) | **Option A** (port forwarding) |
| Mobile hotspot / 4G router | **Option B** (Tailscale) |
| Office/corporate network | **Option B** (Tailscale) |
| Want public access for all users | **Option A** |
| Private access for yourself + 2 others | **Option B** |
| Both — public + private | Option A for public + Option B as backup |

---

### Verify K3s is listening on ports 80/443
After bootstrap, verify Traefik is binding correctly:
```bash
sudo ss -tlnp | grep -E ':80|:443'
# Should show: LISTEN on 0.0.0.0:80 and 0.0.0.0:443
```

If not:
```bash
# K3s Traefik by default uses NodePort 30080/30443
# Force host network binding:
kubectl patch svc traefik -n kube-system \
  -p '{"spec":{"externalIPs":["YOUR_LOCAL_IP"]}}'
```

---

## 11. Deploying the Full Application

### First deployment
```bash
# In WSL2 Ubuntu, inside the project directory:
cp .env.example .env
nano .env           # Fill in all values
sudo bash scripts/bootstrap.sh
```

### Re-deploying after code changes
```bash
# Push to GitHub → GitHub Actions builds new Docker images → ArgoCD auto-deploys
git add .
git commit -m "update: my changes"
git push origin main
# ArgoCD detects the new images and rolls them out automatically
# Usually takes 2-3 minutes
```

### Manual redeploy
```bash
helm upgrade aiz ./helm/aiz -n aiz
```

### Check status
```bash
kubectl get pods -n aiz
kubectl get pods -n monitoring
kubectl logs -n aiz deployment/aiz-backend -f
```

---

## 12. User Management

### User Roles
| Role | Dashboard | Trade History | Bot Control | Settings | User Management |
|---|---|---|---|---|---|
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Analyst** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Viewer** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Guest** | Read-only | ❌ | ❌ | ❌ | ❌ |

### Creating a new user (via API)
```bash
# Get admin token first
TOKEN=$(curl -s -X POST https://aiz-trade.duckdns.org/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"YOUR_ADMIN_PASSWORD"}' | jq -r .access_token)

# Create viewer user
curl -X POST https://aiz-trade.duckdns.org/api/auth/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"friend1","email":"friend@example.com","password":"SecurePass123!","role":"viewer"}'
```

### Each user has their own:
- Username + password (they set their own)
- Login session (JWT token, expires in 60 minutes)
- Their own broker API key configuration (optional, in Settings)
- Their own trade history (users cannot see other users' data)
- MFA (optional — each user configures independently)

---

## 13. Security Architecture

### What protects AI Z from hackers

| Layer | Protection | How |
|---|---|---|
| **HTTPS only** | All traffic encrypted | cert-manager + Let's Encrypt TLS |
| **JWT Tokens** | Stateless auth, expires in 60 min | python-jose library |
| **bcrypt** | Password hashing (one-way) | passlib, cost factor 12 |
| **Rate limiting** | Blocks brute force | Traefik middleware: 5 req/min on /api/auth |
| **Input validation** | SQL injection, XSS prevention | Pydantic v2 validates all inputs |
| **ORM queries** | No raw SQL | SQLAlchemy parameterized queries |
| **CORS** | Only your domain can call the API | FastAPI CORS middleware |
| **K8s Network Policies** | Services isolated from each other | Only allowed connections work |
| **Non-root containers** | Exploit impact limited | All Dockerfiles use non-root users |
| **Security headers** | XSS, clickjacking prevention | Nginx headers |
| **Secrets management** | No hardcoded secrets | K8s Secrets, never in code or Git |

### Do NOT do these things:
- Do NOT commit `.env` to Git (it's in `.gitignore`)
- Do NOT share your JWT token with anyone
- Do NOT enable the API docs in production (`docs_url=None` in main.py)
- Do NOT use `TRADING_MODE=live` until you've tested paper trading for weeks

---

## 14. Switching to Live Trading

**WARNING: Only do this after extensive paper trading testing.**

### Step 1: Verify paper trading results
- Run paper trading for at least 2-4 weeks
- Win rate should be consistently above 60%
- Sharpe ratio should be above 1.5
- Maximum drawdown should be below 5%

### Step 2: Configure your broker
For AngelOne:
```bash
# In .env:
ACTIVE_BROKER=angelone
TRADING_MODE=live    # Change from 'paper' to 'live'
TRADING_CAPITAL=10000  # Start with small capital (₹10,000)
MAX_RISK_PER_TRADE=1   # Reduce risk to 1% for live trading
```

### Step 3: Redeploy
```bash
helm upgrade aiz ./helm/aiz -n aiz
```

### Step 4: Monitor closely
- Watch the Grafana dashboard for first 3 days
- Set Telegram alerts for every trade
- Keep daily loss limit at 3% initially

---

## 15. Adding a Second Machine

### Get the K3s node token from your main machine
```bash
sudo cat /var/lib/rancher/k3s/server/node-token
```
Copy the token output.

### On the NEW machine (Ubuntu 22.04)
```bash
# Set variables
export K3S_SERVER_IP=192.168.1.100   # Your main machine's local IP
export K3S_TOKEN=your-token-from-above

# Join the cluster
curl -sfL https://get.k3s.io | \
  K3S_URL="https://${K3S_SERVER_IP}:6443" \
  K3S_TOKEN="${K3S_TOKEN}" sh -
```

### Verify on main machine
```bash
kubectl get nodes
# Should show 2 nodes: Ready
```

K8s will now automatically distribute pods across both machines.
If one machine goes down, the other continues running the application.

---

## 16. Monitoring

### Access Grafana dashboard
```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80
# Open: http://localhost:3001
# Login: admin / (GRAFANA_ADMIN_PASSWORD from .env)
```

### Pre-built dashboards:
- **Trading Performance**: Win rate, P&L over time, trade frequency
- **AI Model**: Prediction confidence distribution, model accuracy
- **System Health**: CPU, RAM, disk usage per pod
- **K8s Overview**: Node status, pod restarts, resource usage
- **API Performance**: Request rate, latency, error rate

### Alerts configured:
- Bot stopped trading during market hours
- Daily loss limit approaching
- Pod crash (auto-restart + notification)
- Disk space > 80%
- Model accuracy drops below 60%

---

## 17. Backup & Recovery

### Automatic daily backups (runs at 2 AM)
```bash
# Backup PostgreSQL
kubectl exec -n aiz postgresql-0 -- \
  pg_dump -U aiz_user aiz_trading | gzip > backup-$(date +%Y%m%d).sql.gz

# Copy to local machine
kubectl cp aiz/postgresql-0:/tmp/backup.sql.gz ./backups/
```

### Restore from backup
```bash
# Restore to a new PostgreSQL instance
kubectl exec -i -n aiz postgresql-0 -- \
  psql -U aiz_user aiz_trading < backup.sql
```

### What's in a backup:
- All trades (history)
- All positions
- All users
- Portfolio history
- ML model files (separate)

---

## 18. Moving to Another Machine

### Complete migration in 5 steps:

**Step 1: On old machine — backup database**
```bash
kubectl exec -n aiz postgresql-0 -- \
  pg_dump -U aiz_user aiz_trading > aiz-backup.sql
```

**Step 2: Copy files to new machine**
```bash
# Copy the project (or just git clone from GitHub)
scp -r aiz-trading user@new-machine:~/
scp aiz-backup.sql user@new-machine:~/
```

**Step 3: On new machine — run bootstrap**
```bash
cd aiz-trading
cp .env.example .env
nano .env  # Fill in same values as old machine
sudo bash scripts/bootstrap.sh
```

**Step 4: Restore database**
```bash
# Wait for PostgreSQL to be ready, then:
kubectl exec -i -n aiz postgresql-0 -- \
  psql -U aiz_user aiz_trading < aiz-backup.sql
```

**Step 5: Update DuckDNS**
- DuckDNS auto-updater runs every 5 minutes
- It will automatically update to the new machine's IP
- `aiz-trade.duckdns.org` will point to new machine within 5 minutes

**Total migration time: ~30 minutes**

---

## 19. Adding New Brokers

To add a new broker (e.g., Upstox, 5paisa, Fyers):

### Step 1: Create broker file
```python
# backend/app/services/broker/upstox.py
from app.services.broker.base import BrokerBase, OrderResult, Quote

class UpstoxBroker(BrokerBase):
    async def connect(self): ...
    async def get_quote(self, symbol): ...
    async def place_order(self, ...): ...
    async def cancel_order(self, order_id): ...
    async def get_positions(self): ...
    async def get_balance(self): ...
    async def is_market_open(self): ...
```

### Step 2: Register in factory
```python
# backend/app/services/broker/__init__.py
elif broker_name == "upstox":
    from app.services.broker.upstox import UpstoxBroker
    return UpstoxBroker()
```

### Step 3: Add config to .env
```bash
ACTIVE_BROKER=upstox
UPSTOX_API_KEY=...
UPSTOX_ACCESS_TOKEN=...
```

No other code changes needed.

---

## 20. Adding New ML Models

### Step 1: Create model file
```python
# ml-engine/src/models/my_model.py
class MyTradingModel:
    def train(self, df): ...
    def predict(self, features) -> dict:
        # Must return: {"signal": "BUY/SELL/HOLD", "confidence": int, "proba": float}
```

### Step 2: Register in signal generator
```python
# ml-engine/src/trading/signal_generator.py
if os.getenv("ML_MODEL") == "my_model":
    from src.models.my_model import MyTradingModel
    model = MyTradingModel()
```

### Step 3: Switch via .env
```bash
ML_MODEL=my_model
```

### Ideas for new models:
- **LSTM**: Add time-sequence awareness (already in lstm_model.py)
- **Ensemble**: Combine XGBoost + LSTM predictions
- **Sentiment**: Add news sentiment from NewsAPI (free tier)
- **Options Greeks**: Add delta/theta/gamma for F&O trading

---

## 21. Upgrading to Custom Domain

When you buy a domain (e.g., `tradepower.com` on Namecheap/GoDaddy, ~₹800/year):

### Step 1: Add DNS record
In your domain registrar's DNS panel:
```
Type: CNAME
Name: aiz
Value: aiz-trade.duckdns.org
TTL: 300
```
This makes `aiz.tradepower.com` point to `aiz-trade.duckdns.org` which points to your machine.

### Step 2: Update .env and Helm values
```bash
# .env
DOMAIN=aiz.tradepower.com

# helm/aiz/values.yaml
global:
  domain: aiz.tradepower.com
```

### Step 3: Redeploy
```bash
helm upgrade aiz ./helm/aiz -n aiz
```

cert-manager automatically requests a new Let's Encrypt certificate for the new domain.

---

## 22. Troubleshooting

### Bot not trading
```bash
# Check ml-engine logs
kubectl logs -n aiz deployment/aiz-ml-engine -f
# Common issues:
# - Market closed (weekends/holidays)
# - No model found: wait for initial training to complete (30-60 min)
# - AngelOne session expired: restart ml-engine pod
```

### Can't access dashboard
```bash
# Check all pods are running
kubectl get pods -n aiz
# Check ingress
kubectl describe ingress aiz-ingress -n aiz
# Check certificate
kubectl get certificate -n aiz
```

### Database connection errors
```bash
# Check PostgreSQL pod
kubectl logs -n aiz postgresql-0
# Restart backend
kubectl rollout restart deployment/aiz-backend -n aiz
```

### DuckDNS not updating
```bash
# Manually trigger update
kubectl create job --from=cronjob/duckdns-updater manual-update -n aiz
```

### Out of disk space
```bash
# Check disk usage
df -h
# Clean old Docker images
docker image prune -a
```

---

## 23. Glossary

| Term | Definition |
|---|---|
| **OHLCV** | Open, High, Low, Close, Volume — the 5 core data points for every time period |
| **Intraday** | Trades opened and closed within the same trading day |
| **NSE** | National Stock Exchange of India |
| **Nifty 50** | Index of the 50 largest companies listed on NSE |
| **RSI** | Relative Strength Index — momentum indicator (0-100), >70 overbought, <30 oversold |
| **MACD** | Moving Average Convergence Divergence — trend-following momentum indicator |
| **EMA** | Exponential Moving Average — gives more weight to recent prices |
| **Bollinger Bands** | Volatility bands around a moving average |
| **Stop-loss** | Automatic exit price to limit losses on a trade |
| **Paper trading** | Simulated trading with fake money to test strategies safely |
| **Live trading** | Real trading with actual money |
| **XGBoost** | Extreme Gradient Boosting — an ensemble ML algorithm, best for tabular data |
| **LSTM** | Long Short-Term Memory — a type of neural network that handles sequences |
| **Feature engineering** | Converting raw data into ML-ready numeric inputs |
| **Overfitting** | Model memorizes training data, fails on new data |
| **TimeSeriesSplit** | Cross-validation method that prevents future data leaking into training |
| **Sharpe Ratio** | Risk-adjusted return. >1 is good, >2 is excellent |
| **Drawdown** | Peak-to-trough loss. Max drawdown = worst loss period |
| **K8s / Kubernetes** | Container orchestration system — runs, scales, heals containers automatically |
| **K3s** | Lightweight Kubernetes — same API, 4x less memory usage |
| **Pod** | Smallest unit in Kubernetes — one or more containers running together |
| **Helm** | Package manager for Kubernetes — deploys complex apps with one command |
| **ArgoCD** | GitOps tool — watches your Git repo and keeps K8s in sync with it |
| **GitOps** | Using Git as the single source of truth for your infrastructure |
| **JWT** | JSON Web Token — signed token for stateless authentication |
| **bcrypt** | Password hashing algorithm — one-way, cannot be reversed |
| **TLS/SSL** | Transport Layer Security — encrypts all network traffic (HTTPS) |
| **cert-manager** | K8s controller that auto-manages SSL certificates |
| **Ingress** | K8s resource that routes external HTTP/HTTPS traffic to services |
| **DuckDNS** | Free dynamic DNS service |
| **Dynamic DNS** | Automatically updates DNS record when your IP changes |
| **Cloudflare Tunnel** | Secure tunnel from your machine to Cloudflare's edge (no port forwarding) |
| **WebSocket** | Persistent two-way connection for real-time data streaming |
| **TimescaleDB** | PostgreSQL extension optimized for time-series data |
| **MLflow** | ML experiment tracking — logs model versions, accuracy, parameters |
| **Prometheus** | Metrics collection and alerting system |
| **Grafana** | Dashboard and visualization for metrics |
| **CORS** | Cross-Origin Resource Sharing — controls which domains can call your API |
| **ORM** | Object Relational Mapper — maps Python classes to database tables |
| **SaaS** | Software as a Service — web app with paying subscribers |
| **HA** | High Availability — system stays up even if one component fails |
