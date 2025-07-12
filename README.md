# My First Project

🚀 **AI Video Renderer** - Fully automated YouTube content creation using AI, GCP, and Dockerized n8n.

## 📋 Project Information

- **Project Name**: My First Project
- **Project ID**: `brave-hearth-464820-s2`
- **Project Number**: `798807204191`
- **Purpose**: Fully automated YouTube content creation using AI, Google Cloud Platform, and Dockerized n8n workflows

## 🎯 Overview

This project provides a complete automation pipeline for creating, processing, and publishing YouTube videos using artificial intelligence and cloud technologies. The system leverages n8n workflows, Google Cloud services, and various AI APIs to generate content at scale.

## ✨ Features

### 🤖 AI-Powered Content Generation
- **Google AI Integration**: Advanced text and content generation
- **ElevenLabs**: High-quality text-to-speech synthesis
- **Hugging Face**: Machine learning models for content processing
- **JSON2Video**: Automated video creation from structured data

### 📺 YouTube Automation
- Automated video upload and publishing
- Dynamic metadata generation (titles, descriptions, tags)
- Revenue tracking and analytics
- OAuth2 authentication with automatic token refresh

### 🌐 Media & Content Sources
- **Pixabay**: Stock images and videos
- **Pexels**: High-quality visual content
- **Bitly**: URL shortening for tracking
- **Reddit**: Content sourcing and engagement

### 🔔 Notifications & Monitoring
- **Discord**: Real-time workflow notifications
- **Telegram**: Status updates and alerts
- Health monitoring and system diagnostics
- Revenue tracking notifications

### ☁️ Google Cloud Integration
- **Cloud Functions**: Serverless execution
- **Pub/Sub**: Event-driven messaging
- **Secret Manager**: Secure credential storage
- **Cloud Storage**: Media file management

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Services   │    │   n8n Workflows │    │  Google Cloud   │
│                 │    │                 │    │                 │
│ • Google AI     │◄──►│ • Main Pipeline │◄──►│ • Cloud Funcs   │
│ • ElevenLabs    │    │ • Revenue Track │    │ • Pub/Sub       │
│ • Hugging Face  │    │ • Global Config │    │ • Secret Mgr    │
│ • JSON2Video    │    │                 │    │ • Storage       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   │
                    ┌─────────────────┐
                    │    YouTube      │
                    │   Publishing    │
                    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Google Cloud Platform account
- YouTube API credentials
- AI service API keys (Google AI, ElevenLabs, etc.)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/joftfem/ai-video-renderer.git
   cd ai-video-renderer
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.n8n.example .env.n8n
   # Edit .env.n8n with your actual credentials
   ```

3. **Set up Google Cloud credentials**:
   ```bash
   # Place your service account key file
   cp /path/to/your/service-account-key.json ./service-account-key.json
   ```

4. **Start the services**:
   ```bash
   docker-compose up -d
   ```

5. **Access n8n interface**:
   - Open http://localhost:5678
   - Import workflows from `n8n-workflows/` directory

## 📁 Project Structure

```
ai-video-renderer/
├── 📄 .env.n8n                 # Environment configuration
├── 🐳 docker-compose.yml       # Docker services definition
├── 📋 bootstrap.sh             # Setup script
├── 📂 infra/                   # Infrastructure scripts
│   ├── 🔄 refresh-oauth-token.py
│   ├── 📢 notify-video-status.py
│   └── 🛠️ self_heal.py
├── 📂 n8n-workflows/           # n8n workflow definitions
│   ├── 💰 $75000-subflow.json
│   ├── ⚙️ globalconfig-subflow.json
│   └── 📺 youtube-with-notifications.json
└── 📂 scripts/                 # Additional automation scripts
    └── 📝 actual-niche-script.md
```

## ⚙️ Configuration

### Environment Variables

The system uses the following key environment variables:

#### YouTube Configuration
- `YOUTUBE_CLIENT_ID`: OAuth2 client ID
- `YOUTUBE_CLIENT_SECRET`: OAuth2 client secret
- `YOUTUBE_REFRESH_TOKEN`: OAuth2 refresh token
- `YOUTUBE_ACCESS_TOKEN`: OAuth2 access token

#### AI Services
- `GOOGLE_API_KEY`: Google AI API key
- `GOOGLE_AI_STUDIO_KEY`: Google AI Studio key
- `ELEVENLABS_KEY`: ElevenLabs API key
- `HF_TOKEN`: Hugging Face token
- `JSON2VIDEO_KEY`: JSON2Video API key

#### Media Services
- `PIXABAY_KEY`: Pixabay API key
- `PEXELS_KEY`: Pexels API key
- `BITLY_TOKEN`: Bitly access token
- `REDDIT_CLIENT_ID`: Reddit client ID
- `REDDIT_SECRET`: Reddit client secret

#### Notifications
- `DISCORD_WEBHOOK_URL`: Discord webhook URL
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_ID`: Telegram chat ID

#### Google Cloud
- `GOOGLE_PROJECT_ID`: GCP project ID (brave-hearth-464820-s2)
- `GOOGLE_PROJECT_NUMBER`: GCP project number (798807204191)
- `GOOGLE_APPLICATION_CREDENTIALS`: Service account key path

## 🔧 n8n Workflows

### Main Workflows

1. **YouTube with Notifications** (`youtube-with-notifications.json`)
   - Complete video upload pipeline
   - Metadata generation and optimization
   - Multi-channel notification system

2. **Revenue Tracker** (`$75000-subflow.json`)
   - YouTube analytics monitoring
   - Revenue calculation and reporting
   - Goal tracking and notifications

3. **Global Configuration** (`globalconfig-subflow.json`)
   - Centralized configuration management
   - Health monitoring and validation
   - Service status reporting

## 🛠️ Infrastructure Scripts

### Core Scripts

- **`refresh-oauth-token.py`**: Automated OAuth token refresh
- **`notify-video-status.py`**: Video processing status notifications
- **`self_heal.py`**: System health monitoring and auto-recovery

## 📊 Monitoring & Health Checks

The system includes comprehensive monitoring:

- **Service Health**: Real-time status of all integrated services
- **Configuration Validation**: Automatic validation of API keys and settings
- **Performance Metrics**: Memory usage, processing times, error rates
- **Revenue Tracking**: YouTube monetization and goal progress

## 🔒 Security Best Practices

- ✅ Environment variables for all sensitive data
- ✅ Service account key exclusion from version control
- ✅ Encrypted n8n workflows and credentials
- ✅ Secure webhook endpoints
- ✅ OAuth2 token rotation

## 🚀 Deployment

### Local Development
```bash
docker-compose up -d
```

### Production Deployment
1. Configure production environment variables
2. Set up Google Cloud resources
3. Deploy using Docker Compose or Kubernetes
4. Configure monitoring and alerting

## 📈 Scaling

The system is designed for horizontal scaling:

- **Containerized Architecture**: Easy deployment across multiple instances
- **Cloud-Native**: Leverages GCP managed services
- **Event-Driven**: Pub/Sub messaging for decoupled processing
- **Stateless Workflows**: n8n workflows can run on multiple nodes

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- 📧 Create an issue in this repository
- 💬 Join our Discord community
- 📖 Check the documentation in `/docs`

## 🙏 Acknowledgments

- n8n team for the excellent workflow automation platform
- Google Cloud Platform for robust infrastructure services
- All AI service providers for enabling advanced content generation

---

**Built with ❤️ for automated content creation**