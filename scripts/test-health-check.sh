#!/bin/bash

# ===================================================================
# 🔍 N8N GLOBAL CONFIG HEALTH CHECK TESTER
# ===================================================================
# Tests the Global Configuration workflow and verifies connectivity
# Author: DevOps Team
# Last updated: 2025-01-27

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/Users/joft/Downloads/Muliti Niche automation/ai-video-renderer"
N8N_URL="http://localhost:5678"
WEBHOOK_URL="${N8N_URL}/webhook/ConfigurationWebhook"
CONTAINER_NAME="ai-video-renderer-n8n-1"

echo -e "${BLUE}🔍 N8N Global Configuration Health Check Tester${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# Function to check if n8n is running
check_n8n_status() {
    echo -e "${YELLOW}📊 Checking n8n container status...${NC}"
    
    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo -e "${GREEN}✅ n8n container is running${NC}"
        return 0
    else
        echo -e "${RED}❌ n8n container is not running${NC}"
        return 1
    fi
}

# Function to restart n8n container
restart_n8n() {
    echo -e "${YELLOW}🔄 Restarting n8n container...${NC}"
    
    cd "$PROJECT_DIR"
    
    # Stop the container if running
    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo "Stopping n8n container..."
        docker-compose down
        sleep 3
    fi
    
    # Start the container
    echo "Starting n8n container..."
    docker-compose up -d
    
    # Wait for n8n to be ready
    echo "Waiting for n8n to be ready..."
    sleep 15
    
    # Check if n8n is responding
    local retries=0
    local max_retries=12
    
    while [ $retries -lt $max_retries ]; do
        if curl -s "$N8N_URL" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ n8n is ready and responding${NC}"
            return 0
        fi
        
        echo "Waiting for n8n to respond... (attempt $((retries + 1))/$max_retries)"
        sleep 5
        retries=$((retries + 1))
    done
    
    echo -e "${RED}❌ n8n failed to respond after restart${NC}"
    return 1
}

# Function to trigger the health check workflow
trigger_health_check() {
    echo -e "${YELLOW}🚀 Triggering Global Configuration health check...${NC}"
    
    local response
    local http_code
    
    # Make the webhook request
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"trigger": "health_check", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' \
        "$WEBHOOK_URL" 2>/dev/null)
    
    # Extract HTTP status code
    http_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    
    # Extract response body
    local body=$(echo "$response" | sed -e 's/HTTPSTATUS:.*//g')
    
    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        echo -e "${GREEN}✅ Health check triggered successfully (HTTP $http_code)${NC}"
        echo -e "${BLUE}📋 Response:${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        return 0
    else
        echo -e "${RED}❌ Health check failed (HTTP $http_code)${NC}"
        echo -e "${RED}Response: $body${NC}"
        return 1
    fi
}

