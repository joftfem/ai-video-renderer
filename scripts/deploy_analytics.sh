#!/bin/bash

# Deploy Analytics & Memory System to Google Cloud Platform
# This script sets up all necessary GCP resources for the analytics collection
# and hybrid memory system components.

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}
DATASET_ID="ai_renderer"
SCHEDULER_TIMEZONE=${SCHEDULER_TIMEZONE:-"UTC"}
SERVICE_ACCOUNT_NAME="ai-video-analytics"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists gcloud; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check if authenticated with gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "."; then
        print_error "Not authenticated with gcloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Set up GCP project
setup_project() {
    print_status "Setting up GCP project: $PROJECT_ID"
    
    # Set the project
    gcloud config set project $PROJECT_ID
    
    # Enable required APIs
    print_status "Enabling required APIs..."
    gcloud services enable bigquery.googleapis.com
    gcloud services enable cloudscheduler.googleapis.com
    gcloud services enable firestore.googleapis.com
    gcloud services enable youtube.googleapis.com
    gcloud services enable sheets.googleapis.com
    gcloud services enable logging.googleapis.com
    gcloud services enable monitoring.googleapis.com
    gcloud services enable pubsub.googleapis.com
    gcloud services enable cloudfunctions.googleapis.com
    gcloud services enable run.googleapis.com
    
    print_success "APIs enabled successfully"
}

# Create service account
create_service_account() {
    print_status "Creating service account: $SERVICE_ACCOUNT_NAME"
    
    # Check if service account already exists
    if gcloud iam service-accounts describe "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1; then
        print_warning "Service account already exists, skipping creation"
    else
        gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
            --display-name="AI Video Analytics Service Account" \
            --description="Service account for AI video analytics and memory system"
        
        print_success "Service account created"
    fi
    
    # Grant necessary roles
    print_status "Granting IAM roles..."
    
    local service_account_email="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # BigQuery roles
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$service_account_email" \
        --role="roles/bigquery.dataEditor"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$service_account_email" \
        --role="roles/bigquery.jobUser"
    
    # Firestore roles
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$service_account_email" \
        --role="roles/datastore.user"
    
    # Cloud Scheduler roles
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$service_account_email" \
        --role="roles/cloudscheduler.admin"
    
    # Logging roles
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$service_account_email" \
        --role="roles/logging.logWriter"
    
    # Monitoring roles
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$service_account_email" \
        --role="roles/monitoring.metricWriter"
    
    # Pub/Sub roles
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$service_account_email" \
        --role="roles/pubsub.publisher"
    
    print_success "IAM roles granted"
    
    # Create and download service account key
    print_status "Creating service account key..."
    local key_file="config/service-account-key.json"
    
    if [ ! -f "$key_file" ]; then
        mkdir -p config
        gcloud iam service-accounts keys create "$key_file" \
            --iam-account="$service_account_email"
        
        print_success "Service account key created: $key_file"
        print_warning "Keep this key file secure and do not commit it to version control!"
    else
        print_warning "Service account key already exists: $key_file"
    fi
}

