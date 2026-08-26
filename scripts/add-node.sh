#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Z — Add Worker Node to K3s Cluster
# Run this on the SECOND/THIRD machine to join it to your cluster.
#
# Prerequisites:
#   - New machine must be Ubuntu 22.04
#   - SSH access from this machine to the new machine
#   - Both machines on same network (or VPN)
#
# Usage (run on the NEW machine, not the main one):
#   K3S_SERVER_IP=<your-main-machine-IP> \
#   K3S_TOKEN=<token-from-main-machine> \
#   ./scripts/add-node.sh
#
# To get the token from your main machine:
#   sudo cat /var/lib/rancher/k3s/server/node-token
# ══════════════════════════════════════════════════════════════════════════════
set -e

K3S_SERVER_IP="${K3S_SERVER_IP:?Set K3S_SERVER_IP to your main machine IP}"
K3S_TOKEN="${K3S_TOKEN:?Set K3S_TOKEN from /var/lib/rancher/k3s/server/node-token on main machine}"
K3S_SERVER_URL="https://${K3S_SERVER_IP}:6443"

echo "Joining cluster at ${K3S_SERVER_URL}..."
curl -sfL https://get.k3s.io | K3S_URL="${K3S_SERVER_URL}" K3S_TOKEN="${K3S_TOKEN}" sh -

echo ""
echo "Node joined successfully!"
echo "Verify on the main machine with: kubectl get nodes"
echo ""
echo "K8s will automatically schedule pods to this new node."
echo "Your cluster is now HA-capable."
