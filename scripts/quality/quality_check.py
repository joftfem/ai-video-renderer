#!/usr/bin/env python3
"""
Comprehensive Code Quality Check Tool

Automated code quality assessment including:
- Code formatting and style
- Type checking and linting
- Security vulnerability scanning
- Performance profiling
- Test coverage analysis
- Documentation completeness
"""

import os
import sys
import subprocess
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import tempfile
from dataclasses import dataclass, asdict
from enum import Enum


class CheckStatus(Enum):
    """Status of quality checks."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class Severity(Enum):
    """Severity levels for issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QualityIssue:
    """Represents a quality issue found during checks."""
    check_name: str
    severity: Severity
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    rule_id: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class CheckResult:
    """Result of a quality check."""
    name: str
    status: CheckStatus
    duration: float
    issues: List[QualityIssue]
    metrics: Dict[str, Any]
    output: str = ""
    error: str = ""


@dataclass
class QualityReport:
    """Complete quality assessment report."""
    timestamp: str
    project_path: str
    total_duration: float
    overall_status: CheckStatus
    checks: List[CheckResult]
    summary: Dict[str, Any]
    recommendations: List[str]


class QualityChecker:
    """Main quality checking orchestrator."""
    
    def __init__(self, project_path: str, config: Optional[Dict] = None):
        self.project_path = Path(project_path)
        self.config = config or self._load_default_config()
        self.results: List[CheckResult] = []
        
        # Ensure project path exists
        if not self.project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration for quality checks."""
        return {
            'checks': {
                'formatting': {'enabled': True, 'tools': ['black', 'isort']},
                'linting': {'enabled': True, 'tools': ['pylint', 'ruff']},
                'typing': {'enabled': True, 'tools': ['mypy']},
                'security': {'enabled': True, 'tools': ['bandit', 'safety']},
                'testing': {'enabled': True, 'min_coverage': 80},
                'documentation': {'enabled': True, 'check_docstrings': True},
                'performance': {'enabled': True, 'profile_imports': True},
                'complexity': {'enabled': True, 'max_complexity': 10}
            },
            'paths': {
                'source': ['scripts'],
                'tests': ['tests'],
                'exclude': ['__pycache__', '.git', '.venv', 'node_modules']
            },
            'thresholds': {
                'max_line_length': 88,
                'max_function_length': 50,
                'max_class_length': 200,
                'min_test_coverage': 80
            }
        }
    
    def run_all_checks(self, fix_issues: bool = False) -> QualityReport:
        """Run all enabled quality checks."""
        start_time = time.time()
        
        print("🔍 Starting comprehensive quality assessment...")
        print(f"📁 Project: {self.project_path}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Run individual checks
        if self.config['checks']['formatting']['enabled']:
            self._run_formatting_checks(fix_issues)
        
        if self.config['checks']['linting']['enabled']:
            self._run_linting_checks()
        
        if self.config['checks']['typing']['enabled']:
            self._run_type_checks()
        
        if self.config['checks']['security']['enabled']:
            self._run_security_checks()
        
        if self.config['checks']['testing']['enabled']:
            self._run_test_checks()
        
        if self.config['checks']['documentation']['enabled']:
            self._run_documentation_checks()
        
        if self.config['checks']['performance']['enabled']:
            self._run_performance_checks()
        
        if self.config['checks']['complexity']['enabled']:
            self._run_complexity_checks()
        
        # Generate report
        total_duration = time.time() - start_time
        report = self._generate_report(total_duration)
        
        # Print summary
        self._print_summary(report)
        
        return report
    
    def _run_formatting_checks(self, fix_issues: bool = False) -> None:
        """Run code formatting checks."""
        print("\n📝 Running formatting checks...")
        
        # Black formatting check
        black_result = self._run_black_check(fix_issues)
        self.results.append(black_result)
        
        # isort import sorting check
        isort_result = self._run_isort_check(fix_issues)
        self.results.append(isort_result)
    
    def _run_black_check(self, fix_issues: bool = False) -> CheckResult:
        """Run Black code formatting check."""
        start_time = time.time()
        
        cmd = ['black']
        if not fix_issues:
            cmd.extend(['--check', '--diff'])
        
        source_paths = [str(self.project_path / path) for path in self.config['paths']['source']]
        cmd.extend(source_paths)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            issues = []
            if result.returncode != 0 and not fix_issues:
                # Parse Black output for formatting issues
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'would reformat' in line:
                        file_path = line.split()[1] if len(line.split()) > 1 else "unknown"
                        issues.append(QualityIssue(
                            check_name="black",
                            severity=Severity.MEDIUM,
                            message="Code formatting issues found",
                            file_path=file_path,
                            suggestion="Run 'black .' to fix formatting"
                        ))
            
            status = CheckStatus.PASSED if result.returncode == 0 else CheckStatus.FAILED
            
            return CheckResult(
                name="Black Formatting",
                status=status,
                duration=time.time() - start_time,
                issues=issues,
                metrics={'files_checked': len(source_paths)},
                output=result.stdout,
                error=result.stderr
            )
            
        except FileNotFoundError:
            return CheckResult(
                name="Black Formatting",
                status=CheckStatus.SKIPPED,
                duration=time.time() - start_time,
                issues=[],
                metrics={},
                error="Black not installed"
            )
    
    def _run_isort_check(self, fix_issues: bool = False) -> CheckResult:
        """Run isort import sorting check."""
        start_time = time.time()
        
        cmd = ['isort']
        if not fix_issues:
            cmd.extend(['--check-only', '--diff'])
        
        source_paths = [str(self.project_path / path) for path in self.config['paths']['source']]
        cmd.extend(source_paths)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            issues = []
            if result.returncode != 0 and not fix_issues:
                issues.append(QualityIssue(
                    check_name="isort",
                    severity=Severity.LOW,
                    message="Import sorting issues found",
                    suggestion="Run 'isort .' to fix import order"
                ))
            
            status = CheckStatus.PASSED if result.returncode == 0 else CheckStatus.FAILED
            
            return CheckResult(
                name="Import Sorting (isort)",
                status=status,
                duration=time.time() - start_time,
                issues=issues,
                metrics={'files_checked': len(source_paths)},
                output=result.stdout,
                error=result.stderr
            )
            
        except FileNotFoundError:
            return CheckResult(
                name="Import Sorting (isort)",
                status=CheckStatus.SKIPPED,
                duration=time.time() - start_time,
                issues=[],
                metrics={},
                error="isort not installed"
            )
    
    def _run_linting_checks(self) -> None:
        """Run code linting checks."""
        print("\n🔍 Running linting checks...")
        
        # Pylint check
        pylint_result = self._run_pylint_check()
        self.results.append(pylint_result)
        
        # Ruff check
        ruff_result = self._run_ruff_check()
        self.results.append(ruff_result)
    
    def _run_pylint_check(self) -> CheckResult:
        """Run Pylint code analysis."""
        start_time = time.time()
        
        source_paths = [str(self.project_path / path) for path in self.config['paths']['source']]
        
        cmd = ['pylint'] + source_paths + [
            '--output-format=json',
            '--rcfile=pyproject.toml'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            issues = []
            metrics = {'score': 0, 'total_issues': 0}
            
            if result.stdout:
                try:
                    pylint_output = json.loads(result.stdout)
                    for item in pylint_output:
                        severity_map = {
                            'error': Severity.HIGH,
                            'warning': Severity.MEDIUM,
                            'refactor': Severity.LOW,
                            'convention': Severity.LOW
                        }
                        
                        issues.append(QualityIssue(
                            check_name="pylint",
                            severity=severity_map.get(item.get('type', 'warning'), Severity.MEDIUM),
                            message=item.get('message', ''),
                            file_path=item.get('path', ''),
                            line_number=item.get('line', 0),
                            rule_id=item.get('message-id', '')
                        ))
                    
                    metrics['total_issues'] = len(issues)
                except json.JSONDecodeError:
                    pass
            
            # Extract score from stderr if available
            if result.stderr and 'rated at' in result.stderr:
                try:
                    score_line = [line for line in result.stderr.split('\n') if 'rated at' in line][0]
                    score = float(score_line.split('rated at ')[1].split('/')[0])
                    metrics['score'] = score
                except (IndexError, ValueError):
                    pass
            
            status = CheckStatus.PASSED if len(issues) == 0 else CheckStatus.WARNING
            
            return CheckResult(
                name="Pylint Analysis",
                status=status,
                duration=time.time() - start_time,
                issues=issues,
                metrics=metrics,
                output=result.stdout,
                error=result.stderr
            )
            
        except FileNotFoundError:
            return CheckResult(
                name="Pylint Analysis",
                status=CheckStatus.SKIPPED,
                duration=time.time() - start_time,
                issues=[],
                metrics={},
                error="Pylint not installed"
            )
    
    def _run_ruff_check(self) -> CheckResult:
        """Run Ruff fast linting."""
        start_time = time.time()
        
        source_paths = [str(self.project_path / path) for path in self.config['paths']['source']]
        
        cmd = ['ruff', 'check'] + source_paths + ['--output-format=json']
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            issues = []
            
            if result.stdout:
                try:
                    ruff_output = json.loads(result.stdout)
                    for item in ruff_output:
                        issues.append(QualityIssue(
                            check_name="ruff",
                            severity=Severity.MEDIUM,
                            message=item.get('message', ''),
                            file_path=item.get('filename', ''),
                            line_number=item.get('location', {}).get('row', 0),
                            rule_id=item.get('code', '')
                        ))
                except json.JSONDecodeError:
                    pass
            
            status = CheckStatus.PASSED if len(issues) == 0 else CheckStatus.WARNING
            
            return CheckResult(
                name="Ruff Linting",
                status=status,
                duration=time.time() - start_time,
                issues=issues,
                metrics={'total_issues': len(issues)},
                output=result.stdout,
                error=result.stderr
            )
            
        except FileNotFoundError:
            return CheckResult(
                name="Ruff Linting",
                status=CheckStatus.SKIPPED,
                duration=time.time() - start_time,
                issues=[],
                metrics={},
                error="Ruff not installed"
            )
    
    def _run_type_checks(self) -> None:
        """Run type checking."""
        print("\n🔬 Running type checks...")
        
        mypy_result = self._run_mypy_check()
        self.results.append(mypy_result)
    
    def _run_mypy_check(self) -> CheckResult:
        """Run MyPy type checking."""
        start_time = time.time()
        
        source_paths = [str(self.project_path / path) for path in self.config['paths']['source']]
        
        cmd = ['mypy'] + source_paths + [
            '--config-file=pyproject.toml',
            '--show-error-codes',
            '--no-error-summary'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            issues = []
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ':' in line and 'error:' in line:
                        parts = line.split(':')
                        if len(parts) >= 3:
                            file_path = parts[0]
                            line_number = int(parts[1]) if parts[1].isdigit() else 0
                            message = ':'.join(parts[3:]).strip()
                            
                            issues.append(QualityIssue(
                                check_name="mypy",
                                severity=Severity.MEDIUM,
                                message=message,
                                file_path=file_path,
                                line_number=line_number
                            ))
            
            status = CheckStatus.PASSED if result.returncode == 0 else CheckStatus.FAILED
            
            return CheckResult(
                name="MyPy Type Checking",
                status=status,
                duration=time.time() - start_time,
                issues=issues,
                metrics={'type_errors': len(issues)},
                output=result.stdout,
                error=result.stderr
            )
            
        except FileNotFoundError:
            return CheckResult(
                name="MyPy Type Checking",
                status=CheckStatus.SKIPPED,
                duration=time.time() - start_time,
                issues=[],
                metrics={},
                error="MyPy not installed"
            )
    
    def _run_security_checks(self) -> None:
        """Run security vulnerability checks."""
        print("\n🛡️ Running security checks...")
        
        bandit_result = self._run_bandit_check()
        self.results.append(bandit_result)
        
        safety_result = self._run_safety_check()
        self.results.append(safety_result)
    
    def _run_bandit_check(self) -> CheckResult:
        """Run Bandit security analysis."""
        start_time = time.time()
        
        source_paths = [str(self.project_path / path) for path in self.config['paths']['source']]
        
        cmd = ['bandit', '-r'] + source_paths + ['-f', 'json']
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            issues = []
            metrics = {'high': 0, 'medium': 0, 'low': 0}
            
            if result.stdout:
                try:
                    bandit_output = json.loads(result.stdout)
                    for item in bandit_output.get('results', []):
                        severity_map = {
                            'HIGH': Severity.HIGH,
                            'MEDIUM': Severity.MEDIUM,
                            'LOW': Severity.LOW
                        }
                        
                        severity = severity_map.get(item.get('issue_severity', 'MEDIUM'), Severity.MEDIUM)
                        metrics[severity.value] += 1
                        
                        issues.append(QualityIssue(
                            check_name="bandit",
                            severity=severity,
                            message=item.get('issue_text', ''),
                            file_path=item.get('filename', ''),
                            line_number=item.get('line_number', 0),
                            rule_id=item.get('test_id', '')
                        ))
                except json.JSONDecodeError:
                    pass
            
            # Determine status based on severity
            if metrics['high'] > 0:
                status = CheckStatus.FAILED
            elif metrics['medium'] > 0:
                status = CheckStatus.WARNING
            else:
                status = CheckStatus.PASSED
            
            return CheckResult(
                name="Bandit Security Analysis",
                status=status,
                duration=time.time() - start_time,
                issues=issues,
                metrics=metrics,
                output=result.stdout,
                error=result.stderr
            )
            
        except FileNotFoundError:
            return CheckResult(
                name="Bandit Security Analysis",
                status=CheckStatus.SKIPPED,
                duration=time.time() - start_time,
                issues=[],
                metrics={},
                error="Bandit not installed"
            )
    
    def _run_safety_check(self) -> CheckResult:
        """Run Safety dependency vulnerability check."""
        start_time = time.time()
        
        cmd = ['safety', 'check', '--json']
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            issues = []
            
            if result.stdout:
                try:
                    safety_output = json.loads(result.stdout)
                    for item in safety_output:
                        issues.append(QualityIssue(
                            check_name="safety",
                            severity=Severity.HIGH,
                            message=f"Vulnerable dependency: {item.get('package', 'unknown')}",
                            suggestion=f"Update to version {item.get('safe_version', 'latest')}"
                        ))
                except json.JSONDecodeError:
                    pass
            
            status = CheckStatus.PASSED if len(issues) == 0 else CheckStatus.FAILED
            
            return CheckResult(
                name="Safety Dependency Check",
                status=status,
                duration=time.time() - start_time,
                issues=issues,
                metrics={'vulnerable_packages': len(issues)},
                output=result.stdout,
                error=result.stderr
            )
            
        except FileNotFoundError:
            return CheckResult(
                name="Safety Dependency Check",
                status=CheckStatus.SKIPPED,
                duration=time.time() - start_time,
                issues=[],
                metrics={},
                error="Safety not installed"
            )
    
    def _run_test_checks(self) -> None:
        """Run test coverage analysis."""
        print("\n🧪 Running test coverage analysis...")
        
        coverage_result = self._run_coverage_check()
        self.results.append(coverage_result)
    
    def _run_coverage_check(self) -> CheckResult:
        """Run test coverage analysis."""
        start_time = time.time()
        
        # Run tests with coverage
        cmd = [
            'pytest',
            '--cov=scripts',
            '--cov-report=json',
            '--cov-report=term-missing',
            'tests/'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            issues = []
            metrics = {'coverage_percentage': 0, 'missing_lines': 0}
            
            # Read coverage report
            coverage_file = self.project_path / 'coverage.json'
            if coverage_file.exists():
                try:
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                    
                    total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
                    metrics['coverage_percentage'] = total_coverage
                    
                    # Check if coverage meets threshold
                    min_coverage = self.config['thresholds']['min_test_coverage']
                    if total_coverage < min_coverage:
                        issues.append(QualityIssue(
                            check_name="coverage",
                            severity=Severity.MEDIUM,
                            message=f"Test coverage {total_coverage:.1f}% below threshold {min_coverage}%",
                            suggestion="Add more tests to improve coverage"
                        ))
                    
                    # Check individual files
                    for file_path, file_data in coverage_data.get('files', {}).items():
                        file_coverage = file_data.get('summary', {}).get('percent_covered', 0)
                        if file_coverage < min_coverage:
                            missing_lines = len(file_data.get('missing_lines', []))
                            metrics['missing_lines'] += missing_lines
                            
                            issues.append(QualityIssue(
                                check_name="coverage",
                                severity=Severity.LOW,
                                message=f"Low coverage in {file_path}: {file_coverage:.1f}%",
                                file_path=file_path,
                                suggestion=f"Add tests for {missing_lines} uncovered lines"
                            ))
                    
                except (json.JSONDecodeError, FileNotFoundError):
                    pass
            
            status = CheckStatus.PASSED if len(issues) == 0 else CheckStatus.WARNING
            
            return CheckResult(
                name="Test Coverage Analysis",
                status=status,
                duration=time.time() - start_time,
                issues=issues,
                metrics=metrics,
                output=result.stdout,
                error=result.stderr
            )
            
        except FileNotFoundError:
            return CheckResult(
                name="Test Coverage Analysis",
                status=CheckStatus.SKIPPED,
                duration=time.time() - start_time,
                issues=[],
                metrics={},
                error="Pytest or coverage not installed"
            )
    
    def _run_documentation_checks(self) -> None:
        """Run documentation completeness checks."""
        print("\n📚 Running documentation checks...")
        
        docstring_result = self._run_docstring_check()
        self.results.append(docstring_result)
    
    def _run_docstring_check(self) -> CheckResult:
        """Check for missing docstrings."""
        start_time = time.time()
        
        issues = []
        total_functions = 0
        documented_functions = 0
        
        source_paths = [self.project_path / path for path in self.config['paths']['source']]
        
        for source_path in source_paths:
            if source_path.exists():
                for py_file in source_path.rglob('*.py'):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        import ast
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                                if not node.name.startswith('_'):  # Skip private functions
                                    total_functions += 1
                                    
                                    if ast.get_docstring(node):
                                        documented_functions += 1
                                    else:
                                        issues.append(QualityIssue(
                                            check_name="docstring",
                                            severity=Severity.LOW,
                                            message=f"Missing docstring for {node.__class__.__name__.lower()}: {node.name}",
                                            file_path=str(py_file.relative_to(self.project_path)),
                                            line_number=node.lineno,
                                            suggestion="Add docstring to document the function/class"
                                        ))
                    
                    except (SyntaxError, UnicodeDecodeError):
                        continue
        
        documentation_percentage = (documented_functions / total_functions * 100) if total_functions > 0 else 100
        
        metrics = {
            'total_functions': total_functions,
            'documented_functions': documented_functions,
            'documentation_percentage': documentation_percentage
        }
        
        status = CheckStatus.PASSED if documentation_percentage >= 80 else CheckStatus.WARNING
        
        return CheckResult(
            name="Documentation Check",
            status=status,
            duration=time.time() - start_time,
            issues=issues,
            metrics=metrics
        )
    
    def _run_performance_checks(self) -> None:
        """Run performance analysis."""
        print("\n⚡ Running performance checks...")
        
        import_result = self._run_import_analysis()
        self.results.append(import_result)
    
    def _run_import_analysis(self) -> CheckResult:
        """Analyze import performance."""
        start_time = time.time()
        
        issues = []
        metrics = {'slow_imports': 0, 'total_imports': 0}
        
        # This is a simplified import analysis
        # In a real implementation, you'd use tools like py-spy or import profiling
        
        source_paths = [self.project_path / path for path in self.config['paths']['source']]
        
        for source_path in source_paths:
            if source_path.exists():
                for py_file in source_path.rglob('*.py'):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        import ast
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.Import, ast.ImportFrom)):
                                metrics['total_imports'] += 1
                                
                                # Check for potentially slow imports
                                if isinstance(node, ast.ImportFrom):
                                    module = node.module or ''
                                    if any(slow_module in module for slow_module in 
                                          ['pandas', 'numpy', 'tensorflow', 'torch', 'matplotlib']):
                                        metrics['slow_imports'] += 1
                                        
                                        issues.append(QualityIssue(
                                            check_name="import_performance",
                                            severity=Severity.LOW,
                                            message=f"Potentially slow import: {module}",
                                            file_path=str(py_file.relative_to(self.project_path)),
                                            line_number=node.lineno,
                                            suggestion="Consider lazy importing or moving to function scope"
                                        ))
                    
                    except (SyntaxError, UnicodeDecodeError):
                        continue
        
        status = CheckStatus.PASSED if metrics['slow_imports'] == 0 else CheckStatus.WARNING
        
        return CheckResult(
            name="Import Performance Analysis",
            status=status,
            duration=time.time() - start_time,
            issues=issues,
            metrics=metrics
        )
    
    def _run_complexity_checks(self) -> None:
        """Run code complexity analysis."""
        print("\n🧮 Running complexity analysis...")
        
        complexity_result = self._run_complexity_analysis()
        self.results.append(complexity_result)
    
    def _run_complexity_analysis(self) -> CheckResult:
        """Analyze code complexity."""
        start_time = time.time()
        
        issues = []
        metrics = {'high_complexity_functions': 0, 'average_complexity': 0}
        
        # This is a simplified complexity analysis
        # In practice, you'd use tools like radon or mccabe
        
        source_paths = [self.project_path / path for path in self.config['paths']['source']]
        complexities = []
        
        for source_path in source_paths:
            if source_path.exists():
                for py_file in source_path.rglob('*.py'):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        import ast
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                # Simple complexity calculation (count decision points)
                                complexity = 1  # Base complexity
                                
                                for child in ast.walk(node):
                                    if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, 
                                                        ast.ExceptHandler, ast.With, ast.Assert)):
                                        complexity += 1
                                    elif isinstance(child, ast.BoolOp):
                                        complexity += len(child.values) - 1
                                
                                complexities.append(complexity)
                                
                                max_complexity = self.config['thresholds']['max_complexity']
                                if complexity > max_complexity:
                                    metrics['high_complexity_functions'] += 1
                                    
                                    issues.append(QualityIssue(
                                        check_name="complexity",
                                        severity=Severity.MEDIUM,
                                        message=f"High complexity function: {node.name} (complexity: {complexity})",
                                        file_path=str(py_file.relative_to(self.project_path)),
                                        line_number=node.lineno,
                                        suggestion="Consider breaking down into smaller functions"
                                    ))
                    
                    except (SyntaxError, UnicodeDecodeError):
                        continue
        
        if complexities:
            metrics['average_complexity'] = sum(complexities) / len(complexities)
        
        status = CheckStatus.PASSED if metrics['high_complexity_functions'] == 0 else CheckStatus.WARNING
        
        return CheckResult(
            name="Complexity Analysis",
            status=status,
            duration=time.time() - start_time,
            issues=issues,
            metrics=metrics
        )
    
    def _generate_report(self, total_duration: float) -> QualityReport:
        """Generate comprehensive quality report."""
        # Calculate overall status
        failed_checks = [r for r in self.results if r.status == CheckStatus.FAILED]
        warning_checks = [r for r in self.results if r.status == CheckStatus.WARNING]
        
        if failed_checks:
            overall_status = CheckStatus.FAILED
        elif warning_checks:
            overall_status = CheckStatus.WARNING
        else:
            overall_status = CheckStatus.PASSED
        
        # Generate summary
        total_issues = sum(len(r.issues) for r in self.results)
        critical_issues = sum(1 for r in self.results for i in r.issues if i.severity == Severity.CRITICAL)
        high_issues = sum(1 for r in self.results for i in r.issues if i.severity == Severity.HIGH)
        
        summary = {
            'total_checks': len(self.results),
            'passed_checks': len([r for r in self.results if r.status == CheckStatus.PASSED]),
            'failed_checks': len(failed_checks),
            'warning_checks': len(warning_checks),
            'skipped_checks': len([r for r in self.results if r.status == CheckStatus.SKIPPED]),
            'total_issues': total_issues,
            'critical_issues': critical_issues,
            'high_issues': high_issues,
            'quality_score': self._calculate_quality_score()
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        return QualityReport(
            timestamp=datetime.now().isoformat(),
            project_path=str(self.project_path),
            total_duration=total_duration,
            overall_status=overall_status,
            checks=self.results,
            summary=summary,
            recommendations=recommendations
        )
    
    def _calculate_quality_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        if not self.results:
            return 0.0
        
        total_weight = 0
        weighted_score = 0
        
        weights = {
            'security': 0.3,
            'testing': 0.25,
            'linting': 0.2,
            'formatting': 0.1,
            'typing': 0.1,
            'documentation': 0.05
        }
        
        for result in self.results:
            weight = 1.0  # Default weight
            
            # Assign weights based on check type
            check_name_lower = result.name.lower()
            for category, category_weight in weights.items():
                if category in check_name_lower:
                    weight = category_weight
                    break
            
            # Calculate score for this check
            if result.status == CheckStatus.PASSED:
                check_score = 100
            elif result.status == CheckStatus.WARNING:
                check_score = 70
            elif result.status == CheckStatus.FAILED:
                check_score = 30
            else:  # SKIPPED
                check_score = 50
            
            # Adjust score based on issue severity
            critical_issues = sum(1 for i in result.issues if i.severity == Severity.CRITICAL)
            high_issues = sum(1 for i in result.issues if i.severity == Severity.HIGH)
            
            if critical_issues > 0:
                check_score = min(check_score, 20)
            elif high_issues > 0:
                check_score = min(check_score, 50)
            
            weighted_score += check_score * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on results."""
        recommendations = []
        
        # Security recommendations
        security_issues = [i for r in self.results for i in r.issues 
                          if i.check_name in ['bandit', 'safety'] and i.severity in [Severity.HIGH, Severity.CRITICAL]]
        if security_issues:
            recommendations.append("🛡️ Address high-severity security vulnerabilities immediately")
            recommendations.append("🔄 Update vulnerable dependencies to secure versions")
        
        # Test coverage recommendations
        coverage_results = [r for r in self.results if 'coverage' in r.name.lower()]
        if coverage_results:
            coverage_result = coverage_results[0]
            coverage_pct = coverage_result.metrics.get('coverage_percentage', 0)
            if coverage_pct < 80:
                recommendations.append(f"🧪 Improve test coverage from {coverage_pct:.1f}% to at least 80%")
        
        # Code quality recommendations
        linting_issues = [i for r in self.results for i in r.issues if i.check_name in ['pylint', 'ruff']]
        if len(linting_issues) > 10:
            recommendations.append("🔍 Address linting issues to improve code quality")
        
        # Documentation recommendations
        doc_results = [r for r in self.results if 'documentation' in r.name.lower()]
        if doc_results:
            doc_result = doc_results[0]
            doc_pct = doc_result.metrics.get('documentation_percentage', 0)
            if doc_pct < 80:
                recommendations.append(f"📚 Improve documentation coverage from {doc_pct:.1f}% to at least 80%")
        
        # Performance recommendations
        perf_issues = [i for r in self.results for i in r.issues if 'performance' in i.check_name]
        if perf_issues:
            recommendations.append("⚡ Optimize slow imports and consider lazy loading")
        
        # Complexity recommendations
        complexity_issues = [i for r in self.results for i in r.issues if i.check_name == 'complexity']
        if complexity_issues:
            recommendations.append("🧮 Refactor high-complexity functions into smaller, more manageable pieces")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ Great job! Your code quality is excellent")
            recommendations.append("🚀 Consider setting up automated quality checks in CI/CD")
        
        return recommendations
    
    def _print_summary(self, report: QualityReport) -> None:
        """Print quality assessment summary."""
        print("\n" + "=" * 60)
        print("📊 QUALITY ASSESSMENT SUMMARY")
        print("=" * 60)
        
        # Overall status
        status_emoji = {
            CheckStatus.PASSED: "✅",
            CheckStatus.WARNING: "⚠️",
            CheckStatus.FAILED: "❌"
        }
        
        print(f"\n{status_emoji[report.overall_status]} Overall Status: {report.overall_status.value.upper()}")
        print(f"🎯 Quality Score: {report.summary['quality_score']:.1f}/100")
        print(f"⏱️ Total Duration: {report.total_duration:.2f}s")
        
        # Check summary
        print(f"\n📋 Check Summary:")
        print(f"   ✅ Passed: {report.summary['passed_checks']}")
        print(f"   ⚠️ Warnings: {report.summary['warning_checks']}")
        print(f"   ❌ Failed: {report.summary['failed_checks']}")
        print(f"   ⏭️ Skipped: {report.summary['skipped_checks']}")
        
        # Issue summary
        print(f"\n🐛 Issue Summary:")
        print(f"   🔴 Critical: {report.summary['critical_issues']}")
        print(f"   🟠 High: {report.summary['high_issues']}")
        print(f"   📊 Total: {report.summary['total_issues']}")
        
        # Individual check results
        print(f"\n📝 Individual Check Results:")
        for result in report.checks:
            status_icon = status_emoji.get(result.status, "❓")
            duration_str = f"({result.duration:.2f}s)"
            issue_count = f"[{len(result.issues)} issues]" if result.issues else ""
            
            print(f"   {status_icon} {result.name:<30} {duration_str:<8} {issue_count}")
        
        # Top recommendations
        if report.recommendations:
            print(f"\n💡 Top Recommendations:")
            for i, rec in enumerate(report.recommendations[:5], 1):
                print(f"   {i}. {rec}")
        
        # Quality score interpretation
        score = report.summary['quality_score']
        if score >= 90:
            print(f"\n🏆 Excellent! Your code quality is outstanding.")
        elif score >= 80:
            print(f"\n👍 Good! Your code quality is solid with room for minor improvements.")
        elif score >= 70:
            print(f"\n⚠️ Fair. Consider addressing the identified issues to improve quality.")
        else:
            print(f"\n🚨 Needs improvement. Please address critical issues before proceeding.")
        
        print("\n" + "=" * 60)
    
    def save_report(self, report: QualityReport, output_file: str) -> None:
        """Save quality report to file."""
        output_path = Path(output_file)
        
        # Convert report to dictionary for JSON serialization
        report_dict = asdict(report)
        
        # Convert enums to strings
        def convert_enums(obj):
            if isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif isinstance(obj, (CheckStatus, Severity)):
                return obj.value
            else:
                return obj
        
        report_dict = convert_enums(report_dict)
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        print(f"\n💾 Quality report saved to: {output_path}")