# Set up BigQuery
setup_bigquery() {
    print_status "Setting up BigQuery dataset and tables..."
    
    # Create dataset
    if ! bq ls -d $PROJECT_ID:$DATASET_ID >/dev/null 2>&1; then
        bq mk --dataset \
            --description="AI Video Renderer Analytics Dataset" \
            --location=US \
            $PROJECT_ID:$DATASET_ID
        
        print_success "BigQuery dataset created: $DATASET_ID"
    else
        print_warning "BigQuery dataset already exists: $DATASET_ID"
    fi
    
    # Create analytics table
    print_status "Creating analytics table..."
    
    cat > /tmp/analytics_schema.json << 'EOF'
[
  {"name": "video_id", "type": "STRING", "mode": "REQUIRED"},
  {"name": "upload_id", "type": "STRING", "mode": "NULLABLE"},
  {"name": "title", "type": "STRING", "mode": "NULLABLE"},
  {"name": "description", "type": "STRING", "mode": "NULLABLE"},
  {"name": "tags", "type": "STRING", "mode": "REPEATED"},
  {"name": "niche", "type": "STRING", "mode": "NULLABLE"},
  {"name": "views", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "likes", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "comments", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "shares", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "impressions", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "ctr", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "avg_view_duration", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "watch_time_minutes", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "subscribers_gained", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "engagement_rate", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "success_score", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "thumbnail_variant", "type": "STRING", "mode": "NULLABLE"},
  {"name": "thumbnail_score", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "tts_engine", "type": "STRING", "mode": "NULLABLE"},
  {"name": "tts_cost", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "tts_duration", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "moderation_score", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "total_cost", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "collected_at", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "uploaded_at", "type": "TIMESTAMP", "mode": "NULLABLE"},
  {"name": "metadata", "type": "JSON", "mode": "NULLABLE"}
]
EOF
    
    if ! bq ls $PROJECT_ID:$DATASET_ID | grep -q "analytics"; then
        bq mk --table \
            --description="YouTube Analytics and Performance Metrics" \
            --time_partitioning_field=collected_at \
            --time_partitioning_type=DAY \
            --clustering_fields=niche,tts_engine,thumbnail_variant \
            $PROJECT_ID:$DATASET_ID.analytics \
            /tmp/analytics_schema.json
        
        print_success "Analytics table created"
    else
        print_warning "Analytics table already exists"
    fi
    
    # Create cost tracking table
    print_status "Creating cost tracking table..."
    
    cat > /tmp/cost_schema.json << 'EOF'
[
  {"name": "date", "type": "DATE", "mode": "REQUIRED"},
  {"name": "service", "type": "STRING", "mode": "REQUIRED"},
  {"name": "provider", "type": "STRING", "mode": "REQUIRED"},
  {"name": "usage_count", "type": "INTEGER", "mode": "REQUIRED"},
  {"name": "cost_usd", "type": "FLOAT", "mode": "REQUIRED"},
  {"name": "video_count", "type": "INTEGER", "mode": "REQUIRED"},
  {"name": "avg_cost_per_video", "type": "FLOAT", "mode": "REQUIRED"},
  {"name": "metadata", "type": "JSON", "mode": "NULLABLE"}
]
EOF
    
    if ! bq ls $PROJECT_ID:$DATASET_ID | grep -q "cost_tracking"; then
        bq mk --table \
            --description="Daily Cost Tracking by Service" \
            --time_partitioning_field=date \
            --time_partitioning_type=DAY \
            --clustering_fields=service,provider \
            $PROJECT_ID:$DATASET_ID.cost_tracking \
            /tmp/cost_schema.json
        
        print_success "Cost tracking table created"
    else
        print_warning "Cost tracking table already exists"
    fi
    
    # Clean up temporary files
    rm -f /tmp/analytics_schema.json /tmp/cost_schema.json
}

# Set up Firestore
setup_firestore() {
    print_status "Setting up Firestore..."
    
    # Check if Firestore is already initialized
    if gcloud firestore databases describe --region=$REGION >/dev/null 2>&1; then
        print_warning "Firestore already initialized"
    else
        # Initialize Firestore in Native mode
        gcloud firestore databases create --region=$REGION
        print_success "Firestore initialized in region: $REGION"
    fi
    
    # Create composite indexes for efficient querying
    print_status "Creating Firestore indexes..."
    
    cat > /tmp/firestore_indexes.yaml << 'EOF'
indexes:
  - collectionGroup: video_memory
    queryScope: COLLECTION
    fields:
      - fieldPath: niche
        order: ASCENDING
      - fieldPath: uploaded_at
        order: DESCENDING
  
  - collectionGroup: video_memory
    queryScope: COLLECTION
    fields:
      - fieldPath: tts_engine
        order: ASCENDING
      - fieldPath: uploaded_at
        order: DESCENDING
  
  - collectionGroup: video_memory
    queryScope: COLLECTION
    fields:
      - fieldPath: success_score
        order: DESCENDING
      - fieldPath: uploaded_at
        order: DESCENDING
  
  - collectionGroup: video_memory
    queryScope: COLLECTION
    fields:
      - fieldPath: ttl_date
        order: ASCENDING
EOF
    
    gcloud firestore indexes composite create --file=/tmp/firestore_indexes.yaml
    
    print_success "Firestore indexes created"
    
    # Clean up
    rm -f /tmp/firestore_indexes.yaml
}

