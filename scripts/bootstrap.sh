#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Z — Bootstrap Script
# Installs everything on a fresh Ubuntu 22.04 machine in one command.
#
# Usage:
#   chmod +x scripts/bootstrap.sh
#   ./scripts/bootstrap.sh
#
# What this does:
#   1. Installs K3s (lightweight Kubernetes)
#   2. Installs Helm, kubectl, ArgoCD CLI
#   3. Installs cert-manager (free SSL)
#   4. Deploys all AI Z services via Helm
#   5. Sets up Cloudflare Tunnel for web access
#   6. Configures DuckDNS auto-updater
# ══════════════════════════════════════════════════════════════════════════════
set -e

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()   { echo -e "${GREEN}[AIZ]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Mode flag ────────────────────────────────────────────────────────────────
# Usage:
#   sudo bash scripts/bootstrap.sh              → full deploy with domain
#   sudo bash scripts/bootstrap.sh --localhost  → local-only, no SSL, no domain
LOCALHOST_MODE=false
[[ "$*" == *"--localhost"* ]] && LOCALHOST_MODE=true
HELM_VALUES="./helm/aiz/values.yaml"
$LOCALHOST_MODE && HELM_VALUES="./helm/aiz/values.localhost.yaml" && log "Running in LOCALHOST mode (no SSL, no domain required)"

# ── Check requirements ────────────────────────────────────────────────────────
[ "$EUID" -ne 0 ] && error "Run as root: sudo ./scripts/bootstrap.sh"
[ -f ".env" ] || error ".env file not found. Copy .env.example to .env and fill in values."

log "Loading environment..."
# Safe .env loader — handles empty values, spaces, and special characters
while IFS='=' read -r key value || [ -n "$key" ]; do
    [[ "$key" =~ ^[[:space:]]*#.*$ ]] && continue   # skip comments
    [[ -z "${key// }" ]] && continue                  # skip blank lines
    key="${key// /}"                                   # trim spaces from key
    [[ "$key" =~ [^a-zA-Z0-9_] ]] && continue         # skip invalid keys
    export "$key=$value"
done < .env

# ── 1. Install K3s ────────────────────────────────────────────────────────────
log "Installing K3s (lightweight Kubernetes)..."
if ! command -v k3s &>/dev/null; then
    curl -sfL https://get.k3s.io | sh -
    mkdir -p ~/.kube
    cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
    chmod 600 ~/.kube/config
    log "K3s installed. Waiting for it to start..."
    sleep 30
else
    log "K3s already installed."
fi

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# ── 2. Install Helm ───────────────────────────────────────────────────────────
log "Installing Helm..."
if ! command -v helm &>/dev/null; then
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
else
    log "Helm already installed."
fi

# ── 3. Install cert-manager (free SSL) ───────────────────────────────────────
if ! $LOCALHOST_MODE; then
    log "Installing cert-manager for free Let's Encrypt SSL..."
    helm repo add jetstack https://charts.jetstack.io --force-update
    helm upgrade --install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --create-namespace \
        --set installCRDs=true \
        --wait

# ── 4. Create Let's Encrypt ClusterIssuer ────────────────────────────────────
    cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ${ADMIN_EMAIL}
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: traefik
EOF
else
    log "Skipping cert-manager (localhost mode — no SSL needed)."
fi

# ── 5. Create aiz namespace + secrets ────────────────────────────────────────
log "Creating namespace and secrets..."
kubectl create namespace aiz --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic aiz-secrets \
    --namespace aiz \
    --from-literal=SECRET_KEY="${SECRET_KEY}" \
    --from-literal=JWT_SECRET="${JWT_SECRET}" \
    --from-literal=POSTGRES_DB="${POSTGRES_DB}" \
    --from-literal=POSTGRES_USER="${POSTGRES_USER}" \
    --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
    --from-literal=REDIS_PASSWORD="${REDIS_PASSWORD}" \
    --from-literal=ADMIN_USERNAME="${ADMIN_USERNAME}" \
    --from-literal=ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
    --from-literal=ADMIN_EMAIL="${ADMIN_EMAIL}" \
    --from-literal=ANGEL_API_KEY="${ANGEL_API_KEY}" \
    --from-literal=ANGEL_CLIENT_ID="${ANGEL_CLIENT_ID}" \
    --from-literal=ANGEL_PASSWORD="${ANGEL_PASSWORD}" \
    --from-literal=ANGEL_TOTP_SECRET="${ANGEL_TOTP_SECRET}" \
    --from-literal=GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD}" \
    --dry-run=client -o yaml | kubectl apply -f -

# ── 6. Install ArgoCD ────────────────────────────────────────────────────────
log "Installing ArgoCD (GitOps CD)..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=120s

# ── 7. Deploy AI Z via Helm ──────────────────────────────────────────────────
log "Deploying AI Z services..."
helm upgrade --install aiz ./helm/aiz \
    --namespace aiz \
    --values "${HELM_VALUES}" \
    --wait \
    --timeout 10m

# ── 8. Install Prometheus + Grafana monitoring ────────────────────────────────
if ! $LOCALHOST_MODE; then
    log "Installing monitoring stack..."
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
    helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set grafana.adminPassword="${GRAFANA_ADMIN_PASSWORD}" \
        --wait
else
    log "Skipping Grafana/Prometheus (localhost mode — enable later with: bash scripts/enable-monitoring.sh)"
fi

# ── 9. Setup DuckDNS auto-updater ────────────────────────────────────────────
log "Setting up DuckDNS auto-updater..."
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: duckdns-updater
  namespace: aiz
spec:
  schedule: "*/5 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: updater
              image: alpine/curl
              command:
                - sh
                - -c
                - |
                  curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip="
          restartPolicy: OnFailure
EOF

# ── 10. Access Setup ─────────────────────────────────────────────────────────
log "Web Access Setup — choose one option:"
echo ""
echo -e "${GREEN}OPTION A (Recommended): Router Port Forwarding + DuckDNS${NC}"
echo "  1. Find your laptop's local IP:"
echo "     hostname -I | awk '{print \$1}'"
echo "  2. Log into your router (usually http://192.168.1.1)"
echo "  3. Go to Port Forwarding → Add two rules:"
echo "     External 443 → YOUR_LAPTOP_IP:443 (TCP)"
echo "     External 80  → YOUR_LAPTOP_IP:80  (TCP)"
echo "  4. Done. https://${DUCKDNS_DOMAIN}.duckdns.org works from anywhere."
echo ""
echo -e "${YELLOW}OPTION B: Tailscale VPN (if port forwarding is not possible)${NC}"
echo "  1. Install: curl -fsSL https://tailscale.com/install.sh | sh"
echo "  2. Connect: sudo tailscale up"
echo "  3. Get your Tailscale IP: tailscale ip -4"
echo "  4. Access AI Z at: http://YOUR_TAILSCALE_IP"
echo "  5. Install Tailscale on any device you want to access from."
echo "  See docs/MASTER.md Section 10 for full instructions."

# ── Done ─────────────────────────────────────────────────────────────────────
log ""
log "════════════════════════════════════════════════════"
log "  AI Z is deployed!"
if $LOCALHOST_MODE; then
    log ""
    log "  Access on this machine:  http://localhost"
    log "  Access on same WiFi:     http://$(hostname -I | awk '{print $1}')"
    log ""
    log "  To enable domain access later:"
    log "    bash scripts/setup-access.sh"
else
    log "  Dashboard: https://${DUCKDNS_DOMAIN}.duckdns.org"
    log "  Grafana:   kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80"
fi
log ""
log "  Default login:"
log "    Username: ${ADMIN_USERNAME}"
log "    Password: (as set in .env ADMIN_PASSWORD)"
log "════════════════════════════════════════════════════"
