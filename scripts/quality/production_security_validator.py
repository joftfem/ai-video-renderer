#!/usr/bin/env python3
"""
Production Security Validator

Enhanced security validation for production environment readiness.
Validates configuration, credentials, and security settings.
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import logging
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SecurityIssue:
    """Represents a security validation issue."""
    severity: str  # 'critical', 'high', 'medium', 'low'
    category: str
    message: str
    recommendation: str
    affected_component: str


@dataclass
class ValidationResult:
    """Result of security validation."""
    passed: bool
    score: int  # 0-100
    issues: List[SecurityIssue]
    summary: Dict[str, Any]


class ProductionSecurityValidator:
    """Validates production environment security configuration."""
    
    def __init__(self, env_file_path: str = ".env.n8n"):
        self.env_file_path = Path(env_file_path)
        self.env_vars = self._load_environment_variables()
        self.issues: List[SecurityIssue] = []
        
    def _load_environment_variables(self) -> Dict[str, str]:
        """Load environment variables from file."""
        env_vars = {}
        
        if not self.env_file_path.exists():
            logger.warning(f"Environment file not found: {self.env_file_path}")
            return env_vars
        
        try:
            with open(self.env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            logger.error(f"Error loading environment file: {e}")
        
        return env_vars
    
    def validate_production_readiness(self) -> ValidationResult:
        """Comprehensive production readiness validation."""
        logger.info("🔒 Starting production security validation...")
        
        # Run all validation checks
        self._validate_debug_settings()
        self._validate_api_credentials()
        self._validate_security_settings()
        self._validate_database_security()
        self._validate_network_security()
        self._validate_encryption_settings()
        self._validate_rate_limiting()
        self._validate_monitoring_config()
        
        # Calculate overall score
        score = self._calculate_security_score()
        passed = score >= 85 and not any(issue.severity == 'critical' for issue in self.issues)
        
        # Generate summary
        summary = self._generate_summary()
        
        return ValidationResult(
            passed=passed,
            score=score,
            issues=self.issues,
            summary=summary
        )
    
    def _validate_debug_settings(self) -> None:
        """Validate debug and development settings."""
        debug_checks = [
            ('N8N_LOG_LEVEL', ['debug', 'DEBUG'], 'N8N log level should not be DEBUG in production'),
            ('DEBUG_MODE', ['true', 'True', 'TRUE'], 'Debug mode must be disabled in production'),
            ('N8N_DIAGNOSTICS_ENABLED', ['true', 'True', 'TRUE'], 'N8N diagnostics should be disabled in production'),
            ('VERTEX_AI_DEBUG', ['true', 'True', 'TRUE'], 'Vertex AI debug should be disabled in production')
        ]
        
        for var_name, dangerous_values, message in debug_checks:
            value = self.env_vars.get(var_name, '').lower()
            if value in [v.lower() for v in dangerous_values]:
                self.issues.append(SecurityIssue(
                    severity='high',
                    category='debug_settings',
                    message=message,
                    recommendation=f'Set {var_name}=false or remove the variable',
                    affected_component=var_name
                ))
    
    def _validate_api_credentials(self) -> None:
        """Validate API credentials and keys."""
        required_credentials = {
            'YOUTUBE_CLIENT_ID': 'YouTube OAuth Client ID',
            'YOUTUBE_CLIENT_SECRET': 'YouTube OAuth Client Secret',
            'YOUTUBE_REFRESH_TOKEN': 'YouTube Refresh Token',
            'GOOGLE_API_KEY': 'Google API Key',
            'ELEVENLABS_KEY': 'ElevenLabs API Key',
            'TELEGRAM_BOT_TOKEN': 'Telegram Bot Token',
            'DISCORD_WEBHOOK_URL': 'Discord Webhook URL'
        }
        
        placeholder_patterns = [
            'your_', 'placeholder', 'example', 'test_', 'demo_',
            'changeme', 'replace_this', 'add_your_'
        ]
        
        for var_name, description in required_credentials.items():
            value = self.env_vars.get(var_name, '')
            
            # Check if credential is missing
            if not value:
                self.issues.append(SecurityIssue(
                    severity='critical',
                    category='missing_credentials',
                    message=f'Missing required credential: {description}',
                    recommendation=f'Set {var_name} with valid production credential',
                    affected_component=var_name
                ))
                continue
            
            # Check for placeholder values
            if any(pattern in value.lower() for pattern in placeholder_patterns):
                self.issues.append(SecurityIssue(
                    severity='critical',
                    category='placeholder_credentials',
                    message=f'Placeholder value detected for {description}',
                    recommendation=f'Replace {var_name} with actual production credential',
                    affected_component=var_name
                ))
            
            # Validate credential format
            self._validate_credential_format(var_name, value)
    
    def _validate_credential_format(self, var_name: str, value: str) -> None:
        """Validate specific credential formats."""
        validations = {
            'YOUTUBE_CLIENT_ID': (r'^[0-9]+-[a-zA-Z0-9]+\.apps\.googleusercontent\.com$', 'Invalid YouTube Client ID format'),
            'YOUTUBE_CLIENT_SECRET': (r'^GOCSPX-[a-zA-Z0-9_-]+$', 'Invalid YouTube Client Secret format'),
            'GOOGLE_API_KEY': (r'^AIza[a-zA-Z0-9_-]{35}$', 'Invalid Google API Key format'),
            'TELEGRAM_BOT_TOKEN': (r'^[0-9]+:[a-zA-Z0-9_-]+$', 'Invalid Telegram Bot Token format'),
            'DISCORD_WEBHOOK_URL': (r'^https://discord\.com/api/webhooks/[0-9]+/[a-zA-Z0-9_-]+$', 'Invalid Discord Webhook URL format')
        }
        
        if var_name in validations:
            pattern, error_message = validations[var_name]
            if not re.match(pattern, value):
                self.issues.append(SecurityIssue(
                    severity='medium',
                    category='credential_format',
                    message=f'{error_message}: {var_name}',
                    recommendation=f'Verify {var_name} format matches expected pattern',
                    affected_component=var_name
                ))
    
    def _validate_security_settings(self) -> None:
        """Validate security configuration settings."""
        security_checks = [
            ('N8N_BASIC_AUTH_ACTIVE', 'true', 'N8N basic authentication should be enabled in production'),
            ('N8N_USER_MANAGEMENT_DISABLED', 'false', 'N8N user management should be enabled in production'),
            ('INPUT_SANITIZATION', 'true', 'Input sanitization must be enabled'),
            ('SECURE_DELETE_PASSES', '3', 'Secure delete should use multiple passes'),
            ('MONITORING_ENABLED', 'true', 'Monitoring must be enabled in production')
        ]
        
        for var_name, expected_value, message in security_checks:
            actual_value = self.env_vars.get(var_name, '').lower()
            if actual_value != expected_value.lower():
                self.issues.append(SecurityIssue(
                    severity='high',
                    category='security_settings',
                    message=message,
                    recommendation=f'Set {var_name}={expected_value}',
                    affected_component=var_name
                ))
    
    def _validate_database_security(self) -> None:
        """Validate database security configuration."""
        db_type = self.env_vars.get('DB_TYPE', 'sqlite').lower()
        
        if db_type == 'sqlite':
            db_path = self.env_vars.get('DB_SQLITE_DATABASE', '')
            if db_path and not db_path.startswith('/app/'):
                self.issues.append(SecurityIssue(
                    severity='medium',
                    category='database_security',
                    message='SQLite database should be in secure application directory',
                    recommendation='Move database to /app/ directory with proper permissions',
                    affected_component='DB_SQLITE_DATABASE'
                ))
    
    def _validate_network_security(self) -> None:
        """Validate network security settings."""
        # Check N8N host binding
        n8n_host = self.env_vars.get('N8N_HOST', '0.0.0.0')
        if n8n_host == '0.0.0.0':
            self.issues.append(SecurityIssue(
                severity='medium',
                category='network_security',
                message='N8N bound to all interfaces (0.0.0.0)',
                recommendation='Consider binding to specific interface for better security',
                affected_component='N8N_HOST'
            ))
        
        # Check protocol
        n8n_protocol = self.env_vars.get('N8N_PROTOCOL', 'http').lower()
        if n8n_protocol != 'https':
            self.issues.append(SecurityIssue(
                severity='high',
                category='network_security',
                message='N8N should use HTTPS in production',
                recommendation='Set N8N_PROTOCOL=https and configure SSL certificates',
                affected_component='N8N_PROTOCOL'
            ))
    
    def _validate_encryption_settings(self) -> None:
        """Validate encryption configuration."""
        encryption_key = self.env_vars.get('N8N_ENCRYPTION_KEY', '')
        
        if not encryption_key:
            self.issues.append(SecurityIssue(
                severity='critical',
                category='encryption',
                message='N8N encryption key is missing',
                recommendation='Generate and set a strong N8N_ENCRYPTION_KEY',
                affected_component='N8N_ENCRYPTION_KEY'
            ))
        elif len(encryption_key) < 32:
            self.issues.append(SecurityIssue(
                severity='high',
                category='encryption',
                message='N8N encryption key is too short',
                recommendation='Use encryption key with at least 32 characters',
                affected_component='N8N_ENCRYPTION_KEY'
            ))
    
    def _validate_rate_limiting(self) -> None:
        """Validate rate limiting configuration."""
        rate_limit = self.env_vars.get('RATE_LIMIT_RPM', '60')
        
        try:
            rate_limit_value = int(rate_limit)
            if rate_limit_value > 100:
                self.issues.append(SecurityIssue(
                    severity='medium',
                    category='rate_limiting',
                    message='Rate limit may be too high for production',
                    recommendation='Consider lowering RATE_LIMIT_RPM for better security',
                    affected_component='RATE_LIMIT_RPM'
                ))
        except ValueError:
            self.issues.append(SecurityIssue(
                severity='medium',
                category='rate_limiting',
                message='Invalid rate limit configuration',
                recommendation='Set RATE_LIMIT_RPM to a valid integer value',
                affected_component='RATE_LIMIT_RPM'
            ))
    
    def _validate_monitoring_config(self) -> None:
        """Validate monitoring and alerting configuration."""
        monitoring_vars = [
            'TELEGRAM_BOT_TOKEN',
            'DISCORD_WEBHOOK_URL',
            'MONITORING_ENABLED'
        ]
        
        missing_monitoring = []
        for var in monitoring_vars:
            if not self.env_vars.get(var):
                missing_monitoring.append(var)
        
        if missing_monitoring:
            self.issues.append(SecurityIssue(
                severity='medium',
                category='monitoring',
                message=f'Missing monitoring configuration: {", ".join(missing_monitoring)}',
                recommendation='Configure all monitoring and alerting channels',
                affected_component='monitoring_config'
            ))
    
    def _calculate_security_score(self) -> int:
        """Calculate overall security score (0-100)."""
        base_score = 100
        
        severity_penalties = {
            'critical': 25,
            'high': 15,
            'medium': 8,
            'low': 3
        }
        
        for issue in self.issues:
            penalty = severity_penalties.get(issue.severity, 5)
            base_score -= penalty
        
        return max(0, base_score)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate validation summary."""
        severity_counts = {}
        category_counts = {}
        
        for issue in self.issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1
        
        return {
            'total_issues': len(self.issues),
            'severity_breakdown': severity_counts,
            'category_breakdown': category_counts,
            'validation_timestamp': datetime.now().isoformat(),
            'environment_file': str(self.env_file_path),
            'total_env_vars': len(self.env_vars)
        }
    
    def generate_report(self, result: ValidationResult) -> str:
        """Generate human-readable validation report."""
        report = []
        report.append("🔒 PRODUCTION SECURITY VALIDATION REPORT")
        report.append("=" * 50)
        report.append(f"Validation Time: {result.summary['validation_timestamp']}")
        report.append(f"Security Score: {result.score}/100")
        report.append(f"Status: {'✅ PASSED' if result.passed else '❌ FAILED'}")
        report.append("")
        
        if result.issues:
            report.append("🚨 SECURITY ISSUES FOUND:")
            report.append("-" * 30)
            
            # Group issues by severity
            by_severity = {}
            for issue in result.issues:
                if issue.severity not in by_severity:
                    by_severity[issue.severity] = []
                by_severity[issue.severity].append(issue)
            
            severity_order = ['critical', 'high', 'medium', 'low']
            severity_icons = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🔵'
            }
            
            for severity in severity_order:
                if severity in by_severity:
                    report.append(f"\n{severity_icons[severity]} {severity.upper()} ISSUES:")
                    for issue in by_severity[severity]:
                        report.append(f"  • {issue.message}")
                        report.append(f"    Component: {issue.affected_component}")
                        report.append(f"    Fix: {issue.recommendation}")
                        report.append("")
        else:
            report.append("✅ No security issues found!")
        
        report.append("\n📊 SUMMARY:")
        report.append(f"  • Total Issues: {result.summary['total_issues']}")
        report.append(f"  • Environment Variables: {result.summary['total_env_vars']}")
        
        if result.summary['severity_breakdown']:
            report.append("  • Issue Breakdown:")
            for severity, count in result.summary['severity_breakdown'].items():
                report.append(f"    - {severity.title()}: {count}")
        
        return "\n".join(report)


def main():
    """Main entry point for security validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Production Security Validator")
    parser.add_argument(
        '--env-file',
        default='.env.n8n',
        help='Path to environment file (default: .env.n8n)'
    )
    parser.add_argument(
        '--output',
        help='Output file for validation report'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = ProductionSecurityValidator(args.env_file)
    result = validator.validate_production_readiness()
    
    # Generate output
    if args.json:
        output = json.dumps({
            'passed': result.passed,
            'score': result.score,
            'issues': [
                {
                    'severity': issue.severity,
                    'category': issue.category,
                    'message': issue.message,
                    'recommendation': issue.recommendation,
                    'affected_component': issue.affected_component
                }
                for issue in result.issues
            ],
            'summary': result.summary
        }, indent=2)
    else:
        output = validator.generate_report(result)
    
    # Save or print output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Validation report saved to: {args.output}")
    else:
        print(output)
    
    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()