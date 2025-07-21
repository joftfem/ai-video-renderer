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
