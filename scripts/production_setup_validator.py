#!/usr/bin/env python3
"""
🔧 Production Environment Setup & Validation Tool
================================================================
Automated setup and validation for AI Video Renderer production environment
Ensures all dependencies, configurations, and services are properly configured
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import shutil
import requests
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_setup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SetupResult:
    """Result of a setup step"""
    step: str
    success: bool
    message: str
    details: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of a validation check"""
    check: str
    passed: bool
    message: str
    severity: str = "info"  # info, warning, error, critical

class ProductionSetupValidator:
    """Comprehensive production environment setup and validation"""
    
    def __init__(self, project_root: str, env_file: str = ".env.n8n"):
        self.project_root = Path(project_root)
        self.env_file = self.project_root / env_file
        self.setup_results: List[SetupResult] = []
        self.validation_results: List[ValidationResult] = []
        self.env_vars: Dict[str, str] = {}
        
        # Load environment variables
        self._load_environment()
    
    def _load_environment(self) -> None:
        """Load environment variables from .env file"""
        try:
            if self.env_file.exists():
                with open(self.env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            self.env_vars[key.strip()] = value.strip()
                logger.info(f"Loaded {len(self.env_vars)} environment variables")
            else:
                logger.warning(f"Environment file not found: {self.env_file}")
        except Exception as e:
            logger.error(f"Failed to load environment: {e}")
    
    def _run_command(self, command: List[str], capture_output: bool = True) -> Tuple[bool, str]:
        """Run a shell command and return success status and output"""
        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def _check_python_version(self) -> SetupResult:
        """Check Python version compatibility"""
        try:
            version = sys.version_info
            if version.major == 3 and version.minor >= 8:
                return SetupResult(
                    "python_version",
                    True,
                    f"Python {version.major}.{version.minor}.{version.micro} is compatible"
                )
            else:
                return SetupResult(
                    "python_version",
                    False,
                    f"Python {version.major}.{version.minor} is not supported. Requires Python 3.8+"
                )
        except Exception as e:
            return SetupResult("python_version", False, f"Failed to check Python version: {e}")
    
    def _install_system_dependencies(self) -> SetupResult:
        """Install required system dependencies"""
        dependencies = [
            "ffmpeg",  # Video processing
            "imagemagick",  # Image processing
            "curl",  # HTTP requests
            "git"  # Version control
        ]
        
        missing_deps = []
        for dep in dependencies:
            success, _ = self._run_command(["which", dep])
            if not success:
                missing_deps.append(dep)
        
        if missing_deps:
            return SetupResult(
                "system_dependencies",
                False,
                f"Missing system dependencies: {', '.join(missing_deps)}",
                "Install with: brew install " + " ".join(missing_deps)
            )
        
        return SetupResult(
            "system_dependencies",
            True,
            "All system dependencies are installed"
        )
    
    def _install_python_dependencies(self) -> SetupResult:
        """Install Python dependencies"""
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            # Create basic requirements.txt
            basic_requirements = [
                "requests>=2.28.0",
                "pydantic>=1.10.0",
                "python-dotenv>=0.19.0",
                "aiohttp>=3.8.0",
                "aiofiles>=0.8.0",
                "pytest>=7.0.0",
                "pytest-cov>=4.0.0",
                "black>=22.0.0",
                "isort>=5.10.0",
                "pylint>=2.15.0",
                "mypy>=0.991",
                "bandit>=1.7.0",
                "safety>=2.0.0"
            ]
            
            with open(requirements_file, 'w') as f:
                f.write('\n'.join(basic_requirements))
            
            logger.info("Created basic requirements.txt")
        
        # Install dependencies
        success, output = self._run_command([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        
        if success:
            return SetupResult(
                "python_dependencies",
                True,
                "Python dependencies installed successfully"
            )
        else:
            return SetupResult(
                "python_dependencies",
                False,
                "Failed to install Python dependencies",
                output
            )
    
    def _setup_directory_structure(self) -> SetupResult:
        """Create required directory structure"""
        directories = [
            "scripts/quality",
            "quality_reports",
            "logs",
            "output",
            "thumbnails",
            "temp",
            "backups",
            "tests",
            "docs"
        ]
        
        created_dirs = []
        for directory in directories:
            dir_path = self.project_root / directory
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(directory)
                except Exception as e:
                    return SetupResult(
                        "directory_structure",
                        False,
                        f"Failed to create directory {directory}: {e}"
                    )
        
        if created_dirs:
            return SetupResult(
                "directory_structure",
                True,
                f"Created directories: {', '.join(created_dirs)}"
            )
        else:
            return SetupResult(
                "directory_structure",
                True,
                "All required directories already exist"
            )
    
    def _validate_api_credentials(self) -> ValidationResult:
        """Validate API credentials and connectivity"""
        critical_apis = {
            "YOUTUBE_CLIENT_ID": "YouTube API",
            "GOOGLE_API_KEY": "Google API",
            "ELEVENLABS_KEY": "ElevenLabs TTS",
            "NEWSAPI_KEY": "News API"
        }
        
        missing_keys = []
        invalid_keys = []
        
        for key, service in critical_apis.items():
            if key not in self.env_vars or not self.env_vars[key]:
                missing_keys.append(service)
            else:
                # Basic format validation
                value = self.env_vars[key]
                if key == "YOUTUBE_CLIENT_ID" and not value.endswith(".apps.googleusercontent.com"):
                    invalid_keys.append(f"{service} (invalid format)")
                elif key == "GOOGLE_API_KEY" and not value.startswith("AIza"):
                    invalid_keys.append(f"{service} (invalid format)")
                elif key == "ELEVENLABS_KEY" and not value.startswith("sk_"):
                    invalid_keys.append(f"{service} (invalid format)")
        
        if missing_keys or invalid_keys:
            severity = "critical" if missing_keys else "warning"
            message = ""
            if missing_keys:
                message += f"Missing API keys: {', '.join(missing_keys)}. "
            if invalid_keys:
                message += f"Invalid API keys: {', '.join(invalid_keys)}."
            
            return ValidationResult(
                "api_credentials",
                False,
                message.strip(),
                severity
            )
        
        return ValidationResult(
            "api_credentials",
            True,
            "All critical API credentials are present and properly formatted"
        )
    
    def _validate_security_settings(self) -> ValidationResult:
        """Validate security configuration"""
        security_issues = []
        
        # Check debug settings
        if self.env_vars.get("N8N_LOG_LEVEL", "").lower() == "debug":
            security_issues.append("Debug logging enabled in production")
        
        # Check encryption keys
        encryption_key = self.env_vars.get("N8N_ENCRYPTION_KEY", "")
        if not encryption_key or len(encryption_key) < 32:
            security_issues.append("Weak or missing N8N encryption key")
        
        jwt_secret = self.env_vars.get("N8N_USER_MANAGEMENT_JWT_SECRET", "")
        if not jwt_secret or len(jwt_secret) < 32:
            security_issues.append("Weak or missing JWT secret")
        
        # Check host binding
        host = self.env_vars.get("N8N_HOST", "")
        if host == "0.0.0.0":
            security_issues.append("N8N bound to all interfaces (security risk)")
        
        # Check authentication
        if self.env_vars.get("N8N_BASIC_AUTH_ACTIVE", "").lower() != "true":
            security_issues.append("Basic authentication disabled")
        
        if security_issues:
            return ValidationResult(
                "security_settings",
                False,
                f"Security issues found: {'; '.join(security_issues)}",
                "warning"
            )
        
        return ValidationResult(
            "security_settings",
            True,
            "Security settings are properly configured"
        )
    
    def _validate_performance_settings(self) -> ValidationResult:
        """Validate performance configuration"""
        performance_issues = []
        
        # Check memory limits
        max_memory = self.env_vars.get("MAX_MEMORY_MB", "")
        if not max_memory or int(max_memory) < 1024:
            performance_issues.append("Low memory limit (< 1GB)")
        
        # Check concurrent renders
        max_concurrent = self.env_vars.get("MAX_CONCURRENT_RENDERS", "")
        if not max_concurrent or int(max_concurrent) > 5:
            performance_issues.append("High concurrent render limit (may cause resource issues)")
        
        # Check rate limiting
        rate_limit = self.env_vars.get("RATE_LIMIT_RPM", "")
        if not rate_limit or int(rate_limit) > 100:
            performance_issues.append("High rate limit (may trigger API throttling)")
        
        if performance_issues:
            return ValidationResult(
                "performance_settings",
                False,
                f"Performance issues: {'; '.join(performance_issues)}",
                "warning"
            )
        
        return ValidationResult(
            "performance_settings",
            True,
            "Performance settings are optimized"
        )
    
    def _test_api_connectivity(self) -> ValidationResult:
        """Test connectivity to critical APIs"""
        api_tests = []
        
        # Test Google API
        google_key = self.env_vars.get("GOOGLE_API_KEY")
        if google_key:
            try:
                response = requests.get(
                    f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=test&key={google_key}",
                    timeout=10
                )
                if response.status_code == 200:
                    api_tests.append("✅ Google/YouTube API")
                else:
                    api_tests.append(f"❌ Google/YouTube API ({response.status_code})")
            except Exception as e:
                api_tests.append(f"❌ Google/YouTube API (connection failed)")
        
        # Test News API
        news_key = self.env_vars.get("NEWSAPI_KEY")
        if news_key:
            try:
                response = requests.get(
                    f"https://newsapi.org/v2/top-headlines?country=us&apiKey={news_key}",
                    timeout=10
                )
                if response.status_code == 200:
                    api_tests.append("✅ News API")
                else:
                    api_tests.append(f"❌ News API ({response.status_code})")
            except Exception:
                api_tests.append("❌ News API (connection failed)")
        
        failed_tests = [test for test in api_tests if "❌" in test]
        
        if failed_tests:
            return ValidationResult(
                "api_connectivity",
                False,
                f"API connectivity issues: {'; '.join(failed_tests)}",
                "warning"
            )
        
        return ValidationResult(
            "api_connectivity",
            True,
            f"API connectivity verified: {'; '.join(api_tests)}"
        )
    
    def _create_systemd_service(self) -> SetupResult:
        """Create systemd service file for production deployment"""
        service_content = f"""[Unit]
Description=AI Video Renderer - N8N Automation
After=network.target

[Service]
Type=simple
User=n8n
WorkingDirectory={self.project_root}
Environment=NODE_ENV=production
EnvironmentFile={self.env_file}
ExecStart=/usr/local/bin/n8n start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        
        service_file = self.project_root / "ai-video-renderer.service"
        try:
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            return SetupResult(
                "systemd_service",
                True,
                f"Systemd service file created: {service_file}",
                f"Install with: sudo cp {service_file} /etc/systemd/system/ && sudo systemctl enable ai-video-renderer"
            )
        except Exception as e:
            return SetupResult(
                "systemd_service",
                False,
                f"Failed to create systemd service: {e}"
            )
    
    def _setup_monitoring(self) -> SetupResult:
        """Setup basic monitoring and health checks"""
        monitoring_script = self.project_root / "scripts" / "health_check.py"
        
        health_check_content = '''#!/usr/bin/env python3
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
'''
        
        try:
            monitoring_script.parent.mkdir(parents=True, exist_ok=True)
            with open(monitoring_script, 'w') as f:
                f.write(health_check_content)
            
            # Make executable
            os.chmod(monitoring_script, 0o755)
            
            return SetupResult(
                "monitoring_setup",
                True,
                f"Health check script created: {monitoring_script}"
            )
        except Exception as e:
            return SetupResult(
                "monitoring_setup",
                False,
                f"Failed to create monitoring script: {e}"
            )
    
    def run_setup(self) -> None:
        """Run complete production setup"""
        logger.info("Starting production environment setup...")
        
        setup_steps = [
            self._check_python_version,
            self._install_system_dependencies,
            self._install_python_dependencies,
            self._setup_directory_structure,
            self._create_systemd_service,
            self._setup_monitoring
        ]
        
        for step in setup_steps:
            try:
                result = step()
                self.setup_results.append(result)
                
                if result.success:
                    logger.info(f"✅ {result.step}: {result.message}")
                else:
                    logger.error(f"❌ {result.step}: {result.message}")
                    if result.details:
                        logger.info(f"   Details: {result.details}")
            except Exception as e:
                error_result = SetupResult(
                    step.__name__,
                    False,
                    f"Setup step failed: {e}"
                )
                self.setup_results.append(error_result)
                logger.error(f"❌ {step.__name__}: {e}")
    
    def run_validation(self) -> None:
        """Run complete production validation"""
        logger.info("Starting production environment validation...")
        
        validation_checks = [
            self._validate_api_credentials,
            self._validate_security_settings,
            self._validate_performance_settings,
            self._test_api_connectivity
        ]
        
        for check in validation_checks:
            try:
                result = check()
                self.validation_results.append(result)
                
                if result.passed:
                    logger.info(f"✅ {result.check}: {result.message}")
                else:
                    level = logger.error if result.severity in ["error", "critical"] else logger.warning
                    level(f"❌ {result.check}: {result.message}")
            except Exception as e:
                error_result = ValidationResult(
                    check.__name__,
                    False,
                    f"Validation check failed: {e}",
                    "error"
                )
                self.validation_results.append(error_result)
                logger.error(f"❌ {check.__name__}: {e}")
    
    def generate_report(self) -> str:
        """Generate comprehensive setup and validation report"""
        report = []
        report.append("# 🚀 Production Environment Setup & Validation Report")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Project:** {self.project_root}")
        report.append("")
        
        # Setup Results
        report.append("## 🔧 Setup Results")
        report.append("")
        setup_success = sum(1 for r in self.setup_results if r.success)
        setup_total = len(self.setup_results)
        report.append(f"**Success Rate:** {setup_success}/{setup_total} ({setup_success/setup_total*100:.1f}%)")
        report.append("")
        
        for result in self.setup_results:
            status = "✅" if result.success else "❌"
            report.append(f"- {status} **{result.step}:** {result.message}")
            if result.details:
                report.append(f"  - *Details:* {result.details}")
        
        report.append("")
        
        # Validation Results
        report.append("## ✅ Validation Results")
        report.append("")
        validation_passed = sum(1 for r in self.validation_results if r.passed)
        validation_total = len(self.validation_results)
        report.append(f"**Pass Rate:** {validation_passed}/{validation_total} ({validation_passed/validation_total*100:.1f}%)")
        report.append("")
        
        # Group by severity
        critical_issues = [r for r in self.validation_results if not r.passed and r.severity == "critical"]
        warnings = [r for r in self.validation_results if not r.passed and r.severity == "warning"]
        passed_checks = [r for r in self.validation_results if r.passed]
        
        if critical_issues:
            report.append("### 🚨 Critical Issues")
            for result in critical_issues:
                report.append(f"- ❌ **{result.check}:** {result.message}")
            report.append("")
        
        if warnings:
            report.append("### ⚠️ Warnings")
            for result in warnings:
                report.append(f"- ⚠️ **{result.check}:** {result.message}")
            report.append("")
        
        if passed_checks:
            report.append("### ✅ Passed Checks")
            for result in passed_checks:
                report.append(f"- ✅ **{result.check}:** {result.message}")
            report.append("")
        
        # Recommendations
        report.append("## 📋 Next Steps")
        report.append("")
        
        if critical_issues:
            report.append("### Immediate Action Required")
            report.append("1. Address all critical issues before production deployment")
            report.append("2. Re-run validation after fixes")
            report.append("")
        
        if warnings:
            report.append("### Recommended Improvements")
            report.append("1. Review and address warning items")
            report.append("2. Consider implementing additional security measures")
            report.append("")
        
        report.append("### Production Deployment")
        if not critical_issues:
            report.append("1. Install systemd service: `sudo cp ai-video-renderer.service /etc/systemd/system/`")
            report.append("2. Enable service: `sudo systemctl enable ai-video-renderer`")
            report.append("3. Start service: `sudo systemctl start ai-video-renderer`")
            report.append("4. Monitor logs: `sudo journalctl -u ai-video-renderer -f`")
            report.append("5. Setup monitoring: `crontab -e` and add health check")
        else:
            report.append("❌ **Not ready for production deployment** - resolve critical issues first")
        
        return "\n".join(report)

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Production Environment Setup & Validation")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--env-file", default=".env.n8n", help="Environment file path")
    parser.add_argument("--setup-only", action="store_true", help="Run setup only")
    parser.add_argument("--validate-only", action="store_true", help="Run validation only")
    parser.add_argument("--output", help="Output report file")
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = ProductionSetupValidator(args.project_root, args.env_file)
    
    # Run setup and/or validation
    if not args.validate_only:
        validator.run_setup()
    
    if not args.setup_only:
        validator.run_validation()
    
    # Generate and save report
    report = validator.generate_report()
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to: {args.output}")
    else:
        print("\n" + report)
    
    # Exit with error code if critical issues found
    critical_issues = [r for r in validator.validation_results if not r.passed and r.severity == "critical"]
    setup_failures = [r for r in validator.setup_results if not r.success]
    
    if critical_issues or setup_failures:
        sys.exit(1)
    else:
        logger.info("🎉 Production environment is ready!")
        sys.exit(0)

if __name__ == "__main__":
    main()