def main():
    """Main entry point for quality checker."""
    parser = argparse.ArgumentParser(
        description="Comprehensive code quality assessment tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python quality_check.py                    # Run all checks
  python quality_check.py --fix              # Run checks and fix issues
  python quality_check.py --output report.json  # Save report to file
  python quality_check.py --config custom.json  # Use custom configuration
        """
    )
    
    parser.add_argument(
        'project_path',
        nargs='?',
        default='.',
        help='Path to project directory (default: current directory)'
    )
    
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Automatically fix issues where possible'
    )
    
    parser.add_argument(
        '--output',
        help='Output file for quality report (JSON format)'
    )
    
    parser.add_argument(
        '--config',
        help='Path to custom configuration file'
    )
    
    parser.add_argument(
        '--fail-on-error',
        action='store_true',
        help='Exit with non-zero code if any checks fail'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = None
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ Error loading configuration: {e}")
            sys.exit(1)
    
    try:
        # Create quality checker
        checker = QualityChecker(args.project_path, config)
        
        # Run quality assessment
        report = checker.run_all_checks(fix_issues=args.fix)
        
        # Save report if requested
        if args.output:
            checker.save_report(report, args.output)
        
        # Exit with appropriate code
        if args.fail_on_error and report.overall_status == CheckStatus.FAILED:
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Quality check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()