# Set up Cloud Scheduler jobs
setup_scheduler() {
    print_status "Setting up Cloud Scheduler jobs..."
    
    local service_account_email="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Daily analytics collection job
    print_status "Creating daily analytics collection job..."
    
    if gcloud scheduler jobs describe daily-analytics-collection --location=$REGION >/dev/null 2>&1; then
        print_warning "Daily analytics job already exists, updating..."
        gcloud scheduler jobs update http daily-analytics-collection \
            --location=$REGION \
            --schedule="0 6 * * *" \
            --time-zone=$SCHEDULER_TIMEZONE \
            --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/collect-analytics" \
            --http-method=POST \
            --oidc-service-account-email=$service_account_email \
            --headers="Content-Type=application/json" \
            --message-body='{"action": "collect_daily"}'
    else
        gcloud scheduler jobs create http daily-analytics-collection \
            --location=$REGION \
            --schedule="0 6 * * *" \
            --time-zone=$SCHEDULER_TIMEZONE \
            --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/collect-analytics" \
            --http-method=POST \
            --oidc-service-account-email=$service_account_email \
            --headers="Content-Type=application/json" \
            --message-body='{"action": "collect_daily"}' \
            --description="Daily collection of YouTube analytics"
    fi
    
    # Weekly performance report job
    print_status "Creating weekly report job..."
    
    if gcloud scheduler jobs describe weekly-performance-report --location=$REGION >/dev/null 2>&1; then
        print_warning "Weekly report job already exists, updating..."
        gcloud scheduler jobs update http weekly-performance-report \
            --location=$REGION \
            --schedule="0 9 * * 1" \
            --time-zone=$SCHEDULER_TIMEZONE \
            --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/generate-report" \
            --http-method=POST \
            --oidc-service-account-email=$service_account_email \
            --headers="Content-Type=application/json" \
            --message-body='{"action": "weekly_report"}'
    else
        gcloud scheduler jobs create http weekly-performance-report \
            --location=$REGION \
            --schedule="0 9 * * 1" \
            --time-zone=$SCHEDULER_TIMEZONE \
            --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/generate-report" \
            --http-method=POST \
            --oidc-service-account-email=$service_account_email \
            --headers="Content-Type=application/json" \
            --message-body='{"action": "weekly_report"}' \
            --description="Weekly performance report generation"
    fi
    
    # Memory cleanup job
    print_status "Creating memory cleanup job..."
    
    if gcloud scheduler jobs describe memory-cleanup --location=$REGION >/dev/null 2>&1; then
        print_warning "Memory cleanup job already exists, updating..."
        gcloud scheduler jobs update http memory-cleanup \
            --location=$REGION \
            --schedule="0 2 * * *" \
            --time-zone=$SCHEDULER_TIMEZONE \
            --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/cleanup-memory" \
            --http-method=POST \
            --oidc-service-account-email=$service_account_email \
            --headers="Content-Type=application/json" \
            --message-body='{"action": "cleanup_expired"}'
    else
        gcloud scheduler jobs create http memory-cleanup \
            --location=$REGION \
            --schedule="0 2 * * *" \
            --time-zone=$SCHEDULER_TIMEZONE \
            --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/cleanup-memory" \
            --http-method=POST \
            --oidc-service-account-email=$service_account_email \
            --headers="Content-Type=application/json" \
            --message-body='{"action": "cleanup_expired"}' \
            --description="Daily cleanup of expired memory data"
    fi
    
    print_success "Cloud Scheduler jobs created"
}

# Create Cloud Function for analytics collection
create_cloud_function() {
    print_status "Creating Cloud Function for analytics collection..."
    
    # Create function directory
    mkdir -p cloud_functions/analytics
    
    # Create main.py for Cloud Function
    cat > cloud_functions/analytics/main.py << 'EOF'
import functions_framework
import json
import os
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.append('/workspace')

from scripts.analytics.collect_metrics import YouTubeAnalyticsCollector
from scripts.utils.memory_system import HybridMemorySystem

@functions_framework.http
def collect_analytics(request):
    """HTTP Cloud Function for collecting analytics."""
    try:
        # Parse request
        request_json = request.get_json(silent=True)
        action = request_json.get('action', 'collect_daily') if request_json else 'collect_daily'
        
        # Initialize collectors
        analytics_collector = YouTubeAnalyticsCollector()
        
        if action == 'collect_daily':
            # Collect analytics for recent uploads
            result = analytics_collector.collect_daily_metrics()
            return {'status': 'success', 'action': action, 'result': result}
        
        elif action == 'weekly_report':
            # Generate weekly performance report
            report = analytics_collector.generate_performance_report(days=7)
            return {'status': 'success', 'action': action, 'report': report}
        
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}, 400
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@functions_framework.http
def cleanup_memory(request):
    """HTTP Cloud Function for memory cleanup."""
    try:
        # Initialize memory system
        memory_system = HybridMemorySystem()
        
        # Cleanup expired data
        result = memory_system.cleanup_expired_data()
        
        return {'status': 'success', 'action': 'cleanup_expired', 'result': result}
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500
EOF
    
    # Create requirements.txt for Cloud Function
    cat > cloud_functions/analytics/requirements.txt << 'EOF'
functions-framework==3.*
google-cloud-bigquery==3.*
google-cloud-firestore==2.*
google-cloud-logging==3.*
google-api-python-client==2.*
google-auth==2.*
pinecone-client==2.*
sentence-transformers==2.*
pandas==2.*
numpy==1.*
requests==2.*
python-dotenv==1.*
EOF
    
    print_success "Cloud Function files created"
}

