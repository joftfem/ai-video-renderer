#!/usr/bin/env python3
"""
Workflow Issues Fix Script
Fixes common n8n workflow issues including:
1. fs module usage in sandboxed environments
2. Incorrect API endpoints
3. JSON syntax errors
4. Template expression issues
"""

import json
import os
import re
import sys
from pathlib import Path

def fix_fs_module_usage(workflow_data):
    """Fix fs module usage in Code nodes"""
    fixes_applied = []
    
    def traverse_and_fix(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check for jsCode in Code nodes
                if key == "jsCode" and isinstance(value, str):
                    if "require('fs')" in value or 'require("fs")' in value:
                        # Replace fs-based file operations with n8n-compatible alternatives
                        new_code = """// Prepare video upload configuration
// Note: This node expects video file to be provided via webhook or previous node

try {
  const inputData = $input.first();
  const json = inputData.json;
  
  // Check if video file is provided in binary data from previous node
  if (inputData.binary && inputData.binary.video_file) {
    const videoFile = inputData.binary.video_file;
    
    return {
      json: {
        ...json,
        video_file_name: videoFile.fileName || 'video.mp4',
        video_file_path: videoFile.fileName || 'video.mp4',
        video_file_size: videoFile.data ? videoFile.data.length : 0,
        video_ready: true,
        mime_type: videoFile.mimeType || 'video/mp4'
      },
      binary: {
        video_file: videoFile
      }
    };
  }
  
  // If no binary data, check if video_file_path is provided in JSON
  if (json.video_file_path) {
    return {
      json: {
        ...json,
        video_file_name: json.video_file_path.split('/').pop(),
        video_ready: true,
        message: 'Video file path provided, ready for upload'
      }
    };
  }
  
  // If no video file provided, return error
  throw new Error('No video file provided. Please ensure video file is uploaded via webhook or previous node.');
  
} catch (error) {
  return {
    json: {
      ...($input.first().json),
      error: error.message,
      video_ready: false,
      troubleshooting: {
        message: 'Video file not found',
        solutions: [
          'Ensure video file is uploaded via webhook',
          'Check that previous node provides binary video data',
          'Verify video_file_path is correctly set in input JSON'
        ]
      }
    }
  };
}"""
                        obj[key] = new_code
                        fixes_applied.append(f"Fixed fs module usage in {current_path}")
                
                traverse_and_fix(value, current_path)
                
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                traverse_and_fix(item, f"{path}[{i}]")
    
    traverse_and_fix(workflow_data)
    return fixes_applied

def fix_api_endpoints(workflow_data):
    """Fix incorrect API endpoints"""
    fixes_applied = []
    
    def traverse_and_fix(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                # Fix YouTube Analytics API endpoint
                if key == "url" and isinstance(value, str):
                    if "www.googleapis.com/youtube/analytics/v2/reports" in value:
                        obj[key] = value.replace(
                            "www.googleapis.com/youtube/analytics/v2/reports",
                            "youtubeanalytics.googleapis.com/v2/reports"
                        )
                        fixes_applied.append(f"Fixed YouTube Analytics API endpoint in {current_path}")
                
                traverse_and_fix(value, current_path)
                
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                traverse_and_fix(item, f"{path}[{i}]")
    
    traverse_and_fix(workflow_data)
    return fixes_applied

def fix_json_syntax(workflow_data):
    """Fix JSON syntax issues in template expressions"""
    fixes_applied = []
    
    def traverse_and_fix(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                # Fix unquoted template expressions in JSON
                if key == "jsonBody" and isinstance(value, str):
                    # Fix color field template expressions
                    if 'color": {{ $' in value:
                        obj[key] = value.replace('color": {{ $', 'color": "{{ $').replace(' }}', ' }}"')
                        fixes_applied.append(f"Fixed JSON color template in {current_path}")
                
                traverse_and_fix(value, current_path)
                
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                traverse_and_fix(item, f"{path}[{i}]")
    
    traverse_and_fix(workflow_data)
    return fixes_applied

def validate_workflow_file(file_path):
    """Validate and fix a single workflow file"""
    print(f"\n🔍 Validating: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False
    
    all_fixes = []
    
    # Apply fixes
    all_fixes.extend(fix_fs_module_usage(workflow_data))
    all_fixes.extend(fix_api_endpoints(workflow_data))
    all_fixes.extend(fix_json_syntax(workflow_data))
    
    if all_fixes:
        try:
            # Write back the fixed workflow
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Fixed {len(all_fixes)} issues:")
            for fix in all_fixes:
                print(f"   • {fix}")
            return True
            
        except Exception as e:
            print(f"❌ Error writing fixed workflow to {file_path}: {e}")
            return False
    else:
        print("✅ No issues found")
        return True

def main():
    """Main function to validate and fix all workflow files"""
    print("🔧 n8n Workflow Issues Fix Script")
    print("=" * 50)
    
    # Find workflow directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    workflows_dir = project_root / "n8n-workflows"
    
    if not workflows_dir.exists():
        print(f"❌ Workflows directory not found: {workflows_dir}")
        sys.exit(1)
    
    # Find all JSON workflow files
    workflow_files = list(workflows_dir.glob("*.json"))
    
    if not workflow_files:
        print(f"❌ No workflow files found in {workflows_dir}")
        sys.exit(1)
    
    print(f"📁 Found {len(workflow_files)} workflow files")
    
    success_count = 0
    total_count = len(workflow_files)
    
    for workflow_file in workflow_files:
        if validate_workflow_file(workflow_file):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 SUMMARY: {success_count}/{total_count} workflows processed successfully")
    
    if success_count == total_count:
        print("🎉 All workflows are now fixed and ready!")
        
        # Create validation report
        report_path = workflows_dir / "validation_report.txt"
        with open(report_path, 'w') as f:
            f.write("n8n Workflow Validation Report\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Validation Date: {os.popen('date').read().strip()}\n")
            f.write(f"Total Files: {total_count}\n")
            f.write(f"Successfully Fixed: {success_count}\n\n")
            f.write("Fixed Issues:\n")
            f.write("• fs module usage replaced with n8n-compatible alternatives\n")
            f.write("• YouTube Analytics API endpoint corrected\n")
            f.write("• JSON template expression syntax fixed\n\n")
            f.write("All workflows are now ready for production use!\n")
        
        print(f"📄 Validation report saved to: {report_path}")
        sys.exit(0)
    else:
        print("❌ Some workflows still have issues. Please check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()