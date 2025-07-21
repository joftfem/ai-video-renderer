#!/bin/bash

# Test Automation Script for n8n Workflows
# Tests both Global Configuration and YouTube Upload Automation workflows

set -e

# Configuration
PROJECT_DIR="/Users/joft/Downloads/Muliti Niche automation/ai-video-renderer"
N8N_URL="http://localhost:5678"
GLOBAL_CONFIG_WEBHOOK="http://localhost:5678/webhook/global-config"
YOUTUBE_UPLOAD_WEBHOOK="http://localhost:5678/webhook/youtube-upload"
OUTPUT_DIR="$PROJECT_DIR/output"
SAMPLE_VIDEO="$OUTPUT_DIR/sample-video.mp4"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if n8n is running
check_n8n_status() {
    log "Checking n8n status..."
    if curl -s "$N8N_URL" > /dev/null 2>&1; then
        success "n8n is running at $N8N_URL"
        return 0
    else
        error "n8n is not running at $N8N_URL"
        return 1
    fi
}

# Restart n8n
restart_n8n() {
    log "Restarting n8n..."
    cd "$PROJECT_DIR"
    
    # Stop existing n8n processes
    pkill -f "n8n" || true
    sleep 2
    
    # Start n8n in background
    log "Starting n8n..."
    nohup npm run start > n8n.log 2>&1 &
    
    # Wait for n8n to start
    log "Waiting for n8n to start..."
    for i in {1..30}; do
        if check_n8n_status; then
            success "n8n started successfully"
            return 0
        fi
        sleep 2
    done
    
    error "Failed to start n8n"
    return 1
}

# Create sample video if it doesn't exist
create_sample_video() {
    log "Checking for sample video..."
    
    if [ ! -d "$OUTPUT_DIR" ]; then
        log "Creating output directory: $OUTPUT_DIR"
        mkdir -p "$OUTPUT_DIR"
    fi
    
    if [ ! -f "$SAMPLE_VIDEO" ]; then
        log "Creating sample video for testing..."
        
        # Check if ffmpeg is available
        if command -v ffmpeg &> /dev/null; then
            # Create a simple test video with ffmpeg
            ffmpeg -f lavfi -i testsrc=duration=10:size=1280x720:rate=30 \
                   -f lavfi -i sine=frequency=1000:duration=10 \
                   -c:v libx264 -c:a aac -shortest \
                   "$SAMPLE_VIDEO" > /dev/null 2>&1
            success "Sample video created: $SAMPLE_VIDEO"
        else
            warning "ffmpeg not found. Creating placeholder file..."
            echo "This is a placeholder video file for testing" > "$SAMPLE_VIDEO"
            warning "Created placeholder file. For actual video upload testing, replace with a real video file."
        fi
    else
        success "Sample video already exists: $SAMPLE_VIDEO"
    fi
}

