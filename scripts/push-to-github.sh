#!/bin/bash

# GitHub Integration Script for n8n Workflows
# Pushes workflows to GitHub repository and sets up webhook integration

set -e

# Configuration
PROJECT_DIR="/Users/joft/Downloads/Muliti Niche automation/ai-video-renderer"
WORKFLOWS_DIR="$PROJECT_DIR/n8n-workflows"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# GitHub Configuration (update these values)
GITHUB_USERNAME="your-github-username"
GITHUB_REPO="ai-video-renderer"
GITHUB_TOKEN="your-github-token"
GITHUB_WEBHOOK_SECRET="your-webhook-secret"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 N8N Workflows to GitHub Pusher${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

# Function to check if git is initialized
check_git_init() {
    if [ ! -d "$PROJECT_DIR/.git" ]; then
        echo -e "${YELLOW}📁 Initializing Git repository...${NC}"
        cd "$PROJECT_DIR"
        git init
        
        # Add GitHub remote if not exists
        if ! git remote get-url origin >/dev/null 2>&1; then
            echo -e "${YELLOW}🔗 Adding GitHub remote...${NC}"
            echo -e "${RED}⚠️  Please update GITHUB_REPO variable in this script with your actual repository${NC}"
            git remote add origin "https://github.com/$GITHUB_REPO.git"
        fi
        
        # Create .gitignore if not exists
        if [ ! -f "$PROJECT_DIR/.gitignore" ]; then
            echo -e "${YELLOW}📝 Creating .gitignore...${NC}"
            cat > "$PROJECT_DIR/.gitignore" << 'EOF'
# Environment files
.env*
!.env.example

# Node modules
node_modules/

# Docker volumes
n8n-data/
postgres-data/

# Logs
*.log
logs/

# OS files
.DS_Store
Thumbs.db

# IDE files
.vscode/
.idea/

# Temporary files
tmp/
temp/

# Service account keys
*service-account*.json
*credentials*.json

# Output files
output/
renders/
thumbnails/

# Cache
.cache/
EOF
        fi
    fi
}

# Function to validate workflows
validate_workflows() {
    echo -e "${YELLOW}🔍 Validating workflow files...${NC}"
    
    local valid_count=0
    local total_count=0
    
    if [ -d "$WORKFLOWS_DIR" ]; then
        for workflow_file in "$WORKFLOWS_DIR"/*.json; do
            if [ -f "$workflow_file" ]; then
                total_count=$((total_count + 1))
                local filename=$(basename "$workflow_file")
                
                # Validate JSON syntax
                if python3 -m json.tool "$workflow_file" > /dev/null 2>&1; then
                    echo -e "  ${GREEN}✅ $filename${NC}"
                    valid_count=$((valid_count + 1))
                else
                    echo -e "  ${RED}❌ $filename (Invalid JSON)${NC}"
                fi
            fi
        done
        
        echo ""
        echo -e "${BLUE}📊 Validation Summary: $valid_count/$total_count workflows valid${NC}"
        
        if [ $valid_count -ne $total_count ]; then
            echo -e "${RED}❌ Some workflows have validation errors. Please fix them before pushing.${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Workflows directory not found: $WORKFLOWS_DIR${NC}"
        return 1
    fi
    
    return 0
}

# Function to create workflow documentation
create_documentation() {
    echo -e "${YELLOW}📚 Creating workflow documentation...${NC}"
    
    local doc_file="$PROJECT_DIR/WORKFLOWS.md"
    
    cat > "$doc_file" << 'EOF'
# 🎬 AI Video Renderer - N8N Workflows

This repository contains n8n workflows for automated YouTube video creation and management.

## 📋 Available Workflows

### 1. Global Configuration (`global-config.json`)
- **Purpose**: System health monitoring and API connectivity testing
- **Triggers**: Webhook (`/webhook/ConfigurationWebhook`) and Schedule (every 6 hours)
- **Features**:
  - Environment variable validation
  - YouTube API connectivity test
  - Google Cloud API connectivity test
  - Discord webhook test
  - Telegram bot test
  - Health scoring and alerting

### 2. YouTube Upload (`youtube-upload.json`)
- **Purpose**: Automated video upload to YouTube
- **Triggers**: File system events, GitHub webhooks, manual trigger
- **Features**:
  - Video file processing
  - Metadata extraction
  - YouTube API upload
  - Status notifications
  - Error handling and retry logic

## 🚀 Setup Instructions

### Prerequisites
- n8n instance running
- Valid API credentials in `.env.n8n`
- Docker environment configured

### Installation
1. Import workflows into n8n:
   ```bash
   # Copy workflows to n8n data directory
   cp n8n-workflows/*.json /path/to/n8n/data/workflows/
   ```

2. Configure environment variables:
   ```bash
   # Update .env.n8n with your credentials
   cp .env.example .env.n8n
   # Edit .env.n8n with your API keys
   ```

3. Restart n8n:
   ```bash
   docker-compose restart n8n
   ```

### Testing
Run the health check script to verify all workflows:
```bash
./scripts/test-health-check.sh
```

## 🔧 Configuration

### Environment Variables
Key environment variables required:

#### YouTube API
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`
- `YOUTUBE_CHANNEL_ID`

#### Google Cloud
- `GOOGLE_API_KEY`
- `GOOGLE_PROJECT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`

#### Notifications
- `DISCORD_WEBHOOK_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### Webhook Endpoints
- Global Config: `http://localhost:5678/webhook/ConfigurationWebhook`
- YouTube Upload: `http://localhost:5678/webhook/youtube-upload`

## 📊 Monitoring

### Health Checks
The Global Configuration workflow provides:
- Overall health score (0-100)
- Individual service connectivity status
- Detailed error reporting
- Automated alerts via Discord/Telegram

### Logs
Check n8n logs for detailed execution information:
```bash
docker logs ai-video-renderer-n8n-1
```

## 🔄 Maintenance

### Updating Workflows
1. Export updated workflows from n8n UI
2. Save to `n8n-workflows/` directory
3. Run validation: `./scripts/push-to-github.sh`
4. Commit and push changes

### Credential Rotation
1. Update credentials in `.env.n8n`
2. Restart n8n container
3. Run health check to verify connectivity

## 🐛 Troubleshooting

### Common Issues

#### YouTube API Errors
- Check if refresh token is expired
- Verify OAuth scopes include `youtube.upload`
- Regenerate tokens via Google OAuth Playground

#### Google Cloud API Errors
- Verify project ID matches GCP console
- Check service account permissions
- Ensure service account key is accessible in container

#### Webhook Failures
- Verify webhook URLs are accessible
- Check Discord/Telegram bot permissions
- Test endpoints manually with curl

### Getting Help
1. Check workflow execution logs in n8n UI
2. Run health check script for diagnostics
3. Review environment variable configuration
4. Check Docker container logs

## 📈 Performance

### Optimization Tips
- Enable workflow caching where appropriate
- Use appropriate retry strategies
- Monitor execution times and optimize long-running nodes
- Implement proper error handling

### Scaling
- Consider using n8n cloud for high-volume operations
- Implement queue-based processing for large files
- Use webhook authentication for security

## 🔐 Security

### Best Practices
- Never commit API keys to version control
- Use environment variables for all credentials
- Implement webhook authentication
- Regularly rotate API keys
- Monitor for unauthorized access

### Compliance
- Ensure YouTube uploads comply with platform policies
- Implement content filtering where required
- Maintain audit logs for compliance requirements

---

**Last Updated**: 2025-01-27
**Version**: 1.0.0
**Maintainer**: DevOps Team
EOF

    echo -e "${GREEN}✅ Documentation created: $doc_file${NC}"
}

# Function to commit and push changes
commit_and_push() {
    echo -e "${YELLOW}📤 Committing and pushing changes...${NC}"
    
    cd "$PROJECT_DIR"
    
    # Add all workflow files
    git add n8n-workflows/
    git add scripts/
    git add WORKFLOWS.md
    git add .gitignore 2>/dev/null || true
    
    # Check if there are changes to commit
    if git diff --staged --quiet; then
        echo -e "${YELLOW}⚠️  No changes to commit${NC}"
        return 0
    fi
    
    # Create commit message
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local commit_message="🔄 Update n8n workflows - $timestamp

- Updated workflow configurations
- Validated JSON syntax
- Generated documentation
- Automated via push-to-github.sh script"
    
    # Commit changes
    git commit -m "$commit_message"
    
    # Push to GitHub
    echo -e "${YELLOW}🚀 Pushing to GitHub...${NC}"
    
    if git push origin "$BRANCH" 2>/dev/null; then
        echo -e "${GREEN}✅ Successfully pushed to GitHub${NC}"
        
        # Show repository URL
        local repo_url=$(git remote get-url origin | sed 's/\.git$//')
        echo -e "${BLUE}🔗 Repository: $repo_url${NC}"
        
        return 0
    else
        echo -e "${RED}❌ Failed to push to GitHub${NC}"
        echo -e "${YELLOW}💡 Make sure you have:${NC}"
        echo -e "  • Valid GitHub credentials configured"
        echo -e "  • Push access to the repository"
        echo -e "  • Updated the GITHUB_REPO variable in this script"
        echo ""
        echo -e "${YELLOW}🔧 To configure GitHub authentication:${NC}"
        echo -e "  git config --global user.name 'Your Name'"
        echo -e "  git config --global user.email 'your.email@example.com'"
        echo -e "  # For HTTPS: Use personal access token as password"
        echo -e "  # For SSH: Add your SSH key to GitHub"
        
        return 1
    fi
}

# Function to show repository setup instructions
show_setup_instructions() {
    echo -e "${BLUE}📋 GitHub Repository Setup Instructions${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo ""
    echo -e "${YELLOW}1. Create a new GitHub repository:${NC}"
    echo -e "   • Go to https://github.com/new"
    echo -e "   • Repository name: ai-video-renderer-workflows"
    echo -e "   • Description: N8N workflows for AI video automation"
    echo -e "   • Set to Private (recommended for API keys)"
    echo ""
    echo -e "${YELLOW}2. Update this script:${NC}"
    echo -e "   • Edit GITHUB_REPO variable with your username/repo"
    echo -e "   • Example: GITHUB_REPO=\"yourusername/ai-video-renderer-workflows\""
    echo ""
    echo -e "${YELLOW}3. Configure Git authentication:${NC}"
    echo -e "   • For HTTPS: Use personal access token"
    echo -e "   • For SSH: Add SSH key to GitHub"
    echo ""
    echo -e "${YELLOW}4. Set up GitHub webhook (optional):${NC}"
    echo -e "   • Repository Settings → Webhooks → Add webhook"
    echo -e "   • Payload URL: http://your-n8n-host/webhook/github-push"
    echo -e "   • Content type: application/json"
    echo -e "   • Events: Push events"
    echo ""
    echo -e "${YELLOW}5. Run this script again after setup${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Starting workflow push process...${NC}"
    echo ""
    
    # Check if GitHub repo is configured
    if [[ "$GITHUB_REPO" == "your-username/ai-video-renderer-workflows" ]]; then
        echo -e "${RED}❌ GitHub repository not configured${NC}"
        echo ""
        show_setup_instructions
        exit 1
    fi
    
    # Validate workflows first
    if ! validate_workflows; then
        exit 1
    fi
    
    echo ""
    check_git_init
    
    echo ""
    create_documentation
    
    echo ""
    if commit_and_push; then
        echo ""
        echo -e "${GREEN}🎉 Workflows successfully pushed to GitHub!${NC}"
        echo ""
        echo -e "${BLUE}📊 Summary:${NC}"
        echo -e "  • Workflows validated and pushed"
        echo -e "  • Documentation generated"
        echo -e "  • Repository updated with latest changes"
        echo ""
        echo -e "${BLUE}🔗 Next steps:${NC}"
        echo -e "  • Set up GitHub webhook for automated triggers"
        echo -e "  • Configure branch protection rules"
        echo -e "  • Add collaborators if needed"
    else
        echo ""
        echo -e "${RED}❌ Failed to push workflows to GitHub${NC}"
        exit 1
    fi
}

# Show help if requested
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo -e "${BLUE}🚀 N8N Workflows to GitHub Pusher${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC}"
    echo -e "  $0                    # Push workflows to GitHub"
    echo -e "  $0 --help            # Show this help message"
    echo ""
    echo -e "${YELLOW}Configuration:${NC}"
    echo -e "  • Update GITHUB_REPO variable with your repository"
    echo -e "  • Ensure Git authentication is configured"
    echo -e "  • Workflows must be in n8n-workflows/ directory"
    echo ""
    echo -e "${YELLOW}Features:${NC}"
    echo -e "  • JSON validation of all workflows"
    echo -e "  • Automatic documentation generation"
    echo -e "  • Git repository initialization"
    echo -e "  • Automated commit and push"
    exit 0
fi

# Run the main function
main "$@"