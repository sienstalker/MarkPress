#!/usr/bin/env bash
# One-time server setup for MarkPress on a Debian 13 or Ubuntu 24.04 EC2 instance.
# Installs Java + Jenkins, Python, Nginx and prepares the web root.
# Usage (from the repo root on the server):  bash deploy/setup_ec2.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Jenkins needs ~1 GB of RAM by itself. On a 1 GB instance (t2/t3.micro) add swap.
MEM_MB=$(free -m | awk '/^Mem:/ {print $2}')
if [ "$MEM_MB" -lt 1800 ] && [ ! -f /swapfile ]; then
    echo "Only ${MEM_MB} MB RAM: adding a 2 GB swap file so Jenkins doesn't crash..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
fi

echo "Installing Java 21, Python, Nginx, rsync, curl and git..."
sudo apt-get update
sudo apt-get install -y fontconfig openjdk-21-jre python3 python3-venv python3-pip \
    nginx rsync curl git

echo "Installing Jenkins (LTS)..."
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key \
    | sudo tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" \
    | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null
sudo apt-get update
sudo apt-get install -y jenkins

# Debian keeps /tmp in RAM (often under 1 GB), and Jenkins takes its build node
# offline when its temp folder has less than 1 GB free. Use a folder on disk instead.
echo "Giving Jenkins a temp folder on disk..."
sudo mkdir -p /var/lib/jenkins/tmp
sudo chown jenkins:jenkins /var/lib/jenkins/tmp
sudo mkdir -p /etc/systemd/system/jenkins.service.d
printf '[Service]\nEnvironment="JAVA_OPTS=-Djava.awt.headless=true -Djava.io.tmpdir=/var/lib/jenkins/tmp"\n' \
    | sudo tee /etc/systemd/system/jenkins.service.d/override.conf > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable jenkins
sudo systemctl restart jenkins

echo "Creating the web root and giving it to the jenkins user..."
sudo mkdir -p /var/www/markpress
sudo chown -R jenkins:jenkins /var/www/markpress
sudo chmod 755 /var/www/markpress

echo "Configuring Nginx (serves the site and forwards the GitHub webhook to Jenkins)..."
sudo cp "$SCRIPT_DIR/nginx-markpress.conf" /etc/nginx/sites-available/markpress
sudo ln -sf /etc/nginx/sites-available/markpress /etc/nginx/sites-enabled/markpress
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

echo
echo "Setup complete."
echo "  Site:     http://<EC2-public-IP>/  (empty until the first pipeline run)"
echo "  Jenkins:  open an SSH tunnel, then visit http://localhost:8080"
echo "            ssh -i your-key.pem -L 8080:localhost:8080 <user>@<EC2-public-IP>"
echo "  Initial Jenkins admin password:"
sudo cat /var/lib/jenkins/secrets/initialAdminPassword \
    || echo "  (not ready yet; run: sudo cat /var/lib/jenkins/secrets/initialAdminPassword)"
