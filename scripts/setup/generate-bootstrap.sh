#!/bin/bash
# TRAE: Regenerates bootstrap.sh for AI Video Renderer

echo "[TRAE] 🔁 Regenerating bootstrap.sh..."

cat << 'INNER_EOF' > bootstrap.sh
#!/bin/bash
set -e

# === Logging ===
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()   { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn()  { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"; exit 1; }

# === Safety ===
if [[ $EUID -eq 0 ]]; then error "Don't run as root"; fi

# === Update System ===
log "Updating system..."
sudo apt-get update -y && sudo apt-get upgrade -y

# === Core Packages ===
log "Installing packages..."
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release \
    software-properties-common unzip wget git python3 python3-pip htop nano ufw

# === Docker ===
log "Installing Docker..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list
  sudo apt-get update -y && sudo apt-get install -y docker-ce docker-ce-cli containerd.io
  sudo usermod -aG docker $USER
  sudo systemctl enable docker && sudo systemctl start docker
else log "Docker already installed"; fi

# === Docker Compose ===
log "Installing Docker Compose..."
if ! command -v docker-compose &>/dev/null; then
  VER=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d '"' -f4)
  sudo curl -L "https://github.com/docker/compose/releases/download/${VER}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
  sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
else log "Docker Compose already installed"; fi

# === gCloud SDK ===
log "Installing Google Cloud SDK..."
if ! command -v gcloud &>/dev/null; then
  echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
  curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
  sudo apt-get update -y && sudo apt-get install -y google-cloud-sdk
else log "gcloud already installed"; fi

# === Python Virtual Env ===
log "Installing Python dependencies..."
cd ~/ai-video-renderer
if [ ! -d "venv" ]; then python3 -m venv venv; fi
source venv/bin/activate
if [ -f requirements.txt ]; then pip install -r requirements.txt; else warn "requirements.txt missing"; fi

# === .env.n8n and Folders ===
[ -f ".env.n8n" ] || touch .env.n8n
grep -q N8N_ENCRYPTION_KEY .env.n8n || echo "N8N_ENCRYPTION_KEY=$(openssl rand -base64 32)" >> .env.n8n
mkdir -p n8n-data logs backups

# === Firewall ===
sudo ufw allow 5678/tcp
sudo ufw --force enable

# === systemd Service ===
log "Creating systemd service..."
sudo tee /etc/systemd/system/ai-video-renderer.service > /dev/null <<EOL
[Unit]
Description=n8n Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$HOME/ai-video-renderer
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable ai-video-renderer.service

# === Launch ===
docker-compose pull && docker-compose up -d
log "Bootstrap complete. Visit: http://$(curl -s ifconfig.me):5678"
INNER_EOF

chmod +x bootstrap.sh
echo "[TRAE] ✅ bootstrap.sh is ready and executable."