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
