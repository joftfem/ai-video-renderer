#!/bin/bash

# Import n8n workflows and activate them
# This script imports the Global Configuration and YouTube Upload workflows

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
N8N_URL="http://localhost:5678"
WORKFLOWS_DIR="/Users/joft/Downloads/Muliti Niche automation/ai-video-renderer/n8n-workflows"

echo -e "${BLUE}🚀 n8n Workflow Import and Activation Script${NC}"
echo "=================================================="

# Function to check if n8n is running
check_n8n_status() {
    echo -e "${YELLOW}🔍 Checking n8n status...${NC}"
    
    if curl -s -f "${N8N_URL}/healthz" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ n8n is running and accessible${NC}"
        return 0
    else
        echo -e "${RED}❌ n8n is not accessible at ${N8N_URL}${NC}"
        return 1
    fi
}

# Function to import a workflow
import_workflow() {
    local workflow_file="$1"
    local workflow_name=$(basename "$workflow_file" .json)
    
    echo -e "${YELLOW}📥 Importing workflow: ${workflow_name}${NC}"
    
    if [[ ! -f "$workflow_file" ]]; then
        echo -e "${RED}❌ Workflow file not found: $workflow_file${NC}"
        return 1
    fi
    
    # Validate JSON syntax
    if ! cat "$workflow_file" | python3 -c "import json, sys; json.load(sys.stdin)" 2>/dev/null; then
        echo -e "${RED}❌ Invalid JSON in workflow file: $workflow_file${NC}"
        return 1
    fi

    # Clean JSON payload
    local cleaned_json=$(cat "$workflow_file" | python3 -c '
import sys, json
data = json.load(sys.stdin)
keys_to_remove = ["id", "versionId", "meta", "tags", "active", "pinData", "staticData", "triggerCount", "shared"]
for key in keys_to_remove:
    data.pop(key, None)
print(json.dumps(data))
')
    if [[ -z "$cleaned_json" ]]; then
        echo -e "${RED}❌ Failed to clean JSON for: $workflow_file${NC}"
        return 1
    fi
    
    # Import workflow via n8n API
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "X-N8N-API-KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NmFlZjEwMy1mOGZjLTQwNTQtYjNkMS01ZTg2Mjg5YWVkYjkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzUzMDg3NzY1fQ.MkrIY-B7e0k7B3T-gULBk3d_UmvjzsUmNkgKfto1dxw" \
        -d "$cleaned_json" \
        "${N8N_URL}/api/v1/workflows" 2>/dev/null)
    
    if echo "$response" | grep -q '"id"'; then
        local workflow_id=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
        echo -e "${GREEN}✅ Workflow imported successfully (ID: $workflow_id)${NC}"
        
        # Activate the workflow
        activate_workflow "$workflow_id" "$workflow_name"
        return 0
    else
        echo -e "${RED}❌ Failed to import workflow: $workflow_name${NC}"
        echo "Response: $response"
        return 1
    fi
}

# Function to activate a workflow
activate_workflow() {
    local workflow_id="$1"
    local workflow_name="$2"
    
    echo -e "${YELLOW}🔄 Activating workflow: ${workflow_name}${NC}"
    
    local activate_response=$(curl -s -X POST "${N8N_URL}/api/v1/workflows/${workflow_id}/activate" \
        -H "X-N8N-API-KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NmFlZjEwMy1mOGZjLTQwNTQtYjNkMS01ZTg2Mjg5YWVkYjkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzUzMDg3NzY1fQ.MkrIY-B7e0k7B3T-gULBk3d_UmvjzsUmNkgKfto1dxw" \
        -H "Content-Type: application/json")
    
    if echo "$activate_response" | grep -q '"active":true'; then
        echo -e "${GREEN}✅ Workflow activated successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to activate workflow: $workflow_name${NC}"
        echo "Response: $activate_response"
        return 1
    fi
}

# Function to list existing workflows
list_workflows() {
    echo -e "${YELLOW}📋 Listing existing workflows...${NC}"
    
    local response=$(curl -s -H "X-N8N-API-KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NmFlZjEwMy1mOGZjLTQwNTQtYjNkMS01ZTg2Mjg5YWVkYjkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzUzMDg3NzY1fQ.MkrIY-B7e0k7B3T-gULBk3d_UmvjzsUmNkgKfto1dxw" "${N8N_URL}/api/v1/workflows" 2>/dev/null)
    
    if echo "$response" | grep -q '"data"'; then
        echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
workflows = data.get('data', [])
if workflows:
    print('Existing workflows:')
    for wf in workflows:
        status = '🟢 Active' if wf.get('active') else '🔴 Inactive'
        print(f'  - {wf.get(\"name\", \"Unknown\")} (ID: {wf.get(\"id\")}) {status}')
else:
    print('No workflows found.')
" 2>/dev/null
    else
        echo -e "${RED}❌ Failed to list workflows${NC}"
    fi
}

# Function to delete all workflows (for clean import)
delete_all_workflows() {
    echo -e "${YELLOW}🗑️  Deleting all existing workflows...${NC}"
    
    local response=$(curl -s "${N8N_URL}/api/v1/workflows" 2>/dev/null)
    
    if echo "$response" | grep -q '"data"'; then
        echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
workflows = data.get('data', [])
for wf in workflows:
    print(wf.get('id'))
" 2>/dev/null | while read -r workflow_id; do
            if [[ -n "$workflow_id" ]]; then
                curl -s -X DELETE -H "X-N8N-API-KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NmFlZjEwMy1mOGZjLTQwNTQtYjNkMS01ZTg2Mjg5YWVkYjkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzUzMDg3NzY1fQ.MkrIY-B7e0k7B3T-gULBk3d_UmvjzsUmNkgKfto1dxw" "${N8N_URL}/api/v1/workflows/${workflow_id}" > /dev/null 2>&1
                echo -e "${GREEN}✅ Deleted workflow ID: $workflow_id${NC}"
            fi
        done
    fi
}

# Main execution
main() {
    # Check if n8n is running
    if ! check_n8n_status; then
        echo -e "${RED}❌ Please start n8n first using: docker-compose up -d${NC}"
        exit 1
    fi
    
    # List existing workflows
    list_workflows
    
    # Ask user if they want to delete existing workflows
    echo ""
    read -p "Do you want to delete all existing workflows before importing? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        delete_all_workflows
    fi
    
    echo ""
    echo -e "${BLUE}📥 Importing workflows...${NC}"
    
    echo ""
    
    # Import YouTube with Notifications workflow
    if [[ -f "${WORKFLOWS_DIR}/youtube-with-notifications.json" ]]; then
        import_workflow "${WORKFLOWS_DIR}/youtube-with-notifications.json"
    else
        echo -e "${RED}❌ YouTube with Notifications workflow not found${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}📋 Final workflow status:${NC}"
    list_workflows
    
    echo ""
    echo -e "${GREEN}🎉 Workflow import completed!${NC}"
    echo -e "${YELLOW}💡 You can now access n8n at: ${N8N_URL}${NC}"
    echo -e "${YELLOW}💡 Test the Global Configuration workflow at: ${N8N_URL}/webhook/ConfigurationWebhook${NC}"
    echo -e "${YELLOW}💡 Test the YouTube Upload workflow at: ${N8N_URL}/webhook/youtube-upload${NC}"
}

# Run main function
main "$@"