#!/usr/bin/env python3
"""
Fix n8n Workflow JSON Template Issues

This script fixes the JSON parameter validation error in the "Send Health Alert" node
by properly quoting template expressions and ensuring valid JSON structure.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List

class WorkflowJSONFixer:
    def __init__(self, workflows_dir: str = "n8n-workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.fixes_applied = []
        self.errors_found = []
    
    def fix_json_templates(self, json_str: str) -> str:
        """Fix common JSON template issues in n8n workflows"""
        
        # Fix 1: Quote template expressions that should be strings
        # Pattern: "color": {{ $json.something }}
        json_str = re.sub(
            r'"color":\s*{{\s*([^}]+)\s*}}',
            r'"color": "{{ \1 }}"',
            json_str
        )
        
        # Fix 2: Quote template expressions in field values
        # Pattern: "value": {{ $json.something }}
        json_str = re.sub(
            r'"value":\s*{{\s*([^}]+)\s*}}(?=\s*[,}])',
            r'"value": "{{ \1 }}"',
            json_str
        )
        
        # Fix 3: Quote template expressions for timestamps
        # Pattern: "timestamp": {{ $json.something }}
        json_str = re.sub(
            r'"timestamp":\s*{{\s*([^}]+)\s*}}',
            r'"timestamp": "{{ \1 }}"',
            json_str
        )
        
        # Fix 4: Quote template expressions for usernames and URLs
        json_str = re.sub(
            r'"(username|avatar_url)":\s*{{\s*([^}]+)\s*}}',
            r'"\1": "{{ \2 }}"',
            json_str
        )
        
        return json_str
    
    def fix_discord_embed_json(self, embed_json: str) -> str:
        """Specifically fix Discord embed JSON structure"""
        
        # The corrected Discord embed structure
        fixed_embed = '''
{
  "embeds": [
    {
      "title": "❌ Configuration Health Alert",
      "description": "System configuration issues detected that require attention",
      "color": "{{ $json.notifications_config.discord.embed_colors.error }}",
      "fields": [
        {
          "name": "🏥 Health Score",
          "value": "{{ $json.validation.health_score }}%",
          "inline": true
        },
        {
          "name": "🔗 Connectivity Score",
          "value": "{{ $json.validation.connectivity_score }}%",
          "inline": true
        },
        {
          "name": "📊 Status",
          "value": "{{ $json.validation.status }}",
          "inline": true
        },
        {
          "name": "❗ Issues",
          "value": "{{ $json.validation.message }}",
          "inline": false
        },
        {
          "name": "🔧 Service Status",
          "value": "YouTube: {{ $json.service_status.youtube.enabled ? '✅' : '❌' }}\\nAI Services: {{ ($json.service_status.ai_services.google || $json.service_status.ai_services.elevenlabs) ? '✅' : '❌' }}\\nNotifications: {{ ($json.service_status.notifications.discord || $json.service_status.notifications.telegram) ? '✅' : '❌' }}\\nGCP: {{ $json.service_status.gcp.project_configured ? '✅' : '❌' }}",
          "inline": true
        },
        {
          "name": "🌐 Connectivity Tests",
          "value": "YouTube API: {{ $json.connectivity_tests.youtube_api_test ? '✅' : '❌' }}\\nGoogle Cloud: {{ $json.connectivity_tests.google_cloud_test ? '✅' : '❌' }}\\nDiscord: {{ $json.connectivity_tests.discord_webhook_test ? '✅' : '❌' }}\\nTelegram: {{ $json.connectivity_tests.telegram_bot_test ? '✅' : '❌' }}",
          "inline": true
        }
      ],
      "timestamp": "{{ $json.validated_at }}",
      "footer": {
        "text": "AI Video Renderer - Global Config v{{ $json.config_version }}"
      }
    }
  ],
  "username": "{{ $json.notifications_config.discord.username }}",
  "avatar_url": "{{ $json.notifications_config.discord.avatar_url }}"
}'''
        
        return fixed_embed.strip()
    
    def fix_workflow_file(self, file_path: Path) -> bool:
        """Fix a single workflow file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse JSON
            workflow_data = json.loads(content)
            
            # Find and fix HTTP Request nodes with JSON body issues
            nodes_fixed = 0
            for node in workflow_data.get('nodes', []):
                if (node.get('type') == 'n8n-nodes-base.httpRequest' and 
                    'Send Health Alert' in node.get('name', '')):
                    
                    # Fix the JSON body parameter
                    parameters = node.get('parameters', {})
                    if 'body' in parameters:
                        # Replace with corrected Discord embed JSON
                        parameters['body'] = self.fix_discord_embed_json(
                            str(parameters.get('body', ''))
                        )
                        nodes_fixed += 1
                        
                        # Ensure proper content type
                        if 'options' not in parameters:
                            parameters['options'] = {}
                        if 'headers' not in parameters['options']:
                            parameters['options']['headers'] = {}
                        
                        parameters['options']['headers']['Content-Type'] = 'application/json'
            
            if nodes_fixed > 0:
                # Write back the fixed workflow
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                
                self.fixes_applied.append(f"Fixed {nodes_fixed} nodes in {file_path.name}")
                return True
            
            return False
            
        except Exception as e:
            self.errors_found.append(f"Error fixing {file_path.name}: {str(e)}")
            return False
    
    def fix_all_workflows(self) -> Dict[str, Any]:
        """Fix all workflow files in the directory"""
        
        if not self.workflows_dir.exists():
            return {
                'success': False,
                'error': f"Workflows directory not found: {self.workflows_dir}"
            }
        
        workflow_files = list(self.workflows_dir.glob('*.json'))
        
        if not workflow_files:
            return {
                'success': False,
                'error': f"No workflow files found in {self.workflows_dir}"
            }
        
        files_processed = 0
        files_fixed = 0
        
        for file_path in workflow_files:
            files_processed += 1
            if self.fix_workflow_file(file_path):
                files_fixed += 1
        
        return {
            'success': True,
            'files_processed': files_processed,
            'files_fixed': files_fixed,
            'fixes_applied': self.fixes_applied,
            'errors_found': self.errors_found
        }
    
    def create_backup(self) -> str:
        """Create backup of workflows before fixing"""
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = self.workflows_dir.parent / f"n8n-workflows-backup-{timestamp}"
        
        if self.workflows_dir.exists():
            shutil.copytree(self.workflows_dir, backup_dir)
            return str(backup_dir)
        
        return ""

