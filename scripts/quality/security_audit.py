#!/usr/bin/env python3
"""
Security Audit Automation Tool

Comprehensive security scanning and vulnerability assessment for the AI Video Renderer.
Provides automated security analysis including:
- Dependency vulnerability scanning
- Code security analysis
- Configuration security review
- API security assessment
- Infrastructure security checks
- Compliance validation
- Security best practices verification
"""

import os
import sys
import json
import subprocess
import argparse
import hashlib
import re
import yaml
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import tempfile
import shutil
import base64
from urllib.parse import urlparse
import socket
import ssl
import secrets
import string

try:
    import bandit
    from bandit.core import manager as bandit_manager
    from bandit.core import config as bandit_config
    BANDIT_AVAILABLE = True
except ImportError:
    BANDIT_AVAILABLE = False

try:
    import safety
    SAFETY_AVAILABLE = True
except ImportError:
    SAFETY_AVAILABLE = False

try:
    import semgrep
    SEMGREP_AVAILABLE = True
except ImportError:
    SEMGREP_AVAILABLE = False


class SecuritySeverity(Enum):
    """Security issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityCategory(Enum):
    """Security issue categories."""
    VULNERABILITY = "vulnerability"
    MISCONFIGURATION = "misconfiguration"
    WEAK_CRYPTO = "weak_cryptography"
    INJECTION = "injection"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_EXPOSURE = "data_exposure"
    INSECURE_COMMUNICATION = "insecure_communication"
    DEPENDENCY = "dependency"
    INFRASTRUCTURE = "infrastructure"
    COMPLIANCE = "compliance"


@dataclass
class SecurityIssue:
    """Represents a security issue found during audit."""
    id: str
    title: str
    description: str
    severity: SecuritySeverity
    category: SecurityCategory
    file_path: Optional[str]
    line_number: Optional[int]
    code_snippet: Optional[str]
    cwe_id: Optional[str]
    cvss_score: Optional[float]
    remediation: str
    references: List[str]
    confidence: str
    tool: str
    timestamp: str


@dataclass
class SecurityMetrics:
    """Security audit metrics and statistics."""
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    info_issues: int
    files_scanned: int
    lines_scanned: int
    dependencies_scanned: int
    vulnerable_dependencies: int
    security_score: float
    compliance_score: float
    scan_duration: float


@dataclass
class SecurityReport:
    """Comprehensive security audit report."""
    timestamp: str
    project_path: str
    scan_id: str
    metrics: SecurityMetrics
    issues: List[SecurityIssue]
    dependency_vulnerabilities: List[Dict[str, Any]]
    configuration_issues: List[Dict[str, Any]]
    compliance_results: Dict[str, Any]
    recommendations: List[str]
    risk_assessment: Dict[str, Any]
    remediation_plan: List[Dict[str, Any]]


class DependencyScanner:
    """Scans dependencies for known vulnerabilities."""
    
    def __init__(self):
        self.vulnerabilities = []
        
    def scan_python_dependencies(self, project_path: Path) -> List[Dict[str, Any]]:
        """Scan Python dependencies for vulnerabilities."""
        vulnerabilities = []
        
        # Check for requirements files
        req_files = [
            project_path / "requirements.txt",
            project_path / "requirements-dev.txt",
            project_path / "pyproject.toml",
            project_path / "Pipfile",
            project_path / "setup.py"
        ]
        
        for req_file in req_files:
            if req_file.exists():
                vulnerabilities.extend(self._scan_requirements_file(req_file))
        
        # Use Safety if available
        if SAFETY_AVAILABLE:
            vulnerabilities.extend(self._scan_with_safety(project_path))
        
        return vulnerabilities
    
    def _scan_requirements_file(self, req_file: Path) -> List[Dict[str, Any]]:
        """Scan a specific requirements file."""
        vulnerabilities = []
        
        try:
            with open(req_file, 'r') as f:
                content = f.read()
            
            # Parse dependencies
            dependencies = self._parse_dependencies(content, req_file.suffix)
            
            # Check each dependency against vulnerability database
            for dep in dependencies:
                vulns = self._check_dependency_vulnerabilities(dep)
                vulnerabilities.extend(vulns)
                
        except Exception as e:
            print(f"⚠️ Error scanning {req_file}: {e}")
        
        return vulnerabilities
    
    def _parse_dependencies(self, content: str, file_type: str) -> List[Dict[str, str]]:
        """Parse dependencies from file content."""
        dependencies = []
        
        if file_type == '.txt':
            # Parse requirements.txt format
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name and version
                    match = re.match(r'^([a-zA-Z0-9_-]+)([>=<!=]+)([0-9.]+)', line)
                    if match:
                        dependencies.append({
                            'name': match.group(1),
                            'version': match.group(3),
                            'operator': match.group(2)
                        })
        
        elif file_type == '.toml':
            # Parse pyproject.toml (simplified)
            try:
                import toml
                data = toml.loads(content)
                deps = data.get('project', {}).get('dependencies', [])
                for dep in deps:
                    match = re.match(r'^([a-zA-Z0-9_-]+)([>=<!=]+)([0-9.]+)', dep)
                    if match:
                        dependencies.append({
                            'name': match.group(1),
                            'version': match.group(3),
                            'operator': match.group(2)
                        })
            except ImportError:
                pass
        
        return dependencies
    
    def _check_dependency_vulnerabilities(self, dependency: Dict[str, str]) -> List[Dict[str, Any]]:
        """Check a dependency against vulnerability databases."""
        vulnerabilities = []
        
        # Check against PyUp.io safety database (simplified)
        known_vulns = {
            'django': {
                '3.0.0': {
                    'id': 'CVE-2020-9402',
                    'description': 'SQL injection vulnerability',
                    'severity': 'high',
                    'cvss': 8.8
                }
            },
            'requests': {
                '2.19.0': {
                    'id': 'CVE-2018-18074',
                    'description': 'Credential exposure vulnerability',
                    'severity': 'medium',
                    'cvss': 6.5
                }
            },
            'pyyaml': {
                '5.3.0': {
                    'id': 'CVE-2020-1747',
                    'description': 'Arbitrary code execution',
                    'severity': 'critical',
                    'cvss': 9.8
                }
            }
        }
        
        dep_name = dependency['name'].lower()
        dep_version = dependency['version']
        
        if dep_name in known_vulns:
            for vuln_version, vuln_info in known_vulns[dep_name].items():
                if self._version_affected(dep_version, vuln_version, dependency.get('operator', '==')):
                    vulnerabilities.append({
                        'dependency': dep_name,
                        'version': dep_version,
                        'vulnerability_id': vuln_info['id'],
                        'description': vuln_info['description'],
                        'severity': vuln_info['severity'],
                        'cvss_score': vuln_info['cvss'],
                        'remediation': f"Update {dep_name} to a patched version"
                    })
        
        return vulnerabilities
    
    def _version_affected(self, installed_version: str, vuln_version: str, operator: str) -> bool:
        """Check if installed version is affected by vulnerability."""
        # Simplified version comparison
        try:
            installed_parts = [int(x) for x in installed_version.split('.')]
            vuln_parts = [int(x) for x in vuln_version.split('.')]
            
            if operator in ['==', '=']:
                return installed_parts == vuln_parts
            elif operator in ['<=', '=<']:
                return installed_parts <= vuln_parts
            elif operator == '<':
                return installed_parts < vuln_parts
            elif operator in ['>=', '=>']:
                return installed_parts >= vuln_parts
            elif operator == '>':
                return installed_parts > vuln_parts
            
        except ValueError:
            return False
        
        return False
    
    def _scan_with_safety(self, project_path: Path) -> List[Dict[str, Any]]:
        """Scan using Safety tool if available."""
        vulnerabilities = []
        
        try:
            # Run safety check
            result = subprocess.run(
                ['safety', 'check', '--json'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # Parse safety output
                try:
                    safety_data = json.loads(result.stdout)
                    for vuln in safety_data:
                        vulnerabilities.append({
                            'dependency': vuln.get('package'),
                            'version': vuln.get('installed_version'),
                            'vulnerability_id': vuln.get('vulnerability_id'),
                            'description': vuln.get('advisory'),
                            'severity': self._map_safety_severity(vuln.get('severity')),
                            'cvss_score': None,
                            'remediation': f"Update to version {vuln.get('safe_versions', 'latest')}"
                        })
                except json.JSONDecodeError:
                    pass
                    
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return vulnerabilities
    
    def _map_safety_severity(self, safety_severity: str) -> str:
        """Map Safety severity to our severity levels."""
        mapping = {
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        }
        return mapping.get(safety_severity.lower(), 'medium')


class CodeSecurityScanner:
    """Scans source code for security vulnerabilities."""
    
    def __init__(self):
        self.issues = []
        
    def scan_code(self, project_path: Path) -> List[SecurityIssue]:
        """Scan source code for security issues."""
        issues = []
        
        # Scan with Bandit if available
        if BANDIT_AVAILABLE:
            issues.extend(self._scan_with_bandit(project_path))
        
        # Custom security pattern scanning
        issues.extend(self._scan_security_patterns(project_path))
        
        # Scan for hardcoded secrets
        issues.extend(self._scan_secrets(project_path))
        
        # Scan for insecure configurations
        issues.extend(self._scan_configurations(project_path))
        
        return issues
    
    def _scan_with_bandit(self, project_path: Path) -> List[SecurityIssue]:
        """Scan using Bandit static analysis tool."""
        issues = []
        
        try:
            # Configure Bandit
            conf = bandit_config.BanditConfig()
            b_mgr = bandit_manager.BanditManager(conf, 'file')
            
            # Scan Python files
            python_files = list(project_path.rglob('*.py'))
            for py_file in python_files:
                try:
                    b_mgr.discover_files([str(py_file)])
                except Exception:
                    continue
            
            b_mgr.run_tests()
            
            # Convert Bandit results to our format
            for result in b_mgr.get_issue_list():
                issue = SecurityIssue(
                    id=f"bandit_{result.test_id}_{hashlib.md5(str(result).encode()).hexdigest()[:8]}",
                    title=result.test,
                    description=result.text,
                    severity=self._map_bandit_severity(result.severity),
                    category=self._map_bandit_category(result.test),
                    file_path=result.fname,
                    line_number=result.lineno,
                    code_snippet=result.get_code(),
                    cwe_id=getattr(result, 'cwe', None),
                    cvss_score=None,
                    remediation=self._get_bandit_remediation(result.test),
                    references=[],
                    confidence=result.confidence.name.lower(),
                    tool='bandit',
                    timestamp=datetime.now().isoformat()
                )
                issues.append(issue)
                
        except Exception as e:
            print(f"⚠️ Error running Bandit: {e}")
        
        return issues
    
    def _scan_security_patterns(self, project_path: Path) -> List[SecurityIssue]:
        """Scan for common security anti-patterns."""
        issues = []
        
        # Security patterns to detect
        patterns = {
            'sql_injection': {
                'pattern': r'(execute|query)\s*\(\s*["\'].*%.*["\']',
                'severity': SecuritySeverity.HIGH,
                'category': SecurityCategory.INJECTION,
                'description': 'Potential SQL injection vulnerability'
            },
            'command_injection': {
                'pattern': r'(os\.system|subprocess\.call|subprocess\.run)\s*\(.*\+',
                'severity': SecuritySeverity.HIGH,
                'category': SecurityCategory.INJECTION,
                'description': 'Potential command injection vulnerability'
            },
            'hardcoded_password': {
                'pattern': r'(password|passwd|pwd)\s*=\s*["\'][^"\'
]{8,}["\']',
                'severity': SecuritySeverity.CRITICAL,
                'category': SecurityCategory.AUTHENTICATION,
                'description': 'Hardcoded password detected'
            },
            'weak_random': {
                'pattern': r'random\.(random|randint|choice)',
                'severity': SecuritySeverity.MEDIUM,
                'category': SecurityCategory.WEAK_CRYPTO,
                'description': 'Use of weak random number generator'
            },
            'debug_mode': {
                'pattern': r'debug\s*=\s*True',
                'severity': SecuritySeverity.MEDIUM,
                'category': SecurityCategory.MISCONFIGURATION,
                'description': 'Debug mode enabled in production'
            }
        }
        
        # Scan all Python files
        python_files = list(project_path.rglob('*.py'))
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for pattern_name, pattern_info in patterns.items():
                    matches = re.finditer(pattern_info['pattern'], content, re.IGNORECASE)
                    
                    for match in matches:
                        # Find line number
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = lines[line_num - 1] if line_num <= len(lines) else ''
                        
                        issue = SecurityIssue(
                            id=f"pattern_{pattern_name}_{hashlib.md5(f'{py_file}_{line_num}'.encode()).hexdigest()[:8]}",
                            title=f"Security Pattern: {pattern_name.replace('_', ' ').title()}",
                            description=pattern_info['description'],
                            severity=pattern_info['severity'],
                            category=pattern_info['category'],
                            file_path=str(py_file.relative_to(project_path)),
                            line_number=line_num,
                            code_snippet=line_content.strip(),
                            cwe_id=None,
                            cvss_score=None,
                            remediation=self._get_pattern_remediation(pattern_name),
                            references=[],
                            confidence='medium',
                            tool='custom_patterns',
                            timestamp=datetime.now().isoformat()
                        )
                        issues.append(issue)
                        
            except Exception as e:
                print(f"⚠️ Error scanning {py_file}: {e}")
        
        return issues
    
    def _scan_secrets(self, project_path: Path) -> List[SecurityIssue]:
        """Scan for hardcoded secrets and credentials."""
        issues = []
        
        # Secret patterns
        secret_patterns = {
            'api_key': r'(api[_-]?key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9]{20,}["\']',
            'aws_access_key': r'AKIA[0-9A-Z]{16}',
            'aws_secret_key': r'[0-9a-zA-Z/+]{40}',
            'github_token': r'ghp_[a-zA-Z0-9]{36}',
            'jwt_token': r'eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
            'private_key': r'-----BEGIN (RSA )?PRIVATE KEY-----',
            'database_url': r'(mysql|postgresql|mongodb)://[^\s"\'
]+',
            'generic_secret': r'(secret|token|key|password)\s*[=:]\s*["\'][a-zA-Z0-9!@#$%^&*()_+-=]{16,}["\']'
        }
        
        # File types to scan
        file_patterns = ['*.py', '*.js', '*.json', '*.yaml', '*.yml', '*.env', '*.config']
        
        for pattern in file_patterns:
            for file_path in project_path.rglob(pattern):
                # Skip certain directories
                if any(skip in str(file_path) for skip in ['.git', '__pycache__', 'node_modules', '.venv']):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                    
                    for secret_type, secret_pattern in secret_patterns.items():
                        matches = re.finditer(secret_pattern, content, re.IGNORECASE)
                        
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            line_content = lines[line_num - 1] if line_num <= len(lines) else ''
                            
                            # Mask the secret in the snippet
                            masked_line = re.sub(r'["\'][^"\'
]{8,}["\']', '"***REDACTED***"', line_content)
                            
                            issue = SecurityIssue(
                                id=f"secret_{secret_type}_{hashlib.md5(f'{file_path}_{line_num}'.encode()).hexdigest()[:8]}",
                                title=f"Hardcoded Secret: {secret_type.replace('_', ' ').title()}",
                                description=f"Potential {secret_type.replace('_', ' ')} found in source code",
                                severity=SecuritySeverity.CRITICAL,
                                category=SecurityCategory.DATA_EXPOSURE,
                                file_path=str(file_path.relative_to(project_path)),
                                line_number=line_num,
                                code_snippet=masked_line.strip(),
                                cwe_id='CWE-798',
                                cvss_score=9.8,
                                remediation="Move secrets to environment variables or secure secret management system",
                                references=[
                                    "https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password"
                                ],
                                confidence='high',
                                tool='secret_scanner',
                                timestamp=datetime.now().isoformat()
                            )
                            issues.append(issue)
                            
                except Exception as e:
                    print(f"⚠️ Error scanning {file_path} for secrets: {e}")
        
        return issues
    
    def _scan_configurations(self, project_path: Path) -> List[SecurityIssue]:
        """Scan configuration files for security issues."""
        issues = []
        
        # Configuration security checks
        config_checks = {
            'docker': self._check_docker_security,
            'yaml': self._check_yaml_security,
            'env': self._check_env_security,
            'nginx': self._check_nginx_security
        }
        
        for config_type, check_func in config_checks.items():
            try:
                config_issues = check_func(project_path)
                issues.extend(config_issues)
            except Exception as e:
                print(f"⚠️ Error checking {config_type} configuration: {e}")
        
        return issues
    
    def _check_docker_security(self, project_path: Path) -> List[SecurityIssue]:
        """Check Docker configuration security."""
        issues = []
        
        dockerfile_paths = list(project_path.rglob('Dockerfile*'))
        
        for dockerfile in dockerfile_paths:
            try:
                with open(dockerfile, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Check for security issues
                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    
                    # Running as root
                    if line.startswith('USER root') or (line.startswith('RUN') and 'sudo' in line):
                        issues.append(SecurityIssue(
                            id=f"docker_root_{hashlib.md5(f'{dockerfile}_{i}'.encode()).hexdigest()[:8]}",
                            title="Docker: Running as Root",
                            description="Container running as root user",
                            severity=SecuritySeverity.MEDIUM,
                            category=SecurityCategory.MISCONFIGURATION,
                            file_path=str(dockerfile.relative_to(project_path)),
                            line_number=i,
                            code_snippet=line,
                            cwe_id='CWE-250',
                            cvss_score=None,
                            remediation="Create and use a non-root user in the container",
                            references=[],
                            confidence='high',
                            tool='docker_scanner',
                            timestamp=datetime.now().isoformat()
                        ))
                    
                    # Exposed sensitive ports
                    if line.startswith('EXPOSE') and any(port in line for port in ['22', '3389', '5432', '3306']):
                        issues.append(SecurityIssue(
                            id=f"docker_port_{hashlib.md5(f'{dockerfile}_{i}'.encode()).hexdigest()[:8]}",
                            title="Docker: Sensitive Port Exposed",
                            description="Potentially sensitive port exposed",
                            severity=SecuritySeverity.MEDIUM,
                            category=SecurityCategory.MISCONFIGURATION,
                            file_path=str(dockerfile.relative_to(project_path)),
                            line_number=i,
                            code_snippet=line,
                            cwe_id=None,
                            cvss_score=None,
                            remediation="Review if port exposure is necessary and secure",
                            references=[],
                            confidence='medium',
                            tool='docker_scanner',
                            timestamp=datetime.now().isoformat()
                        ))
                        
            except Exception as e:
                print(f"⚠️ Error scanning Dockerfile {dockerfile}: {e}")
        
        return issues
    
    def _check_yaml_security(self, project_path: Path) -> List[SecurityIssue]:
        """Check YAML configuration security."""
        issues = []
        
        yaml_files = list(project_path.rglob('*.yml')) + list(project_path.rglob('*.yaml'))
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r') as f:
                    content = f.read()
                
                # Check for unsafe YAML loading
                if 'yaml.load(' in content and 'Loader=' not in content:
                    line_num = content[:content.find('yaml.load(')].count('\n') + 1
                    
                    issues.append(SecurityIssue(
                        id=f"yaml_unsafe_{hashlib.md5(f'{yaml_file}_{line_num}'.encode()).hexdigest()[:8]}",
                        title="YAML: Unsafe Loading",
                        description="Unsafe YAML loading detected",
                        severity=SecuritySeverity.HIGH,
                        category=SecurityCategory.INJECTION,
                        file_path=str(yaml_file.relative_to(project_path)),
                        line_number=line_num,
                        code_snippet=content.split('\n')[line_num - 1].strip(),
                        cwe_id='CWE-502',
                        cvss_score=8.1,
                        remediation="Use yaml.safe_load() instead of yaml.load()",
                        references=[
                            "https://security.snyk.io/vuln/SNYK-PYTHON-PYYAML-42159"
                        ],
                        confidence='high',
                        tool='yaml_scanner',
                        timestamp=datetime.now().isoformat()
                    ))
                    
            except Exception as e:
                print(f"⚠️ Error scanning YAML file {yaml_file}: {e}")
        
        return issues
    
    def _check_env_security(self, project_path: Path) -> List[SecurityIssue]:
        """Check environment file security."""
        issues = []
        
        env_files = list(project_path.rglob('.env*'))
        
        for env_file in env_files:
            # Check if .env files are in version control
            gitignore_path = project_path / '.gitignore'
            if gitignore_path.exists():
                with open(gitignore_path, 'r') as f:
                    gitignore_content = f.read()
                
                if '.env' not in gitignore_content:
                    issues.append(SecurityIssue(
                        id=f"env_vcs_{hashlib.md5(str(env_file).encode()).hexdigest()[:8]}",
                        title="Environment File in Version Control",
                        description="Environment file may be tracked in version control",
                        severity=SecuritySeverity.HIGH,
                        category=SecurityCategory.DATA_EXPOSURE,
                        file_path=str(env_file.relative_to(project_path)),
                        line_number=None,
                        code_snippet=None,
                        cwe_id='CWE-200',
                        cvss_score=None,
                        remediation="Add .env files to .gitignore",
                        references=[],
                        confidence='medium',
                        tool='env_scanner',
                        timestamp=datetime.now().isoformat()
                    ))
        
        return issues
    
    def _check_nginx_security(self, project_path: Path) -> List[SecurityIssue]:
        """Check Nginx configuration security."""
        issues = []
        
        nginx_files = list(project_path.rglob('nginx.conf')) + list(project_path.rglob('*.nginx'))
        
        for nginx_file in nginx_files:
            try:
                with open(nginx_file, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    
                    # Check for server_tokens on
                    if 'server_tokens on' in line:
                        issues.append(SecurityIssue(
                            id=f"nginx_tokens_{hashlib.md5(f'{nginx_file}_{i}'.encode()).hexdigest()[:8]}",
                            title="Nginx: Server Tokens Enabled",
                            description="Server version information exposed",
                            severity=SecuritySeverity.LOW,
                            category=SecurityCategory.DATA_EXPOSURE,
                            file_path=str(nginx_file.relative_to(project_path)),
                            line_number=i,
                            code_snippet=line,
                            cwe_id=None,
                            cvss_score=None,
                            remediation="Set 'server_tokens off;' to hide version information",
                            references=[],
                            confidence='high',
                            tool='nginx_scanner',
                            timestamp=datetime.now().isoformat()
                        ))
                        
            except Exception as e:
                print(f"⚠️ Error scanning Nginx file {nginx_file}: {e}")
        
        return issues
    
    def _map_bandit_severity(self, bandit_severity) -> SecuritySeverity:
        """Map Bandit severity to our severity levels."""
        mapping = {
            'LOW': SecuritySeverity.LOW,
            'MEDIUM': SecuritySeverity.MEDIUM,
            'HIGH': SecuritySeverity.HIGH
        }
        return mapping.get(bandit_severity.name, SecuritySeverity.MEDIUM)
    
    def _map_bandit_category(self, test_name: str) -> SecurityCategory:
        """Map Bandit test to security category."""
        category_mapping = {
            'hardcoded_password': SecurityCategory.AUTHENTICATION,
            'sql_injection': SecurityCategory.INJECTION,
            'shell_injection': SecurityCategory.INJECTION,
            'weak_cryptographic': SecurityCategory.WEAK_CRYPTO,
            'insecure_transport': SecurityCategory.INSECURE_COMMUNICATION,
        }
        
        for key, category in category_mapping.items():
            if key in test_name.lower():
                return category
        
        return SecurityCategory.VULNERABILITY
    
    def _get_bandit_remediation(self, test_name: str) -> str:
        """Get remediation advice for Bandit test."""
        remediation_mapping = {
            'hardcoded_password': "Use environment variables or secure credential storage",
            'sql_injection': "Use parameterized queries or ORM",
            'shell_injection': "Validate and sanitize input, use subprocess with shell=False",
            'weak_cryptographic': "Use strong cryptographic algorithms and libraries",
            'insecure_transport': "Use HTTPS/TLS for all communications",
        }
        
        for key, remediation in remediation_mapping.items():
            if key in test_name.lower():
                return remediation
        
        return "Review and fix the security issue according to best practices"
    
    def _get_pattern_remediation(self, pattern_name: str) -> str:
        """Get remediation advice for security pattern."""
        remediation_mapping = {
            'sql_injection': "Use parameterized queries or prepared statements",
            'command_injection': "Validate input and use subprocess.run() with shell=False",
            'hardcoded_password': "Use environment variables or secure credential storage",
            'weak_random': "Use secrets module for cryptographically secure random numbers",
            'debug_mode': "Disable debug mode in production environments"
        }
        
        return remediation_mapping.get(pattern_name, "Follow security best practices")


class ComplianceChecker:
    """Checks compliance with security standards and frameworks."""
    
    def __init__(self):
        self.compliance_results = {}
        
    def check_compliance(self, project_path: Path, issues: List[SecurityIssue]) -> Dict[str, Any]:
        """Check compliance with various security frameworks."""
        results = {}
        
        # OWASP Top 10 compliance
        results['owasp_top10'] = self._check_owasp_top10(issues)
        
        # CWE compliance
        results['cwe'] = self._check_cwe_compliance(issues)
        
        # Security best practices
        results['best_practices'] = self._check_best_practices(project_path, issues)
        
        # Data protection compliance (GDPR-like)
        results['data_protection'] = self._check_data_protection(project_path)
        
        return results
    
    def _check_owasp_top10(self, issues: List[SecurityIssue]) -> Dict[str, Any]:
        """Check against OWASP Top 10 vulnerabilities."""
        owasp_categories = {
            'A01_Broken_Access_Control': SecurityCategory.AUTHORIZATION,
            'A02_Cryptographic_Failures': SecurityCategory.WEAK_CRYPTO,
            'A03_Injection': SecurityCategory.INJECTION,
            'A04_Insecure_Design': SecurityCategory.MISCONFIGURATION,
            'A05_Security_Misconfiguration': SecurityCategory.MISCONFIGURATION,
            'A06_Vulnerable_Components': SecurityCategory.DEPENDENCY,
            'A07_Authentication_Failures': SecurityCategory.AUTHENTICATION,
            'A08_Software_Integrity_Failures': SecurityCategory.VULNERABILITY,
            'A09_Logging_Failures': SecurityCategory.MISCONFIGURATION,
            'A10_Server_Side_Request_Forgery': SecurityCategory.INJECTION
        }
        
        results = {}
        total_issues = len(issues)
        
        for owasp_cat, sec_cat in owasp_categories.items():
            category_issues = [i for i in issues if i.category == sec_cat]
            results[owasp_cat] = {
                'issues_count': len(category_issues),
                'compliance_score': max(0, 100 - (len(category_issues) * 10)),
                'critical_issues': len([i for i in category_issues if i.severity == SecuritySeverity.CRITICAL]),
                'high_issues': len([i for i in category_issues if i.severity == SecuritySeverity.HIGH])
            }
        
        # Overall OWASP compliance score
        avg_score = sum(cat['compliance_score'] for cat in results.values()) / len(results)
        results['overall_score'] = avg_score
        
        return results
    
    def _check_cwe_compliance(self, issues: List[SecurityIssue]) -> Dict[str, Any]:
        """Check CWE (Common Weakness Enumeration) compliance."""
        cwe_issues = [i for i in issues if i.cwe_id]
        cwe_counts = {}
        
        for issue in cwe_issues:
            cwe_id = issue.cwe_id
            if cwe_id not in cwe_counts:
                cwe_counts[cwe_id] = 0
            cwe_counts[cwe_id] += 1
        
        return {
            'total_cwe_issues': len(cwe_issues),
            'unique_cwes': len(cwe_counts),
            'cwe_distribution': cwe_counts,
            'top_cwes': sorted(cwe_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def _check_best_practices(self, project_path: Path, issues: List[SecurityIssue]) -> Dict[str, Any]:
        """Check adherence to security best practices."""
        practices = {
            'secrets_management': self._check_secrets_management(project_path),
            'dependency_management': self._check_dependency_management(project_path),
            'error_handling': self._check_error_handling(project_path),
            'logging_security': self._check_logging_security(project_path),
            'input_validation': self._check_input_validation(issues)
        }
        
        # Calculate overall best practices score
        scores = [p['score'] for p in practices.values() if 'score' in p]
        overall_score = sum(scores) / len(scores) if scores else 0
        
        return {
            'practices': practices,
            'overall_score': overall_score
        }
    
    def _check_secrets_management(self, project_path: Path) -> Dict[str, Any]:
        """Check secrets management practices."""
        score = 100
        issues = []
        
        # Check for .env files in .gitignore
        gitignore_path = project_path / '.gitignore'
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
            
            if '.env' not in gitignore_content:
                score -= 30
                issues.append("Environment files not in .gitignore")
        else:
            score -= 20
            issues.append("No .gitignore file found")
        
        # Check for secrets in code
        secret_patterns = ['password', 'secret', 'key', 'token']
        python_files = list(project_path.rglob('*.py'))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read().lower()
                
                for pattern in secret_patterns:
                    if f'{pattern} =' in content or f'{pattern}"' in content:
                        score -= 10
                        issues.append(f"Potential hardcoded {pattern} in {py_file.name}")
                        break
            except Exception:
                continue
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': [
                "Use environment variables for secrets",
                "Implement secure secret management system",
                "Add .env files to .gitignore"
            ]
        }
    
    def _check_dependency_management(self, project_path: Path) -> Dict[str, Any]:
        """Check dependency management practices."""
        score = 100
        issues = []
        
        # Check for requirements.txt or pyproject.toml
        has_requirements = (project_path / 'requirements.txt').exists()
        has_pyproject = (project_path / 'pyproject.toml').exists()
        
        if not has_requirements and not has_pyproject:
            score -= 50
            issues.append("No dependency management file found")
        
        # Check for version pinning
        if has_requirements:
            with open(project_path / 'requirements.txt', 'r') as f:
                content = f.read()
            
            lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
            unpinned = [line for line in lines if '==' not in line and '>=' not in line]
            
            if unpinned:
                score -= 20
                issues.append(f"{len(unpinned)} dependencies without version pinning")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': [
                "Pin dependency versions",
                "Regularly update dependencies",
                "Use dependency scanning tools"
            ]
        }
    
    def _check_error_handling(self, project_path: Path) -> Dict[str, Any]:
        """Check error handling practices."""
        score = 100
        issues = []
        
        python_files = list(project_path.rglob('*.py'))
        total_files = len(python_files)
        files_with_try_catch = 0
        
        for py_file in python_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                if 'try:' in content and 'except' in content:
                    files_with_try_catch += 1
                
                # Check for bare except clauses
                if 'except:' in content:
                    score -= 10
                    issues.append(f"Bare except clause in {py_file.name}")
                    
            except Exception:
                continue
        
        if total_files > 0:
            error_handling_ratio = files_with_try_catch / total_files
            if error_handling_ratio < 0.5:
                score -= 30
                issues.append("Low error handling coverage")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'error_handling_ratio': files_with_try_catch / total_files if total_files > 0 else 0,
            'recommendations': [
                "Implement comprehensive error handling",
                "Avoid bare except clauses",
                "Log errors appropriately"
            ]
        }
    
    def _check_logging_security(self, project_path: Path) -> Dict[str, Any]:
        """Check logging security practices."""
        score = 100
        issues = []
        
        python_files = list(project_path.rglob('*.py'))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Check for logging sensitive data
                sensitive_patterns = ['password', 'secret', 'token', 'key']
                for pattern in sensitive_patterns:
                    if f'log' in content.lower() and pattern in content.lower():
                        score -= 15
                        issues.append(f"Potential sensitive data logging in {py_file.name}")
                        break
                        
            except Exception:
                continue
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': [
                "Avoid logging sensitive information",
                "Implement log sanitization",
                "Use structured logging"
            ]
        }
    
    def _check_input_validation(self, issues: List[SecurityIssue]) -> Dict[str, Any]:
        """Check input validation based on found issues."""
        injection_issues = [i for i in issues if i.category == SecurityCategory.INJECTION]
        
        score = max(0, 100 - (len(injection_issues) * 20))
        
        return {
            'score': score,
            'injection_issues': len(injection_issues),
            'recommendations': [
                "Implement input validation and sanitization",
                "Use parameterized queries",
                "Validate all user inputs"
            ]
        }
    
    def _check_data_protection(self, project_path: Path) -> Dict[str, Any]:
        """Check data protection compliance."""
        score = 100
        issues = []
        
        # Check for privacy policy or data handling documentation
        docs = list(project_path.rglob('*privacy*')) + list(project_path.rglob('*data*'))
        if not docs:
            score -= 20
            issues.append("No data protection documentation found")
        
        # Check for encryption usage
        python_files = list(project_path.rglob('*.py'))
        has_encryption = False
        
        for py_file in python_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                if any(crypto in content for crypto in ['encrypt', 'decrypt', 'cryptography', 'hashlib']):
                    has_encryption = True
                    break
                    
            except Exception:
                continue
        
        if not has_encryption:
            score -= 30
            issues.append("No encryption implementation found")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': [
                "Implement data encryption",
                "Create data protection documentation",
                "Implement data retention policies"
            ]
        }


class SecurityAuditor:
    """Main security auditor orchestrator."""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.dependency_scanner = DependencyScanner()
        self.code_scanner = CodeSecurityScanner()
        self.compliance_checker = ComplianceChecker()
        
    def run_audit(self, scan_id: str = None) -> SecurityReport:
        """Run comprehensive security audit."""
        if scan_id is None:
            scan_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"🔒 Starting security audit: {scan_id}")
        start_time = time.time()
        
        # Scan dependencies
        print("📦 Scanning dependencies...")
        dependency_vulnerabilities = self.dependency_scanner.scan_python_dependencies(self.project_path)
        
        # Scan source code
        print("🔍 Scanning source code...")
        code_issues = self.code_scanner.scan_code(self.project_path)
        
        # Check compliance
        print("📋 Checking compliance...")
        compliance_results = self.compliance_checker.check_compliance(self.project_path, code_issues)
        
        end_time = time.time()
        scan_duration = end_time - start_time
        
        # Calculate metrics
        all_issues = code_issues
        metrics = self._calculate_metrics(all_issues, dependency_vulnerabilities, scan_duration)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_issues, dependency_vulnerabilities, compliance_results)
        
        # Assess risk
        risk_assessment = self._assess_risk(all_issues, dependency_vulnerabilities)
        
        # Create remediation plan
        remediation_plan = self._create_remediation_plan(all_issues, dependency_vulnerabilities)
        
        # Configuration issues (placeholder)
        configuration_issues = []
        
        report = SecurityReport(
            timestamp=datetime.now().isoformat(),
            project_path=str(self.project_path),
            scan_id=scan_id,
            metrics=metrics,
            issues=all_issues,
            dependency_vulnerabilities=dependency_vulnerabilities,
            configuration_issues=configuration_issues,
            compliance_results=compliance_results,
            recommendations=recommendations,
            risk_assessment=risk_assessment,
            remediation_plan=remediation_plan
        )
        
        print(f"✅ Security audit completed in {scan_duration:.2f}s")
        return report
    
    def _calculate_metrics(self, issues: List[SecurityIssue], 
                          dep_vulns: List[Dict[str, Any]], 
                          scan_duration: float) -> SecurityMetrics:
        """Calculate security metrics."""
        severity_counts = {
            SecuritySeverity.CRITICAL: 0,
            SecuritySeverity.HIGH: 0,
            SecuritySeverity.MEDIUM: 0,
            SecuritySeverity.LOW: 0,
            SecuritySeverity.INFO: 0
        }
        
        for issue in issues:
            severity_counts[issue.severity] += 1
        
        # Calculate security score (0-100)
        total_issues = len(issues)
        if total_issues == 0:
            security_score = 100.0
        else:
            # Weight by severity
            weighted_score = (
                severity_counts[SecuritySeverity.CRITICAL] * 25 +
                severity_counts[SecuritySeverity.HIGH] * 15 +
                severity_counts[SecuritySeverity.MEDIUM] * 10 +
                severity_counts[SecuritySeverity.LOW] * 5 +
                severity_counts[SecuritySeverity.INFO] * 1
            )
            security_score = max(0, 100 - weighted_score)
        
        # Count files and lines scanned
        python_files = list(self.project_path.rglob('*.py'))
        files_scanned = len(python_files)
        
        lines_scanned = 0
        for py_file in python_files:
            try:
                with open(py_file, 'r') as f:
                    lines_scanned += len(f.readlines())
            except Exception:
                continue
        
        return SecurityMetrics(
            total_issues=total_issues,
            critical_issues=severity_counts[SecuritySeverity.CRITICAL],
            high_issues=severity_counts[SecuritySeverity.HIGH],
            medium_issues=severity_counts[SecuritySeverity.MEDIUM],
            low_issues=severity_counts[SecuritySeverity.LOW],
            info_issues=severity_counts[SecuritySeverity.INFO],
            files_scanned=files_scanned,
            lines_scanned=lines_scanned,
            dependencies_scanned=len(dep_vulns),
            vulnerable_dependencies=len([v for v in dep_vulns if v.get('severity') in ['critical', 'high']]),
            security_score=security_score,
            compliance_score=75.0,  # Placeholder
            scan_duration=scan_duration
        )
    
    def _generate_recommendations(self, issues: List[SecurityIssue], 
                                dep_vulns: List[Dict[str, Any]], 
                                compliance: Dict[str, Any]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        
        # Critical issues
        critical_issues = [i for i in issues if i.severity == SecuritySeverity.CRITICAL]
        if critical_issues:
            recommendations.append(
                f"🚨 Address {len(critical_issues)} critical security issues immediately"
            )
        
        # Dependency vulnerabilities
        critical_deps = [v for v in dep_vulns if v.get('severity') == 'critical']
        if critical_deps:
            recommendations.append(
                f"📦 Update {len(critical_deps)} dependencies with critical vulnerabilities"
            )
        
        # Common issue patterns
        injection_issues = [i for i in issues if i.category == SecurityCategory.INJECTION]
        if injection_issues:
            recommendations.append(
                "🛡️ Implement input validation and parameterized queries to prevent injection attacks"
            )
        
        auth_issues = [i for i in issues if i.category == SecurityCategory.AUTHENTICATION]
        if auth_issues:
            recommendations.append(
                "🔐 Strengthen authentication mechanisms and credential management"
            )
        
        crypto_issues = [i for i in issues if i.category == SecurityCategory.WEAK_CRYPTO]
        if crypto_issues:
            recommendations.append(
                "🔒 Upgrade to strong cryptographic algorithms and secure random number generation"
            )
        
        # Compliance recommendations
        owasp_score = compliance.get('owasp_top10', {}).get('overall_score', 100)
        if owasp_score < 80:
            recommendations.append(
                "📋 Improve OWASP Top 10 compliance by addressing identified vulnerabilities"
            )
        
        # General recommendations
        if not recommendations:
            recommendations.append(
                "✅ Security posture looks good! Continue monitoring and regular security audits"
            )
        
        recommendations.extend([
            "🔄 Implement automated security scanning in CI/CD pipeline",
            "📚 Provide security training for development team",
            "🎯 Establish security incident response procedures"
        ])
        
        return recommendations
    
    def _assess_risk(self, issues: List[SecurityIssue], 
                    dep_vulns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess overall security risk."""
        critical_count = len([i for i in issues if i.severity == SecuritySeverity.CRITICAL])
        high_count = len([i for i in issues if i.severity == SecuritySeverity.HIGH])
        
        critical_deps = len([v for v in dep_vulns if v.get('severity') == 'critical'])
        high_deps = len([v for v in dep_vulns if v.get('severity') == 'high'])
        
        # Calculate risk level
        if critical_count > 0 or critical_deps > 0:
            risk_level = "CRITICAL"
            risk_score = 90 + min(10, (critical_count + critical_deps))
        elif high_count > 2 or high_deps > 2:
            risk_level = "HIGH"
            risk_score = 70 + min(20, (high_count + high_deps) * 2)
        elif high_count > 0 or high_deps > 0:
            risk_level = "MEDIUM"
            risk_score = 40 + min(30, (high_count + high_deps) * 5)
        else:
            risk_level = "LOW"
            risk_score = max(0, 30 - len(issues))
        
        return {
            'risk_level': risk_level,
            'risk_score': min(100, risk_score),
            'critical_issues': critical_count,
            'high_issues': high_count,
            'critical_dependencies': critical_deps,
            'high_dependencies': high_deps,
            'risk_factors': [
                f"{critical_count} critical code issues",
                f"{high_count} high severity code issues",
                f"{critical_deps} critical dependency vulnerabilities",
                f"{high_deps} high severity dependency vulnerabilities"
            ]
        }
    
    def _create_remediation_plan(self, issues: List[SecurityIssue], 
                               dep_vulns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create prioritized remediation plan."""
        plan = []
        
        # Group issues by priority
        critical_issues = [i for i in issues if i.severity == SecuritySeverity.CRITICAL]
        high_issues = [i for i in issues if i.severity == SecuritySeverity.HIGH]
        
        critical_deps = [v for v in dep_vulns if v.get('severity') == 'critical']
        high_deps = [v for v in dep_vulns if v.get('severity') == 'high']
        
        # Phase 1: Critical issues (immediate)
        if critical_issues or critical_deps:
            phase1_tasks = []
            
            for issue in critical_issues[:5]:  # Top 5 critical
                phase1_tasks.append({
                    'type': 'code_fix',
                    'title': issue.title,
                    'file': issue.file_path,
                    'line': issue.line_number,
                    'remediation': issue.remediation,
                    'effort': 'high'
                })
            
            for dep in critical_deps[:3]:  # Top 3 critical deps
                phase1_tasks.append({
                    'type': 'dependency_update',
                    'title': f"Update {dep['dependency']}",
                    'current_version': dep['version'],
                    'remediation': dep['remediation'],
                    'effort': 'medium'
                })
            
            plan.append({
                'phase': 1,
                'priority': 'CRITICAL',
                'timeline': 'Immediate (1-3 days)',
                'tasks': phase1_tasks,
                'estimated_effort': f"{len(phase1_tasks) * 2} hours"
            })
        
        # Phase 2: High priority issues (short term)
        if high_issues or high_deps:
            phase2_tasks = []
            
            for issue in high_issues[:10]:  # Top 10 high
                phase2_tasks.append({
                    'type': 'code_fix',
                    'title': issue.title,
                    'file': issue.file_path,
                    'line': issue.line_number,
                    'remediation': issue.remediation,
                    'effort': 'medium'
                })
            
            for dep in high_deps[:5]:  # Top 5 high deps
                phase2_tasks.append({
                    'type': 'dependency_update',
                    'title': f"Update {dep['dependency']}",
                    'current_version': dep['version'],
                    'remediation': dep['remediation'],
                    'effort': 'low'
                })
            
            plan.append({
                'phase': 2,
                'priority': 'HIGH',
                'timeline': 'Short term (1-2 weeks)',
                'tasks': phase2_tasks,
                'estimated_effort': f"{len(phase2_tasks) * 1} hours"
            })
        
        # Phase 3: Medium priority and improvements (medium term)
        medium_issues = [i for i in issues if i.severity == SecuritySeverity.MEDIUM]
        if medium_issues:
            phase3_tasks = []
            
            for issue in medium_issues[:15]:  # Top 15 medium
                phase3_tasks.append({
                    'type': 'code_improvement',
                    'title': issue.title,
                    'file': issue.file_path,
                    'remediation': issue.remediation,
                    'effort': 'low'
                })
            
            plan.append({
                'phase': 3,
                'priority': 'MEDIUM',
                'timeline': 'Medium term (1 month)',
                'tasks': phase3_tasks,
                'estimated_effort': f"{len(phase3_tasks) * 0.5} hours"
            })
        
        return plan
    
    def generate_report(self, report: SecurityReport, output_format: str = 'json') -> str:
        """Generate security audit report in specified format."""
        if output_format == 'json':
            return self._generate_json_report(report)
        elif output_format == 'html':
            return self._generate_html_report(report)
        elif output_format == 'markdown':
            return self._generate_markdown_report(report)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _generate_json_report(self, report: SecurityReport) -> str:
        """Generate JSON format report."""
        # Convert dataclasses to dict for JSON serialization
        report_dict = {
            'timestamp': report.timestamp,
            'project_path': report.project_path,
            'scan_id': report.scan_id,
            'metrics': asdict(report.metrics),
            'issues': [asdict(issue) for issue in report.issues],
            'dependency_vulnerabilities': report.dependency_vulnerabilities,
            'configuration_issues': report.configuration_issues,
            'compliance_results': report.compliance_results,
            'recommendations': report.recommendations,
            'risk_assessment': report.risk_assessment,
            'remediation_plan': report.remediation_plan
        }
        
        return json.dumps(report_dict, indent=2, default=str)
    
    def _generate_html_report(self, report: SecurityReport) -> str:
        """Generate HTML format report."""
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Security Audit Report - {report.scan_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .metrics {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 5px; flex: 1; }}
        .critical {{ color: #dc3545; }}
        .high {{ color: #fd7e14; }}
        .medium {{ color: #ffc107; }}
        .low {{ color: #28a745; }}
        .issue {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ddd; }}
        .issue.critical {{ border-left-color: #dc3545; }}
        .issue.high {{ border-left-color: #fd7e14; }}
        .issue.medium {{ border-left-color: #ffc107; }}
        .issue.low {{ border-left-color: #28a745; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔒 Security Audit Report</h1>
        <p><strong>Scan ID:</strong> {report.scan_id}</p>
        <p><strong>Timestamp:</strong> {report.timestamp}</p>
        <p><strong>Project:</strong> {report.project_path}</p>
    </div>
    
    <div class="metrics">
        <div class="metric-card">
            <h3>Security Score</h3>
            <h2>{report.metrics.security_score:.1f}/100</h2>
        </div>
        <div class="metric-card">
            <h3>Total Issues</h3>
            <h2>{report.metrics.total_issues}</h2>
        </div>
        <div class="metric-card">
            <h3>Critical Issues</h3>
            <h2 class="critical">{report.metrics.critical_issues}</h2>
        </div>
        <div class="metric-card">
            <h3>High Issues</h3>
            <h2 class="high">{report.metrics.high_issues}</h2>
        </div>
    </div>
    
    <h2>🚨 Critical Issues</h2>
    {self._format_issues_html([i for i in report.issues if i.severity == SecuritySeverity.CRITICAL])}
    
    <h2>⚠️ High Priority Issues</h2>
    {self._format_issues_html([i for i in report.issues if i.severity == SecuritySeverity.HIGH])}
    
    <h2>📋 Recommendations</h2>
    <ul>
        {''.join(f'<li>{rec}</li>' for rec in report.recommendations)}
    </ul>
    
</body>
</html>
        """
        
        return html_template
    
    def _format_issues_html(self, issues: List[SecurityIssue]) -> str:
        """Format issues for HTML report."""
        if not issues:
            return "<p>No issues found.</p>"
        
        html = ""
        for issue in issues:
            severity_class = issue.severity.value
            html += f"""
            <div class="issue {severity_class}">
                <h4>{issue.title}</h4>
                <p><strong>File:</strong> {issue.file_path or 'N/A'}</p>
                <p><strong>Line:</strong> {issue.line_number or 'N/A'}</p>
                <p><strong>Description:</strong> {issue.description}</p>
                <p><strong>Remediation:</strong> {issue.remediation}</p>
            </div>
            """
        
        return html
    
    def _generate_markdown_report(self, report: SecurityReport) -> str:
        """Generate Markdown format report."""
        md = f"""
# 🔒 Security Audit Report

**Scan ID:** {report.scan_id}  
**Timestamp:** {report.timestamp}  
**Project:** {report.project_path}  

## 📊 Security Metrics

| Metric | Value |
|--------|-------|
| Security Score | {report.metrics.security_score:.1f}/100 |
| Total Issues | {report.metrics.total_issues} |
| Critical Issues | {report.metrics.critical_issues} |
| High Issues | {report.metrics.high_issues} |
| Medium Issues | {report.metrics.medium_issues} |
| Low Issues | {report.metrics.low_issues} |
| Files Scanned | {report.metrics.files_scanned} |
| Lines Scanned | {report.metrics.lines_scanned} |
| Scan Duration | {report.metrics.scan_duration:.2f}s |

## 🚨 Critical Issues

{self._format_issues_markdown([i for i in report.issues if i.severity == SecuritySeverity.CRITICAL])}

## ⚠️ High Priority Issues

{self._format_issues_markdown([i for i in report.issues if i.severity == SecuritySeverity.HIGH])}

## 📦 Dependency Vulnerabilities

{self._format_dependencies_markdown(report.dependency_vulnerabilities)}

## 📋 Recommendations

{chr(10).join(f'- {rec}' for rec in report.recommendations)}

## 🎯 Risk Assessment

**Risk Level:** {report.risk_assessment['risk_level']}  
**Risk Score:** {report.risk_assessment['risk_score']}/100  

### Risk Factors:
{chr(10).join(f'- {factor}' for factor in report.risk_assessment['risk_factors'])}

## 🔧 Remediation Plan

{self._format_remediation_markdown(report.remediation_plan)}
        """
        
        return md
    
    def _format_issues_markdown(self, issues: List[SecurityIssue]) -> str:
        """Format issues for Markdown report."""
        if not issues:
            return "No issues found."
        
        md = ""
        for issue in issues:
            md += f"""
### {issue.title}

- **File:** {issue.file_path or 'N/A'}
- **Line:** {issue.line_number or 'N/A'}
- **Severity:** {issue.severity.value.upper()}
- **Category:** {issue.category.value}
- **Description:** {issue.description}
- **Remediation:** {issue.remediation}
- **Tool:** {issue.tool}

"""
            if issue.code_snippet:
                md += f"```\n{issue.code_snippet}\n```\n\n"
        
        return md
    
    def _format_dependencies_markdown(self, dependencies: List[Dict[str, Any]]) -> str:
        """Format dependency vulnerabilities for Markdown."""
        if not dependencies:
            return "No dependency vulnerabilities found."
        
        md = "| Dependency | Version | Vulnerability | Severity | Remediation |\n"
        md += "|------------|---------|---------------|----------|-------------|\n"
        
        for dep in dependencies:
            md += f"| {dep.get('dependency', 'N/A')} | {dep.get('version', 'N/A')} | {dep.get('vulnerability_id', 'N/A')} | {dep.get('severity', 'N/A')} | {dep.get('remediation', 'N/A')} |\n"
        
        return md
    
    def _format_remediation_markdown(self, plan: List[Dict[str, Any]]) -> str:
        """Format remediation plan for Markdown."""
        if not plan:
            return "No remediation plan available."
        
        md = ""
        for phase in plan:
            md += f"""
### Phase {phase['phase']}: {phase['priority']} Priority

**Timeline:** {phase['timeline']}  
**Estimated Effort:** {phase['estimated_effort']}  

**Tasks:**
{chr(10).join(f"- {task['title']} ({task['type']})" for task in phase['tasks'])}

"""
        
        return md


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Security Audit Tool for AI Video Renderer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python security_audit.py                    # Audit current directory
  python security_audit.py /path/to/project  # Audit specific project
  python security_audit.py --format html     # Generate HTML report
  python security_audit.py --output report.json  # Save to file
        """
    )
    
    parser.add_argument(
        'project_path',
        nargs='?',
        default='.',
        help='Path to the project to audit (default: current directory)'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'html', 'markdown'],
        default='json',
        help='Output format (default: json)'
    )
    
    parser.add_argument(
        '--output',
        help='Output file path (default: stdout)'
    )
    
    parser.add_argument(
        '--scan-id',
        help='Custom scan ID (default: auto-generated)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize auditor
        auditor = SecurityAuditor(args.project_path)
        
        # Run audit
        report = auditor.run_audit(args.scan_id)
        
        # Generate report
        report_content = auditor.generate_report(report, args.format)
        
        # Output report
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report_content)
            print(f"✅ Security audit report saved to: {args.output}")
        else:
            print(report_content)
        
        # Print summary
        if args.verbose:
            print(f"\n📊 Audit Summary:")
            print(f"Security Score: {report.metrics.security_score:.1f}/100")
            print(f"Total Issues: {report.metrics.total_issues}")
            print(f"Critical: {report.metrics.critical_issues}")
            print(f"High: {report.metrics.high_issues}")
            print(f"Medium: {report.metrics.medium_issues}")
            print(f"Low: {report.metrics.low_issues}")
            print(f"Risk Level: {report.risk_assessment['risk_level']}")
        
        # Exit with appropriate code
        if report.metrics.critical_issues > 0:
            sys.exit(2)  # Critical issues found
        elif report.metrics.high_issues > 0:
            sys.exit(1)  # High issues found
        else:
            sys.exit(0)  # No critical/high issues
            
    except Exception as e:
        print(f"❌ Error running security audit: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(3)


if __name__ == '__main__':
    main()