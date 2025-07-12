#!/bin/bash

# AI Video Renderer Bootstrap Script
# Optimized for Google Cloud Platform e2-micro instances
# This script installs Docker, Docker Compose, and starts the n8n automation system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root for security reasons"
fi

# Update system packages
log "Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Install required packages
log "Installing required packages..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    unzip \
    wget \
    git \
    python3 \
    python3-pip \
    htop \
    nano

# Install Docker
log "Installing Docker..."
if ! command -v docker &> /dev/null; then
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    # Enable Docker service
    sudo systemctl enable docker
    sudo systemctl start docker
    
    log "Docker installed successfully"
else
    log "Docker is already installed"
fi

# Install Docker Compose
log "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    # Get latest version
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d'"' -f4)
    
    # Download and install
    sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    # Create symlink for easier access
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    log "Docker Compose installed successfully"
else
    log "Docker Compose is already installed"
fi

# Install Google Cloud SDK (for Secret Manager integration)
log "Installing Google Cloud SDK..."
if ! command -v gcloud &> /dev/null; then
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
    sudo apt-get update -y
    sudo apt-get install -y google-cloud-sdk
    log "Google Cloud SDK installed successfully"
else
    log "Google Cloud SDK is already installed"
fi

# Install Python dependencies for infrastructure scripts
log "Installing Python dependencies..."
pip3 install --user google-cloud-secret-manager google-auth google-auth-oauthlib google-auth-httplib2 requests

# Set up project directory
PROJECT_DIR="/home/$USER/ai-video-renderer"
log "Setting up project directory at $PROJECT_DIR"

# Create project directory if it doesn't exist
if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
    log "Created project directory"
fi

# Navigate to project directory
cd "$PROJECT_DIR"

# Check if .env.n8n exists
if [ ! -f ".env.n8n" ]; then
    warn ".env.n8n file not found. Please create it with your API keys and tokens."
    warn "You can copy the template from the repository and fill in your values."
fi

# Generate n8n encryption key if not set
if ! grep -q "N8N_ENCRYPTION_KEY=" .env.n8n 2>/dev/null || grep -q "N8N_ENCRYPTION_KEY=your_n8n_encryption_key_here" .env.n8n 2>/dev/null; then
    log "Generating n8n encryption key..."
    ENCRYPTION_KEY=$(openssl rand -base64 32)
    if [ -f ".env.n8n" ]; then
        sed -i "s/N8N_ENCRYPTION_KEY=.*/N8N_ENCRYPTION_KEY=$ENCRYPTION_KEY/" .env.n8n
    else
        echo "N8N_ENCRYPTION_KEY=$ENCRYPTION_KEY" > .env.n8n
    fi
    log "n8n encryption key generated and saved"
fi

# Create necessary directories
log "Creating necessary directories..."
mkdir -p n8n-data
mkdir -p logs
mkdir -p backups

# Set proper permissions
sudo chown -R $USER:$USER "$PROJECT_DIR"
chmod +x bootstrap.sh 2>/dev/null || true
chmod +x infra/*.py 2>/dev/null || true

# Configure firewall for n8n port
log "Configuring firewall..."
sudo ufw allow 5678/tcp comment "n8n web interface"
sudo ufw --force enable

# Create systemd service for auto-start
log "Creating systemd service..."
sudo tee /etc/systemd/system/ai-video-renderer.service > /dev/null <<EOF
[Unit]
Description=AI Video Renderer n8n Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable ai-video-renderer.service

# Start the application
log "Starting AI Video Renderer..."

# Pull latest images
docker-compose pull

# Start services
docker-compose up -d

# Wait for n8n to be ready
log "Waiting for n8n to be ready..."
sleep 30

# Check if n8n is running
if docker-compose ps | grep -q "Up"; then
    log "✅ AI Video Renderer is running successfully!"
    log "📊 n8n interface: http://$(curl -s ifconfig.me):5678"
    log "🔍 Check status: docker-compose ps"
    log "📋 View logs: docker-compose logs -f"
    log "🛑 Stop services: docker-compose down"
else
    error "❌ Failed to start AI Video Renderer. Check logs with: docker-compose logs"
fi

# Display system information
log "System Information:"
echo "  - OS: $(lsb_release -d | cut -f2)"
echo "  - Docker: $(docker --version | cut -d' ' -f3 | cut -d',' -f1)"
echo "  - Docker Compose: $(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)"
echo "  - Available Memory: $(free -h | awk '/^Mem:/ {print $7}')"
echo "  - Available Disk: $(df -h / | awk 'NR==2 {print $4}')"

log "🎉 Bootstrap completed successfully!"
log "📖 Next steps:"
log "   1. Fill in your API keys in .env.n8n"
log "   2. Import workflows from n8n-workflows/ directory"
log "   3. Configure your automation schedules"
log "   4. Monitor logs and system health"

exit 0