# Test Global Configuration workflow
test_global_config() {
    log "Testing Global Configuration workflow..."
    
    local response=$(curl -s -w "%{http_code}" -X POST "$GLOBAL_CONFIG_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d '{"test": true, "source": "automation_test"}' \
        -o /tmp/global_config_response.json)
    
    local http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        success "Global Configuration webhook responded successfully"
        
        # Parse response
        if [ -f /tmp/global_config_response.json ]; then
            local health_score=$(cat /tmp/global_config_response.json | grep -o '"health_score":[0-9]*' | cut -d':' -f2 || echo "0")
            local connectivity_score=$(cat /tmp/global_config_response.json | grep -o '"connectivity_score":[0-9]*' | cut -d':' -f2 || echo "0")
            local status=$(cat /tmp/global_config_response.json | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
            
            log "Health Score: $health_score%"
            log "Connectivity Score: $connectivity_score%"
            log "Status: $status"
            
            if [ "$health_score" -ge 70 ] && [ "$connectivity_score" -ge 50 ]; then
                success "Global Configuration is healthy"
                return 0
            else
                warning "Global Configuration has issues (Health: $health_score%, Connectivity: $connectivity_score%)"
                return 1
            fi
        else
            warning "Could not parse Global Configuration response"
            return 1
        fi
    else
        error "Global Configuration webhook failed with HTTP code: $http_code"
        return 1
    fi
}

# Test YouTube Upload Automation workflow
test_youtube_upload() {
    log "Testing YouTube Upload Automation workflow..."
    
    if [ ! -f "$SAMPLE_VIDEO" ]; then
        error "Sample video not found: $SAMPLE_VIDEO"
        return 1
    fi
    
    # Prepare test data
    local test_data='{
        "video_file": "'$SAMPLE_VIDEO'",
        "title": "Test Video - Automation Test",
        "description": "This is a test video uploaded by the automation test script.",
        "tags": ["test", "automation", "n8n"],
        "privacy": "private",
        "category": "22",
        "test_mode": true
    }'
    
    local response=$(curl -s -w "%{http_code}" -X POST "$YOUTUBE_UPLOAD_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$test_data" \
        -o /tmp/youtube_upload_response.json)
    
    local http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        success "YouTube Upload webhook responded successfully"
        
        # Parse response
        if [ -f /tmp/youtube_upload_response.json ]; then
            local upload_status=$(cat /tmp/youtube_upload_response.json | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
            local video_id=$(cat /tmp/youtube_upload_response.json | grep -o '"video_id":"[^"]*"' | cut -d'"' -f4 || echo "")
            
            log "Upload Status: $upload_status"
            if [ -n "$video_id" ]; then
                log "Video ID: $video_id"
                success "Video uploaded successfully"
                return 0
            else
                warning "Upload completed but no video ID returned"
                return 1
            fi
        else
            warning "Could not parse YouTube Upload response"
            return 1
        fi
    else
        error "YouTube Upload webhook failed with HTTP code: $http_code"
        if [ -f /tmp/youtube_upload_response.json ]; then
            error "Response: $(cat /tmp/youtube_upload_response.json)"
        fi
        return 1
    fi
}

# Generate test report
generate_report() {
    local global_config_result=$1
    local youtube_upload_result=$2
    
    log "Generating test report..."
    
    cat > "$PROJECT_DIR/test-report.txt" << EOF
n8n Workflow Test Report
========================
Generated: $(date)

Test Results:
- Global Configuration: $([ $global_config_result -eq 0 ] && echo "PASSED" || echo "FAILED")
- YouTube Upload Automation: $([ $youtube_upload_result -eq 0 ] && echo "PASSED" || echo "FAILED")

Overall Status: $([ $global_config_result -eq 0 ] && [ $youtube_upload_result -eq 0 ] && echo "ALL TESTS PASSED" || echo "SOME TESTS FAILED")

Recommendations:
$([ $global_config_result -ne 0 ] && echo "- Fix Global Configuration issues before proceeding to production")
$([ $youtube_upload_result -ne 0 ] && echo "- Verify YouTube credentials and API access")
$([ $global_config_result -eq 0 ] && [ $youtube_upload_result -eq 0 ] && echo "- System is ready for production deployment")

Log Files:
- n8n log: $PROJECT_DIR/n8n.log
- Global Config response: /tmp/global_config_response.json
- YouTube Upload response: /tmp/youtube_upload_response.json
EOF
    
    success "Test report saved to: $PROJECT_DIR/test-report.txt"
}

# Main execution
main() {
    log "Starting n8n workflow automation tests..."
    
    # Check if we're in the right directory
    if [ ! -d "$PROJECT_DIR" ]; then
        error "Project directory not found: $PROJECT_DIR"
        exit 1
    fi
    
    # Create sample video
    create_sample_video
    
    # Restart n8n
    if ! restart_n8n; then
        error "Failed to start n8n. Exiting."
        exit 1
    fi
    
    # Wait a bit more for workflows to load
    sleep 5
    
    # Test Global Configuration
    log "Running Global Configuration test..."
    test_global_config
    local global_config_result=$?
    
    # Wait between tests
    sleep 2
    
    # Test YouTube Upload (only if global config is healthy)
    log "Running YouTube Upload test..."
    if [ $global_config_result -eq 0 ]; then
        test_youtube_upload
        local youtube_upload_result=$?
    else
        warning "Skipping YouTube Upload test due to Global Configuration issues"
        local youtube_upload_result=1
    fi
    
    # Generate report
    generate_report $global_config_result $youtube_upload_result
    
    # Final status
    if [ $global_config_result -eq 0 ] && [ $youtube_upload_result -eq 0 ]; then
        success "All tests passed! System is ready for production."
        exit 0
    else
        error "Some tests failed. Check the test report for details."
        exit 1
    fi
}

# Run main function
main "$@"