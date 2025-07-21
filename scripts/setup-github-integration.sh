#!/bin/bash

# GitHub Webhook Configuration Script for n8n
# This script sets up GitHub integration for the AI Video Renderer project

set -e

# Configuration
PROJECT_DIR="/Users/joft/Downloads/Muliti Niche automation/ai-video-renderer"
WORKFLOWS_DIR="$PROJECT_DIR/n8n-workflows"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
GITHUB_REPO_URL=""  # To be set by user
GITHUB_USERNAME=""  # To be set by user
GITHUB_TOKEN=""     # To be set by user

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Function to check if Git is configured
check_git_config() {
    log "Checking Git configuration..."
    
    if ! command -v git &> /dev/null; then
        error "Git is not installed. Please install Git first."
        exit 1
    fi
    
    if [ -z "$(git config --global user.name)" ] || [ -z "$(git config --global user.email)" ]; then
        warn "Git user configuration is missing."
        echo "Please configure Git with your credentials:"
        echo "  git config --global user.name 'Your Name'"
        echo "  git config --global user.email 'your.email@example.com'"
        exit 1
    fi
    
    log "Git configuration is valid"
}

# Function to initialize Git repository
init_git_repo() {
    log "Initializing Git repository..."
    
    cd "$PROJECT_DIR"
    
    if [ ! -d ".git" ]; then
        git init
        log "Git repository initialized"
    else
        log "Git repository already exists"
    fi
    
    # Create .gitignore if it doesn't exist
    if [ ! -f ".gitignore" ]; then
        cat > .gitignore << 'EOF'
# Environment files
.env*
!.env.example

# Node modules
node_modules/
npm-debug.log*

# Docker
.docker/
docker-compose.override.yml

# Logs
logs/
*.log

# Runtime data
pids/
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/

# nyc test coverage
.nyc_output

# Dependency directories
jspm_packages/

# Optional npm cache directory
.npm

# Optional REPL history
.node_repl_history

# Output of 'npm pack'
*.tgz

# Yarn Integrity file
.yarn-integrity

# dotenv environment variables file
.env

# next.js build output
.next

# Nuxt.js build output
.nuxt

# vuepress build output
.vuepress/dist

# Serverless directories
.serverless

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# AI Video Renderer specific
output/
temp/
cache/
service-account-key.json
EOF
        log "Created .gitignore file"
    fi
}

