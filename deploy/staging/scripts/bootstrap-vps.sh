#!/usr/bin/env bash
# Bootstrap an Ubuntu LTS VPS for Karzar staging (Docker, firewall, Nginx, Certbot).
# Run as root or with sudo:  sudo bash deploy/staging/scripts/bootstrap-vps.sh
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y ca-certificates curl gnupg ufw nginx certbot python3-certbot-nginx git

# Docker Engine (official)
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  # shellcheck disable=SC1091
  . /etc/os-release
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

systemctl enable --now docker
systemctl enable --now nginx

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

mkdir -p /var/www/certbot
mkdir -p /opt/karzar

echo
echo "Bootstrap complete."
echo "Next:"
echo "  1) Point DNS A records for api/shop/admin to this server IP"
echo "  2) Clone backend into /opt/karzar/Karzar"
echo "  3) Follow deploy/staging/STAGING_DEPLOY.md"
