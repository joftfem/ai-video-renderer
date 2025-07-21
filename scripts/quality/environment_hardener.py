#!/usr/bin/env python3
"""
Environment Configuration Hardening Script

Automatically hardens production environment configuration by:
- Validating and fixing security settings
- Generating secure encryption keys
- Setting proper production defaults
- Creating backup of original configuration
"""

import os
import sys
import secrets
import string
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnvironmentHardener:
    """Hardens environment configuration for production deployment."""
    
    def __init__(self, env_file_path: str = ".env.n8n"):
        self.env_file_path = Path(env_file_path)
        self.backup_path = Path(f"{env_file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.env_vars: Dict[str, str] = {}
        self.changes_made: List[str] = []
        
    def load_environment(self) -> None:
        """Load current environment variables."""
        if not self.env_file_path.exists():
            logger.error(f"Environment file not found: {self.env_file_path}")
            sys.exit(1)
        
        try:
            with open(self.env_file_path, 'r') as f:
                content = f.read()
            
            # Parse environment variables while preserving comments and structure
            self.original_content = content
            self.env_vars = {}
            
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    self.env_vars[key.strip()] = value.strip()
                    
        except Exception as e:
            logger.error(f"Error loading environment file: {e}")
            sys.exit(1)
    
    def create_backup(self) -> None:
        """Create backup of original environment file."""
        try:
            shutil.copy2(self.env_file_path, self.backup_path)
            logger.info(f"✅ Backup created: {self.backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            sys.exit(1)
    
    def generate_secure_key(self, length: int = 32) -> str:
        """Generate cryptographically secure random key."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def harden_security_settings(self) -> None:
        """Apply security hardening to configuration."""
        logger.info("🔒 Applying security hardening...")
        
        # Security settings that should be enforced
        security_settings = {
            # N8N Security
            'N8N_BASIC_AUTH_ACTIVE': 'true',
            'N8N_USER_MANAGEMENT_DISABLED': 'false',
            'N8N_DIAGNOSTICS_ENABLED': 'false',
            'N8N_VERSION_NOTIFICATIONS_ENABLED': 'false',
            'N8N_TEMPLATES_ENABLED': 'false',
            'N8N_ONBOARDING_FLOW_DISABLED': 'true',
            'N8N_METRICS': 'false',
            'N8N_LOG_LEVEL': 'info',
            
            # System Security
            'INPUT_SANITIZATION': 'true',
            'SECURE_DELETE_PASSES': '3',
            'MONITORING_ENABLED': 'true',
            
            # Privacy & Compliance
            'DEFAULT_UPLOAD_PRIVACY': 'private',
            'YOUTUBE_DEFAULT_PRIVACY': 'private',
            'STRICT_COMPLIANCE': 'true',
            
            # Rate Limiting
            'RATE_LIMIT_RPM': '60',
            'MAX_CONCURRENT_RENDERS': '3',
            'MAX_UPLOADS_PER_DAY': '3',
            
            # TTS Security
            'TTS_CACHE_ENABLED': 'true',
            'TTS_RATE_LIMIT_RPM': '20',
            
            # Vertex AI Security
            'VERTEX_AI_CACHE_ENABLED': 'true',
            'VERTEX_AI_RETRY_MAX': '3',
            'VERTEX_AI_RATE_LIMIT_RPM': '30'
        }
        
        for key, secure_value in security_settings.items():
            current_value = self.env_vars.get(key, '')
            if current_value.lower() != secure_value.lower():
                self.env_vars[key] = secure_value
                self.changes_made.append(f"Set {key}={secure_value}")
    
    def generate_encryption_keys(self) -> None:
        """Generate secure encryption keys if missing or weak."""
        logger.info("🔑 Checking encryption keys...")
        
        # N8N Encryption Key
        n8n_key = self.env_vars.get('N8N_ENCRYPTION_KEY', '')
        if not n8n_key or len(n8n_key) < 32:
            new_key = self.generate_secure_key(32)
            self.env_vars['N8N_ENCRYPTION_KEY'] = new_key
            self.changes_made.append("Generated new N8N_ENCRYPTION_KEY")
        
        # JWT Secret
        jwt_secret = self.env_vars.get('N8N_USER_MANAGEMENT_JWT_SECRET', '')
        if not jwt_secret or len(jwt_secret) < 32:
            new_secret = self.generate_secure_key(32)
            self.env_vars['N8N_USER_MANAGEMENT_JWT_SECRET'] = new_secret
            self.changes_made.append("Generated new N8N_USER_MANAGEMENT_JWT_SECRET")
    
    def validate_credentials(self) -> None:
        """Validate that production credentials are properly set."""
        logger.info("🔍 Validating credentials...")
        
        required_credentials = [
            'YOUTUBE_CLIENT_ID',
            'YOUTUBE_CLIENT_SECRET', 
            'YOUTUBE_REFRESH_TOKEN',
            'GOOGLE_API_KEY',
            'ELEVENLABS_KEY',
            'TELEGRAM_BOT_TOKEN',
            'DISCORD_WEBHOOK_URL'
        ]
        
        placeholder_patterns = [
            'your_', 'placeholder', 'example', 'test_', 'demo_',
            'changeme', 'replace_this', 'add_your_'
        ]
        
        missing_credentials = []
        placeholder_credentials = []
        
        for cred in required_credentials:
            value = self.env_vars.get(cred, '')
            if not value:
                missing_credentials.append(cred)
            elif any(pattern in value.lower() for pattern in placeholder_patterns):
                placeholder_credentials.append(cred)
        
        if missing_credentials:
            logger.warning(f"⚠️  Missing credentials: {', '.join(missing_credentials)}")
        
        if placeholder_credentials:
            logger.warning(f"⚠️  Placeholder credentials detected: {', '.join(placeholder_credentials)}")
    
    def optimize_performance_settings(self) -> None:
        """Optimize performance settings for production."""
        logger.info("⚡ Optimizing performance settings...")
        
        performance_settings = {
            # Memory Management
            'MAX_MEMORY_MB': '2048',
            
            # Caching
            'TTS_CACHE_TTL': '86400',
            'VERTEX_AI_CACHE_TTL': '3600',
            
            # Timeouts
            'VERTEX_AI_TIMEOUT': '60',
            'TTS_RETRY_BACKOFF': '2.0',
            'VERTEX_AI_RETRY_BACKOFF': '2.0',
            
            # Upload Optimization
            'BASE_UPLOAD_DELAY': '3600',
            'UPLOAD_DELAY_VARIATION': '1800'
        }
        
        for key, optimal_value in performance_settings.items():
            if key not in self.env_vars:
                self.env_vars[key] = optimal_value
                self.changes_made.append(f"Added {key}={optimal_value}")
    
    def add_security_headers(self) -> None:
        """Add security-related environment variables."""
        logger.info("🛡️  Adding security headers...")
        
        security_additions = {
            # Security Headers
            'SECURITY_HEADERS_ENABLED': 'true',
            'CORS_ENABLED': 'false',
            'CSRF_PROTECTION': 'true',
            
            # Audit & Logging
            'AUDIT_LOG_ENABLED': 'true',
            'SECURITY_LOG_LEVEL': 'info',
            'ACCESS_LOG_ENABLED': 'true',
            
            # Backup & Recovery
            'AUTO_BACKUP_ENABLED': 'true',
            'BACKUP_RETENTION_DAYS': '30',
            
            # Health Monitoring
            'HEALTH_CHECK_ENABLED': 'true',
            'HEALTH_CHECK_INTERVAL': '300',
            
            # Error Handling
            'ERROR_REPORTING_ENABLED': 'true',
            'DETAILED_ERRORS': 'false'
        }
        
        for key, value in security_additions.items():
            if key not in self.env_vars:
                self.env_vars[key] = value
                self.changes_made.append(f"Added security setting {key}={value}")
    
    def write_hardened_config(self) -> None:
        """Write the hardened configuration back to file."""
        logger.info("💾 Writing hardened configuration...")
        
        try:
            # Read original content to preserve structure
            lines = self.original_content.split('\n')
            new_lines = []
            processed_vars = set()
            
            # Process existing lines
            for line in lines:
                if line.strip() and not line.strip().startswith('#') and '=' in line:
                    key = line.split('=', 1)[0].strip()
                    if key in self.env_vars:
                        new_lines.append(f"{key}={self.env_vars[key]}")
                        processed_vars.add(key)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            # Add new variables at the end
            new_vars = set(self.env_vars.keys()) - processed_vars
            if new_vars:
                new_lines.append("")
                new_lines.append("# =================================================================== ")
                new_lines.append("# 🔒 SECURITY HARDENING ADDITIONS")
                new_lines.append("# =================================================================== ")
                
                for var in sorted(new_vars):
                    new_lines.append(f"{var}={self.env_vars[var]}")
            
            # Write to file
            with open(self.env_file_path, 'w') as f:
                f.write('\n'.join(new_lines))
            
            logger.info(f"✅ Hardened configuration written to {self.env_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to write hardened configuration: {e}")
            sys.exit(1)
    
    def generate_hardening_report(self) -> str:
        """Generate a report of changes made during hardening."""
        report = []
        report.append("🔒 ENVIRONMENT HARDENING REPORT")
        report.append("=" * 50)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append(f"Environment File: {self.env_file_path}")
        report.append(f"Backup Created: {self.backup_path}")
        report.append(f"Total Changes: {len(self.changes_made)}")
        report.append("")
        
        if self.changes_made:
            report.append("📝 CHANGES MADE:")
            report.append("-" * 20)
            for i, change in enumerate(self.changes_made, 1):
                report.append(f"{i:2d}. {change}")
        else:
            report.append("✅ No changes needed - configuration already hardened")
        
        report.append("")
        report.append("🔍 NEXT STEPS:")
        report.append("1. Review the changes above")
        report.append("2. Test the application with new settings")
        report.append("3. Run production security validation")
        report.append("4. Monitor logs for any issues")
        report.append("")
        report.append("⚠️  IMPORTANT:")
        report.append("- Keep the backup file safe")
        report.append("- Update any external configurations")
        report.append("- Restart services to apply changes")
        
        return "\n".join(report)
    
    def run_hardening(self) -> None:
        """Execute the complete hardening process."""
        logger.info("🚀 Starting environment hardening process...")
        
        # Load current configuration
        self.load_environment()
        
        # Create backup
        self.create_backup()
        
        # Apply hardening steps
        self.harden_security_settings()
        self.generate_encryption_keys()
        self.validate_credentials()
        self.optimize_performance_settings()
        self.add_security_headers()
        
        # Write hardened configuration
        self.write_hardened_config()
        
        # Generate and display report
        report = self.generate_hardening_report()
        print("\n" + report)
        
        # Save report to file
        report_file = f"hardening_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"📄 Hardening report saved to: {report_file}")
        logger.info("🎉 Environment hardening completed successfully!")


def main():
    """Main entry point for environment hardening."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Environment Configuration Hardener")
    parser.add_argument(
        '--env-file',
        default='.env.n8n',
        help='Path to environment file (default: .env.n8n)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🔍 Running in dry-run mode - no changes will be made")
        # TODO: Implement dry-run functionality
        logger.info("Dry-run mode not yet implemented")
        return
    
    # Run hardening
    hardener = EnvironmentHardener(args.env_file)
    hardener.run_hardening()


if __name__ == "__main__":
    main()