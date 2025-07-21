#!/usr/bin/env python3
"""Health check script for AI Video Renderer"""

import requests
import sys
import os
from datetime import datetime

def check_n8n_health():
    """Check N8N health endpoint"""
    try:
        n8n_port = os.getenv("N8N_PORT", "5678")
        response = requests.get(f"http://localhost:{n8n_port}/healthz", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_disk_space():
    """Check available disk space"""
    import shutil
    total, used, free = shutil.disk_usage("/")
    free_gb = free // (1024**3)
    return free_gb > 5  # At least 5GB free

def main():
    """Run health checks"""
    checks = {
        "N8N Service": check_n8n_health(),
        "Disk Space": check_disk_space()
    }
    
    all_passed = all(checks.values())
    
    print(f"Health Check Report - {datetime.now()}")
    print("=" * 40)
    
    for check, status in checks.items():
        status_str = "✅ PASS" if status else "❌ FAIL"
        print(f"{check}: {status_str}")
    
    print("=" * 40)
    print(f"Overall Status: {'✅ HEALTHY' if all_passed else '❌ UNHEALTHY'}")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