# Function to check workflow execution status
check_workflow_status() {
    echo -e "${YELLOW}📈 Checking workflow execution status...${NC}"
    
    # Wait a moment for the workflow to process
    sleep 5
    
    # Try to get execution status from n8n API
    local executions_response
    executions_response=$(curl -s "$N8N_URL/api/v1/executions?limit=5" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$executions_response" ]; then
        echo -e "${BLUE}📊 Recent workflow executions:${NC}"
        echo "$executions_response" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'data' in data:
        for exec in data['data'][:3]:
            status = exec.get('finished', False)
            mode = exec.get('mode', 'unknown')
            workflow_name = exec.get('workflowData', {}).get('name', 'Unknown')
            start_time = exec.get('startedAt', 'Unknown')
            print(f\"  • {workflow_name}: {'✅ Completed' if status else '⏳ Running'} ({mode}) - {start_time}\")
    else:
        print('  No execution data available')
except:
    print('  Unable to parse execution data')
" 2>/dev/null || echo "  Unable to retrieve execution status"
    else
        echo -e "${YELLOW}⚠️  Unable to retrieve execution status from n8n API${NC}"
    fi
}

# Function to test individual API endpoints
test_api_endpoints() {
    echo -e "${YELLOW}🔗 Testing individual API endpoints...${NC}"
    
    # Test YouTube API
    echo -e "${BLUE}📺 Testing YouTube API...${NC}"
    local youtube_test=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true&key=AIzaSyDO8kk09sgUnzqUZVILrN-o6s5Jfj8TvIg" \
        2>/dev/null)
    local youtube_code=$(echo "$youtube_test" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    
    if [ "$youtube_code" -eq 200 ]; then
        echo -e "  ${GREEN}✅ YouTube API responding${NC}"
    else
        echo -e "  ${RED}❌ YouTube API failed (HTTP $youtube_code)${NC}"
    fi
    
    # Test Google Cloud API
    echo -e "${BLUE}☁️  Testing Google Cloud API...${NC}"
    local gcp_test=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        "https://cloudresourcemanager.googleapis.com/v1/projects/brave-hearth-464820-s2?key=AIzaSyDO8kk09sgUnzqUZVILrN-o6s5Jfj8TvIg" \
        2>/dev/null)
    local gcp_code=$(echo "$gcp_test" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    
    if [ "$gcp_code" -eq 200 ]; then
        echo -e "  ${GREEN}✅ Google Cloud API responding${NC}"
    else
        echo -e "  ${RED}❌ Google Cloud API failed (HTTP $gcp_code)${NC}"
    fi
    
    # Test Discord Webhook
    echo -e "${BLUE}💬 Testing Discord Webhook...${NC}"
    local discord_test=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"content": "🔍 Health check test from n8n"}' \
        "https://discord.com/api/webhooks/1392152611599417517/2r0YiRE1PUscX-LRitQx1iVn-vHvWy0-P5vMtsOlZrM21li-JvIW4xu5PBe4HsC_eZUd" \
        2>/dev/null)
    local discord_code=$(echo "$discord_test" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    
    if [ "$discord_code" -eq 200 ] || [ "$discord_code" -eq 204 ]; then
        echo -e "  ${GREEN}✅ Discord Webhook responding${NC}"
    else
        echo -e "  ${RED}❌ Discord Webhook failed (HTTP $discord_code)${NC}"
    fi
    
    # Test Telegram Bot
    echo -e "${BLUE}📱 Testing Telegram Bot...${NC}"
    local telegram_test=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        "https://api.telegram.org/bot8161916898:AAG4yBGjmRxT3BblYb0JbYhyxUt1qRMGrI8/getMe" \
        2>/dev/null)
    local telegram_code=$(echo "$telegram_test" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    
    if [ "$telegram_code" -eq 200 ]; then
        echo -e "  ${GREEN}✅ Telegram Bot responding${NC}"
    else
        echo -e "  ${RED}❌ Telegram Bot failed (HTTP $telegram_code)${NC}"
    fi
}

# Function to show environment status
show_environment_status() {
    echo -e "${YELLOW}🌍 Environment Status...${NC}"
    
    if [ -f "$PROJECT_DIR/.env.n8n" ]; then
        echo -e "${GREEN}✅ .env.n8n file exists${NC}"
        
        # Check for critical environment variables
        local env_file="$PROJECT_DIR/.env.n8n"
        
        echo -e "${BLUE}📋 Critical Environment Variables:${NC}"
        
        if grep -q "YOUTUBE_CLIENT_ID=" "$env_file"; then
            echo -e "  ${GREEN}✅ YOUTUBE_CLIENT_ID${NC}"
        else
            echo -e "  ${RED}❌ YOUTUBE_CLIENT_ID missing${NC}"
        fi
        
        if grep -q "GOOGLE_API_KEY=" "$env_file"; then
            echo -e "  ${GREEN}✅ GOOGLE_API_KEY${NC}"
        else
            echo -e "  ${RED}❌ GOOGLE_API_KEY missing${NC}"
        fi
        
        if grep -q "GOOGLE_PROJECT_ID=" "$env_file"; then
            echo -e "  ${GREEN}✅ GOOGLE_PROJECT_ID${NC}"
        else
            echo -e "  ${RED}❌ GOOGLE_PROJECT_ID missing${NC}"
        fi
        
        if grep -q "DISCORD_WEBHOOK_URL=" "$env_file"; then
            echo -e "  ${GREEN}✅ DISCORD_WEBHOOK_URL${NC}"
        else
            echo -e "  ${RED}❌ DISCORD_WEBHOOK_URL missing${NC}"
        fi
        
        if grep -q "TELEGRAM_BOT_TOKEN=" "$env_file"; then
            echo -e "  ${GREEN}✅ TELEGRAM_BOT_TOKEN${NC}"
        else
            echo -e "  ${RED}❌ TELEGRAM_BOT_TOKEN missing${NC}"
        fi
    else
        echo -e "${RED}❌ .env.n8n file not found${NC}"
    fi
    
    # Check for service account file
    if docker exec "$CONTAINER_NAME" test -f "/app/service-account-key.json" 2>/dev/null; then
        echo -e "  ${GREEN}✅ Service account file accessible in container${NC}"
    else
        echo -e "  ${RED}❌ Service account file not accessible in container${NC}"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}Starting health check process...${NC}"
    echo ""
    
    # Check current status
    if ! check_n8n_status; then
        echo ""
        echo -e "${YELLOW}🔄 n8n is not running. Starting restart process...${NC}"
        if ! restart_n8n; then
            echo -e "${RED}❌ Failed to restart n8n. Exiting.${NC}"
            exit 1
        fi
    fi
    
    echo ""
    show_environment_status
    
    echo ""
    test_api_endpoints
    
    echo ""
    if trigger_health_check; then
        echo ""
        check_workflow_status
        
        echo ""
        echo -e "${GREEN}🎉 Health check completed successfully!${NC}"
        echo -e "${BLUE}📊 Check your Discord/Telegram for detailed results.${NC}"
    else
        echo ""
        echo -e "${RED}❌ Health check failed. Check the logs above for details.${NC}"
        exit 1
    fi
    
    echo ""
    echo -e "${BLUE}💡 Tips:${NC}"
    echo -e "  • Check n8n logs: ${YELLOW}docker logs $CONTAINER_NAME${NC}"
    echo -e "  • Access n8n UI: ${YELLOW}$N8N_URL${NC}"
    echo -e "  • Trigger manual test: ${YELLOW}curl -X POST $WEBHOOK_URL${NC}"
}

# Run the main function
main "$@"