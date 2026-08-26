#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Z — Web Access Setup
# Run this after bootstrap.sh to configure access from outside your network.
#
# Choose ONE option:
#   Option A: Router port forwarding (home broadband)
#   Option B: Tailscale VPN (office/4G/no router access)
# ══════════════════════════════════════════════════════════════════════════════

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  AI Z — Web Access Diagnostic & Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

# ── Show current IPs ──────────────────────────────────────────────────────────
LOCAL_IP=$(hostname -I | awk '{print $1}')
PUBLIC_IP=$(curl -s https://api.ipify.org 2>/dev/null || echo "Could not detect")

echo "Your local IP (router-side):  ${GREEN}${LOCAL_IP}${NC}"
echo "Your public IP (internet):    ${GREEN}${PUBLIC_IP}${NC}"
echo ""

# ── Check if K3s Traefik is listening ────────────────────────────────────────
echo "Checking K3s Traefik ports..."
PORT_80=$(ss -tlnp 2>/dev/null | grep ':80 ' | head -1)
PORT_443=$(ss -tlnp 2>/dev/null | grep ':443 ' | head -1)

if [ -n "$PORT_80" ] && [ -n "$PORT_443" ]; then
    echo -e "  Port 80:  ${GREEN}✓ Listening${NC}"
    echo -e "  Port 443: ${GREEN}✓ Listening${NC}"
else
    echo -e "  ${YELLOW}Traefik not yet on 80/443. Checking NodePort...${NC}"
    kubectl get svc traefik -n kube-system 2>/dev/null
fi
echo ""

# ── Check DuckDNS config ─────────────────────────────────────────────────────
if [ -f ".env" ]; then
    source <(grep -v '^#' .env | grep -E 'DUCKDNS')
    if [ -n "$DUCKDNS_DOMAIN" ] && [ -n "$DUCKDNS_TOKEN" ]; then
        echo "Updating DuckDNS now..."
        RESULT=$(curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=")
        echo -e "  DuckDNS: ${GREEN}${RESULT}${NC}"
        echo "  URL: https://${DUCKDNS_DOMAIN}.duckdns.org → ${PUBLIC_IP}"
    fi
fi
echo ""

# ── Instructions ─────────────────────────────────────────────────────────────
echo -e "${GREEN}OPTION A — Router Port Forwarding (for home broadband):${NC}"
echo "  1. Open your router admin: http://192.168.1.1 (or check label on router)"
echo "  2. Go to: Port Forwarding → Add rules:"
echo "     External 443 → ${LOCAL_IP}:443"
echo "     External 80  → ${LOCAL_IP}:80"
echo "  3. Save. Test: curl -I https://${DUCKDNS_DOMAIN:-aiz-trade}.duckdns.org"
echo ""
echo -e "${YELLOW}OPTION B — Tailscale VPN (no router config needed):${NC}"
echo "  1. Install: curl -fsSL https://tailscale.com/install.sh | sh"
echo "  2. Connect: sudo tailscale up"
echo "  3. Get IP:  tailscale ip -4"
echo "  4. Access:  http://YOUR_TAILSCALE_IP (from any Tailscale device)"
echo ""
echo "See docs/MASTER.md Section 10 for full details."