# Set up monitoring and alerting
setup_monitoring() {
    print_status "Setting up monitoring and alerting..."
    
    # Create notification channel (email)
    if [ ! -z "$ALERT_EMAIL" ]; then
        print_status "Creating email notification channel..."
        
        cat > /tmp/notification_channel.json << EOF
{
  "type": "email",
  "displayName": "AI Video Analytics Alerts",
  "description": "Email notifications for AI video analytics system",
  "labels": {
    "email_address": "$ALERT_EMAIL"
  }
}
EOF
        
        gcloud alpha monitoring channels create --channel-content-from-file=/tmp/notification_channel.json
        
        print_success "Email notification channel created"
        rm -f /tmp/notification_channel.json
    fi
    
    # Create alerting policies
    print_status "Creating alerting policies..."
    
    # High error rate alert
    cat > /tmp/error_rate_policy.json << 'EOF'
{
  "displayName": "High Error Rate - Analytics Collection",
  "documentation": {
    "content": "Analytics collection error rate is above 5%"
  },
  "conditions": [
    {
      "displayName": "Error rate condition",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_function\" AND resource.labels.function_name=\"collect-analytics\"",
        "comparison": "COMPARISON_GREATER_THAN",
        "thresholdValue": 0.05,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_RATE",
            "crossSeriesReducer": "REDUCE_MEAN"
          }
        ]
      }
    }
  ],
  "enabled": true
}
EOF
    
    gcloud alpha monitoring policies create --policy-from-file=/tmp/error_rate_policy.json
    
    print_success "Monitoring and alerting configured"
    rm -f /tmp/error_rate_policy.json
}

# Create environment file template
create_env_template() {
    print_status "Creating environment configuration template..."
    
    cat > .env.analytics.template << 'EOF'
# Google Cloud Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=config/service-account-key.json

# BigQuery Configuration
BIGQUERY_LOCATION=US

# YouTube API
YOUTUBE_API_KEY=your-youtube-api-key

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=ai-video-memory

# Google Sheets (Optional)
GOOGLE_SHEETS_SYNC=false
GOOGLE_SHEETS_CREDENTIALS=config/sheets-credentials.json
ANALYTICS_SPREADSHEET_ID=your-spreadsheet-id

# Notifications (Optional)
NOTIFICATIONS_ENABLED=true
TELEGRAM_NOTIFICATIONS=false
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

EMAIL_NOTIFICATIONS=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
TO_EMAILS=alerts@yourdomain.com

# Cost Limits
DAILY_COST_LIMIT=10.0
MONTHLY_COST_LIMIT=300.0

# Feature Flags
AUTO_ANALYTICS_ENABLED=true
MEMORY_LOGGING_ENABLED=true
MEMORY_CLEANUP_ENABLED=true
SCHEDULER_ENABLED=true
ADVANCED_ANALYTICS=true
COST_OPTIMIZATION=true
REAL_TIME_MONITORING=true
AUTOMATED_RECOMMENDATIONS=true

# Development
DEBUG_MODE=false
MOCK_APIS=false
TEST_DATA_ENABLED=false
LOG_LEVEL=INFO
EOF
    
    print_success "Environment template created: .env.analytics.template"
    print_warning "Please copy this to .env.analytics and fill in your actual values"
}

# Main deployment function
main() {
    print_status "Starting Analytics & Memory System deployment..."
    
    # Check if PROJECT_ID is set
    if [ "$PROJECT_ID" = "your-project-id" ]; then
        print_error "Please set GCP_PROJECT_ID environment variable"
        exit 1
    fi
    
    check_prerequisites
    setup_project
    create_service_account
    setup_bigquery
    setup_firestore
    setup_scheduler
    create_cloud_function
    setup_monitoring
    create_env_template
    
    print_success "\n🎉 Analytics & Memory System deployment completed successfully!"
    
    echo -e "\n${BLUE}Next steps:${NC}"
    echo "1. Copy .env.analytics.template to .env.analytics and configure your API keys"
    echo "2. Set up Pinecone index (if not already done)"
    echo "3. Deploy Cloud Functions: cd cloud_functions/analytics && gcloud functions deploy collect-analytics --runtime python39 --trigger-http"
    echo "4. Test the analytics collection: python scripts/analytics/collect_metrics.py"
    echo "5. Monitor the system: gcloud logging read 'resource.type=cloud_function'"
    
    echo -e "\n${GREEN}Resources created:${NC}"
    echo "• BigQuery dataset: $PROJECT_ID:$DATASET_ID"
    echo "• BigQuery tables: analytics, cost_tracking"
    echo "• Firestore database in region: $REGION"
    echo "• Service account: $SERVICE_ACCOUNT_NAME"
    echo "• Cloud Scheduler jobs: daily-analytics-collection, weekly-performance-report, memory-cleanup"
    echo "• Cloud Function code: cloud_functions/analytics/"
    
    echo -e "\n${YELLOW}Important:${NC}"
    echo "• Keep your service account key secure: config/service-account-key.json"
    echo "• Set up your API keys in .env.analytics"
    echo "• Monitor costs in the GCP Console"
    echo "• Review and adjust the Cloud Scheduler job schedules as needed"
}

# Run main function
main "$@"