def main():
    """Main function to fix workflow JSON issues"""
    
    print("🔧 n8n Workflow JSON Fixer")
    print("=" * 50)
    
    # Initialize fixer
    fixer = WorkflowJSONFixer()
    
    # Create backup
    print("📦 Creating backup...")
    backup_path = fixer.create_backup()
    if backup_path:
        print(f"✅ Backup created: {backup_path}")
    else:
        print("⚠️  No backup created (workflows directory not found)")
    
    # Fix workflows
    print("\n🔧 Fixing workflow JSON issues...")
    result = fixer.fix_all_workflows()
    
    if result['success']:
        print(f"✅ Processing complete!")
        print(f"   Files processed: {result['files_processed']}")
        print(f"   Files fixed: {result['files_fixed']}")
        
        if result['fixes_applied']:
            print("\n🎯 Fixes applied:")
            for fix in result['fixes_applied']:
                print(f"   • {fix}")
        
        if result['errors_found']:
            print("\n⚠️  Errors encountered:")
            for error in result['errors_found']:
                print(f"   • {error}")
        
        if result['files_fixed'] > 0:
            print("\n✨ JSON validation issues have been fixed!")
            print("   The 'Send Health Alert' node should now work properly.")
        else:
            print("\n✅ No JSON issues found in workflows.")
    
    else:
        print(f"❌ Error: {result['error']}")
        return 1
    
    print("\n🚀 Next steps:")
    print("   1. Restart n8n: sudo systemctl restart ai-video-renderer")
    print("   2. Test the health alert workflow")
    print("   3. Monitor logs for any remaining issues")
    
    return 0

if __name__ == "__main__":
    exit(main())