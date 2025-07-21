#!/bin/bash

# AI Video Renderer - Quick Start Production Setup
# This script sets up the entire system for immediate production use

set -e

echo "🚀 AI Video Renderer - Quick Start Production Setup"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}📍 Project root: $PROJECT_ROOT${NC}"

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is designed for macOS. Please adapt for your OS."
    exit 1
fi

print_status "Environment validation passed"

# Install Python dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
    pip3 install -r requirements.txt
    print_status "Python dependencies installed"
else
    print_warning "No requirements.txt found, skipping Python dependencies"
fi

# Install n8n if not already installed
if ! command -v n8n &> /dev/null; then
    echo -e "${BLUE}📦 Installing n8n...${NC}"
    npm install -g n8n
    print_status "n8n installed globally"
else
    print_status "n8n already installed"
fi

# Fix workflow JSON issues
echo -e "${BLUE}🔧 Fixing workflow JSON issues...${NC}"
if [ -f "scripts/quality/fix_workflow_json.py" ]; then
    python3 scripts/quality/fix_workflow_json.py
    print_status "Workflow JSON issues fixed"
else
    print_warning "fix_workflow_json.py not found, skipping"
fi

# Run production QA if available
if [ -f "scripts/quality/production_qa_suite.sh" ]; then
    echo -e "${BLUE}🧪 Running production validation...${NC}"
    bash scripts/quality/production_qa_suite.sh
    print_status "Production validation completed"
else
    print_warning "Production QA suite not found, skipping validation"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}📝 Creating .env file template...${NC}"
    cat > .env << 'EOF'
# AI Video Renderer Environment Configuration
# Copy this file and fill in your actual values

# YouTube API Configuration
YOUTUBE_API_KEY=your_youtube_api_key_here
YOUTUBE_CHANNEL_ID=your_channel_id_here

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT_ID=your_project_id_here
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account.json

# AI Services
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Notification Services
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Reddit API (for content sourcing)
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=your_app_name_here

# News API (for content sourcing)
NEWS_API_KEY=your_news_api_key_here

# n8n Configuration
N8N_HOST=localhost
N8N_PORT=5678
N8N_PROTOCOL=http
EOF
    print_status ".env template created - PLEASE FILL IN YOUR ACTUAL VALUES"
else
    print_status ".env file already exists"
fi

# Start n8n in the background
echo -e "${BLUE}🚀 Starting n8n server...${NC}"
export N8N_HOST=localhost
export N8N_PORT=5678
export N8N_PROTOCOL=http

# Kill any existing n8n processes
pkill -f "n8n" || true
sleep 2

# Start n8n in background
nohup n8n start > n8n.log 2>&1 &
N8N_PID=$!

# Wait for n8n to start
echo -e "${BLUE}⏳ Waiting for n8n to start...${NC}"
sleep 10

# Check if n8n is running
if ps -p $N8N_PID > /dev/null; then
    print_status "n8n started successfully (PID: $N8N_PID)"
else
    print_error "Failed to start n8n. Check n8n.log for details."
    exit 1
fi

echo ""
echo "🎉 Production Setup Complete!"
echo "=============================="
echo ""
echo -e "${GREEN}✅ n8n is running at: http://localhost:5678${NC}"
echo -e "${GREEN}✅ Process ID: $N8N_PID${NC}"
echo ""
echo "📋 Next Steps:"
echo "1. Open http://localhost:5678 in your browser"
echo "2. Import the workflows from the n8n-workflows/ directory"
echo "3. Configure your environment variables in .env file"
echo "4. Set up your API keys and credentials"
echo "5. Test the global-config workflow first"
echo ""
echo "📁 Important Files:"
echo "   • .env - Environment configuration"
echo "   • n8n.log - n8n server logs"
echo "   • n8n-workflows/ - Workflow definitions"
echo ""
echo "🔧 Management Commands:"
echo "   • View logs: tail -f n8n.log"
echo "   • Stop n8n: kill $N8N_PID"
echo "   • Restart: pkill -f n8n && n8n start"
echo ""
echo -e "${YELLOW}⚠️  Remember to configure your API keys in the .env file!${NC}"
echo ""