# Function to validate workflow JSON files
validate_workflows() {
    log "Validating workflow JSON files..."
    
    local validation_failed=false
    
    for workflow_file in "$WORKFLOWS_DIR"/*.json; do
        if [ -f "$workflow_file" ]; then
            filename=$(basename "$workflow_file")
            if python3 -m json.tool "$workflow_file" > /dev/null 2>&1; then
                log "✅ $filename is valid JSON"
            else
                error "❌ $filename has invalid JSON syntax"
                validation_failed=true
            fi
        fi
    done
    
    if [ "$validation_failed" = true ]; then
        error "Workflow validation failed. Please fix JSON syntax errors before proceeding."
        exit 1
    fi
    
    log "All workflow files are valid"
}

# Function to generate workflow documentation
generate_documentation() {
    log "Generating workflow documentation..."
    
    cat > "$PROJECT_DIR/WORKFLOWS.md" << 'EOF'
# AI Video Renderer - n8n Workflows

This document describes the n8n workflows used in the AI Video Renderer project for automation and integration.

## Overview

The AI Video Renderer uses n8n workflows to automate video processing, YouTube uploads, and system monitoring. All workflows are designed for headless operation and can be triggered via webhooks or schedules.

## Workflows

### 1. Global Configuration Workflow (`global-config.json`)

**Purpose**: System health monitoring and API connectivity validation

**Triggers**:
- Webhook: `http://localhost:5678/webhook/ConfigurationWebhook`
- Schedule: Every 6 hours (configurable)

**Features**:
- Validates environment variables and configuration
- Tests API connectivity (YouTube, Google Cloud, Discord, Telegram)
- Calculates system health score
- Sends notifications via Discord/Telegram
- Provides detailed error reporting

**Setup**:
1. Import the workflow into n8n
2. Configure environment variables in `.env.n8n`
3. Test the webhook endpoint
4. Monitor health notifications

### 2. YouTube Upload Workflow (`youtube-upload.json`)

**Purpose**: Automated YouTube video uploads from rendered content

**Triggers**:
- Webhook: `http://localhost:5678/webhook/youtube-upload`
- Schedule: Every 6 hours (configurable)
- GitHub webhook (when new videos are rendered)

**Features**:
- Automatically finds latest video in output directory
- Handles YouTube OAuth token refresh
- Uploads videos with metadata
- Sends success/failure notifications
- Supports multiple video formats (MP4, MOV, AVI, MKV)

**Setup**:
1. Configure YouTube API credentials in `.env.n8n`
2. Set `YOUTUBE_CHANNEL_ID` and upload preferences
3. Ensure output directory is accessible
4. Test upload workflow

## Configuration

### Environment Variables

Key environment variables required for workflows:

```bash
# YouTube Configuration
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret
YOUTUBE_REFRESH_TOKEN=your_refresh_token
YOUTUBE_CHANNEL_ID=your_channel_id
YOUTUBE_DEFAULT_PRIVACY=private
YOUTUBE_DEFAULT_CATEGORY=22

# Google Cloud
GOOGLE_PROJECT_ID=your_project_id
GOOGLE_API_KEY=your_api_key
GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json

# Notifications
DISCORD_WEBHOOK_URL=your_discord_webhook
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id

# System
RENDER_OUTPUT_DIR=/app/output
CONFIGURATION_WEBHOOK=http://localhost:5678/webhook/ConfigurationWebhook
```

### Webhook Endpoints

- **Global Config**: `http://localhost:5678/webhook/ConfigurationWebhook`
- **YouTube Upload**: `http://localhost:5678/webhook/youtube-upload`

## Monitoring

### Health Check

The Global Configuration workflow provides comprehensive health monitoring:

- **Health Score**: 0-100% based on configuration completeness
- **API Connectivity**: Tests all external services
- **Error Reporting**: Detailed error messages for troubleshooting
- **Notifications**: Real-time alerts via Discord/Telegram

### Testing

Use the provided scripts to test workflows:

```bash
# Test health check
./scripts/test-health-check.sh

# Push workflows to GitHub
./scripts/push-to-github.sh
```

## Maintenance

### Regular Tasks

1. **Monitor Health Score**: Keep above 70% for optimal operation
2. **Update Tokens**: Refresh YouTube tokens when expired
3. **Check Logs**: Review n8n execution logs for errors
4. **Backup Workflows**: Regular commits to GitHub repository

### Troubleshooting

Common issues and solutions:

1. **YouTube Upload Fails**:
   - Check refresh token validity
   - Verify channel ID and permissions
   - Ensure video file accessibility

2. **Health Check Fails**:
   - Validate environment variables
   - Test API endpoints manually
   - Check service account file permissions

3. **Webhook Not Responding**:
   - Verify n8n container is running
   - Check webhook URL configuration
   - Review firewall/network settings

## Performance

### Optimization Tips

1. **Scheduling**: Stagger workflow executions to avoid conflicts
2. **Timeouts**: Adjust HTTP timeouts for large video uploads
3. **Retries**: Configure appropriate retry attempts for API calls
4. **Monitoring**: Use health checks to detect issues early

## Security

### Best Practices

1. **Environment Variables**: Never commit secrets to repository
2. **API Keys**: Rotate keys regularly
3. **Webhooks**: Use HTTPS in production
4. **Access Control**: Limit n8n access to authorized users
5. **Logging**: Avoid logging sensitive information

## GitHub Integration

### Webhook Setup

1. Create a GitHub webhook pointing to your n8n instance
2. Configure payload URL: `http://your-domain:5678/webhook/youtube-upload`
3. Set content type to `application/json`
4. Select relevant events (push, release, etc.)

### Automated Deployment

The `push-to-github.sh` script automates workflow deployment:

1. Validates all JSON files
2. Commits changes with descriptive messages
3. Pushes to configured GitHub repository
4. Maintains version history

## Support

For issues or questions:

1. Check n8n execution logs
2. Review workflow documentation
3. Test individual nodes in n8n editor
4. Validate environment configuration
5. Monitor system health scores

---

*Last updated: $(date)*
EOF

    log "Documentation generated: WORKFLOWS.md"
}

# Function to commit and push changes
commit_and_push() {
    log "Committing and pushing changes to GitHub..."
    
    cd "$PROJECT_DIR"
    
    # Add all workflow files
    git add n8n-workflows/
    git add scripts/
    git add WORKFLOWS.md
    git add .gitignore
    
    # Check if there are changes to commit
    if git diff --staged --quiet; then
        warn "No changes to commit"
        return 0
    fi
    
    # Create commit message
    local commit_message="Update n8n workflows and configuration

- Updated Global Configuration workflow with enhanced error handling
- Created YouTube Upload workflow for automated video uploads
- Added comprehensive workflow documentation
- Updated environment configuration
- Added GitHub integration scripts

Generated on: $(date)"
    
    git commit -m "$commit_message"
    
    # Push to GitHub if remote is configured
    if git remote get-url origin &> /dev/null; then
        log "Pushing to GitHub repository..."
        git push origin main || git push origin master
        log "Successfully pushed to GitHub"
    else
        warn "No GitHub remote configured. Please add remote manually:"
        echo "  git remote add origin https://github.com/USERNAME/REPOSITORY.git"
        echo "  git push -u origin main"
    fi
}

# Function to setup GitHub webhook in n8n
setup_github_webhook() {
    log "Setting up GitHub webhook configuration..."
    
    cat > "$PROJECT_DIR/github-webhook-setup.md" << 'EOF'
# GitHub Webhook Setup for n8n

## Prerequisites

1. GitHub repository for your AI Video Renderer project
2. n8n instance accessible from the internet (or use ngrok for testing)
3. GitHub personal access token with repository permissions

## Setup Steps

### 1. Configure GitHub Repository

1. Go to your GitHub repository
2. Navigate to Settings > Webhooks
3. Click "Add webhook"
4. Configure the webhook:
   - **Payload URL**: `http://your-domain:5678/webhook/youtube-upload`
   - **Content type**: `application/json`
   - **Secret**: (optional, but recommended)
   - **Events**: Select "Just the push event" or customize as needed
   - **Active**: ✅ Checked

### 2. Configure n8n Webhook

The YouTube Upload workflow is already configured to receive GitHub webhooks at:
`http://localhost:5678/webhook/youtube-upload`

### 3. Test the Integration

1. Make a commit to your repository
2. Check n8n execution logs
3. Verify the workflow triggers correctly
4. Monitor Discord/Telegram notifications

### 4. Security Considerations

1. Use HTTPS in production
2. Configure webhook secrets
3. Validate payload signatures
4. Limit webhook access

## Troubleshooting

- **Webhook not triggering**: Check URL accessibility and n8n logs
- **Authentication errors**: Verify GitHub token permissions
- **Payload issues**: Review webhook payload format in n8n

## Alternative: Using ngrok for Development

If your n8n instance is not publicly accessible:

1. Install ngrok: `brew install ngrok` (macOS)
2. Expose n8n: `ngrok http 5678`
3. Use the ngrok URL in GitHub webhook configuration
4. Update webhook URL when ngrok restarts

EOF

    log "GitHub webhook setup guide created: github-webhook-setup.md"
}

# Main execution
main() {
    log "Starting GitHub integration setup for AI Video Renderer..."
    
    # Check if project directory exists
    if [ ! -d "$PROJECT_DIR" ]; then
        error "Project directory not found: $PROJECT_DIR"
        exit 1
    fi
    
    # Create scripts directory if it doesn't exist
    mkdir -p "$SCRIPTS_DIR"
    
    # Check Git configuration
    check_git_config
    
    # Initialize Git repository
    init_git_repo
    
    # Validate workflow files
    validate_workflows
    
    # Generate documentation
    generate_documentation
    
    # Setup GitHub webhook guide
    setup_github_webhook
    
    # Commit and push changes
    commit_and_push
    
    log "GitHub integration setup completed successfully!"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Configure GitHub repository and webhook (see github-webhook-setup.md)"
    echo "2. Set up GitHub remote: git remote add origin https://github.com/USERNAME/REPOSITORY.git"
    echo "3. Test the workflows using the provided scripts"
    echo "4. Monitor workflow executions in n8n"
    echo
    echo -e "${GREEN}Files created/updated:${NC}"
    echo "- .gitignore"
    echo "- WORKFLOWS.md"
    echo "- github-webhook-setup.md"
    echo "- All workflow JSON files validated"
}

# Run main function
main "$@"