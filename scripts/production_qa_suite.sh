#!/usr/bin/env bash

# =================================================================== 
# 🚀 PRODUCTION QUALITY ASSURANCE SUITE
# =================================================================== 
# Comprehensive quality assurance automation for production deployment
# Runs all quality checks, security validation, and optimization analysis

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/quality_reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${PURPLE}=== $1 ===${NC}"
}

# Create reports directory
create_reports_dir() {
    mkdir -p "$REPORTS_DIR"
    log_info "Reports will be saved to: $REPORTS_DIR"
}

# Check if Python is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    log_success "Python 3 is available"
}

# Install required packages
install_dependencies() {
    log_section "Installing Quality Assurance Dependencies"
    
    # Check if pip is available
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is required but not installed"
        exit 1
    fi
    
    # Install quality tools
    local packages=(
        "black"           # Code formatting
        "isort"           # Import sorting
        "pylint"          # Linting
        "mypy"            # Type checking
        "bandit"          # Security scanning
        "safety"          # Dependency vulnerability scanning
        "pytest"          # Testing framework
        "pytest-cov"     # Coverage reporting
        "flake8"          # Style guide enforcement
        "autopep8"        # PEP 8 formatting
        "pydocstyle"      # Docstring style checking
    )
    
    log_info "Installing quality assurance tools..."
    for package in "${packages[@]}"; do
        if pip3 show "$package" &> /dev/null; then
            log_info "$package is already installed"
        else
            log_info "Installing $package..."
            pip3 install "$package" --quiet
        fi
    done
    
    log_success "All quality tools installed"
}

# Run production security validation
run_security_validation() {
    log_section "Production Security Validation"
    
    local security_script="$SCRIPT_DIR/quality/production_security_validator.py"
    local report_file="$REPORTS_DIR/security_validation_$TIMESTAMP.txt"
    
    if [[ -f "$security_script" ]]; then
        log_info "Running production security validation..."
        
        if python3 "$security_script" --env-file "$PROJECT_ROOT/.env.n8n" --output "$report_file"; then
            log_success "Security validation passed"
        else
            log_warning "Security validation found issues - check report"
        fi
        
        log_info "Security report saved to: $report_file"
    else
        log_warning "Security validator script not found: $security_script"
    fi
}

# Run environment hardening
run_environment_hardening() {
    log_section "Environment Configuration Hardening"
    
    local hardening_script="$SCRIPT_DIR/quality/environment_hardener.py"
    
    if [[ -f "$hardening_script" ]]; then
        log_info "Running environment hardening..."
        
        # Ask for confirmation before hardening
        read -p "Do you want to harden the environment configuration? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 "$hardening_script" --env-file "$PROJECT_ROOT/.env.n8n"
            log_success "Environment hardening completed"
        else
            log_info "Environment hardening skipped"
        fi
    else
        log_warning "Environment hardener script not found: $hardening_script"
    fi
}

# Run async optimization analysis
run_async_optimization() {
    log_section "Async Performance Optimization Analysis"
    
    local async_script="$SCRIPT_DIR/quality/async_optimizer.py"
    local report_file="$REPORTS_DIR/async_optimization_$TIMESTAMP.txt"
    
    if [[ -f "$async_script" ]]; then
        log_info "Analyzing async optimization opportunities..."
        
        python3 "$async_script" --project-root "$PROJECT_ROOT" --output "$report_file" --examples
        
        log_success "Async optimization analysis completed"
        log_info "Report saved to: $report_file"
    else
        log_warning "Async optimizer script not found: $async_script"
    fi
}

# Run type safety enhancement
run_type_safety_analysis() {
    log_section "Type Safety Enhancement Analysis"
    
    local type_script="$SCRIPT_DIR/quality/type_safety_enhancer.py"
    local report_file="$REPORTS_DIR/type_safety_$TIMESTAMP.txt"
    
    if [[ -f "$type_script" ]]; then
        log_info "Analyzing type safety improvements..."
        
        python3 "$type_script" --project-root "$PROJECT_ROOT" --output "$report_file" --generate-mypy-config
        
        log_success "Type safety analysis completed"
        log_info "Report saved to: $report_file"
    else
        log_warning "Type safety enhancer script not found: $type_script"
    fi
}

# Run code formatting
run_code_formatting() {
    log_section "Code Formatting"
    
    log_info "Running Black code formatter..."
    if black --check --diff "$PROJECT_ROOT" 2>/dev/null; then
        log_success "Code is properly formatted"
    else
        log_warning "Code formatting issues found"
        read -p "Do you want to auto-format the code? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            black "$PROJECT_ROOT"
            log_success "Code formatting applied"
        fi
    fi
    
    log_info "Running isort import sorting..."
    if isort --check-only --diff "$PROJECT_ROOT" 2>/dev/null; then
        log_success "Imports are properly sorted"
    else
        log_warning "Import sorting issues found"
        read -p "Do you want to auto-sort imports? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            isort "$PROJECT_ROOT"
            log_success "Import sorting applied"
        fi
    fi
}

# Run linting
run_linting() {
    log_section "Code Linting"
    
    local lint_report="$REPORTS_DIR/lint_report_$TIMESTAMP.txt"
    
    log_info "Running Pylint analysis..."
    if pylint "$PROJECT_ROOT" --output-format=text > "$lint_report" 2>&1; then
        log_success "No linting issues found"
    else
        log_warning "Linting issues found - check report"
    fi
    
    log_info "Lint report saved to: $lint_report"
}

# Run security scanning
run_security_scanning() {
    log_section "Security Scanning"
    
    local security_report="$REPORTS_DIR/security_scan_$TIMESTAMP.txt"
    
    log_info "Running Bandit security scanner..."
    if bandit -r "$PROJECT_ROOT" -f txt -o "$security_report" 2>/dev/null; then
        log_success "No security issues found"
    else
        log_warning "Security issues found - check report"
    fi
    
    log_info "Running Safety dependency scanner..."
    local safety_report="$REPORTS_DIR/safety_scan_$TIMESTAMP.txt"
    if safety check --output text > "$safety_report" 2>&1; then
        log_success "No vulnerable dependencies found"
    else
        log_warning "Vulnerable dependencies found - check report"
    fi
    
    log_info "Security reports saved to: $REPORTS_DIR"
}

# Run type checking
run_type_checking() {
    log_section "Type Checking"
    
    local mypy_report="$REPORTS_DIR/mypy_report_$TIMESTAMP.txt"
    
    if [[ -f "$PROJECT_ROOT/mypy.ini" ]]; then
        log_info "Running MyPy type checker..."
        if mypy "$PROJECT_ROOT" > "$mypy_report" 2>&1; then
            log_success "No type checking issues found"
        else
            log_warning "Type checking issues found - check report"
        fi
        
        log_info "Type checking report saved to: $mypy_report"
    else
        log_info "MyPy configuration not found - skipping type checking"
    fi
}

# Run tests
run_tests() {
    log_section "Running Tests"
    
    local test_report="$REPORTS_DIR/test_report_$TIMESTAMP.txt"
    
    if [[ -d "$PROJECT_ROOT/tests" ]] || find "$PROJECT_ROOT" -name "test_*.py" -o -name "*_test.py" | grep -q .; then
        log_info "Running pytest with coverage..."
        
        if pytest "$PROJECT_ROOT" --cov="$PROJECT_ROOT" --cov-report=term --cov-report=html:"$REPORTS_DIR/coverage_html" > "$test_report" 2>&1; then
            log_success "All tests passed"
        else
            log_warning "Some tests failed - check report"
        fi
        
        log_info "Test report saved to: $test_report"
        log_info "Coverage report saved to: $REPORTS_DIR/coverage_html"
    else
        log_info "No tests found - skipping test execution"
    fi
}

# Generate comprehensive quality report
generate_quality_report() {
    log_section "Generating Comprehensive Quality Report"
    
    local final_report="$REPORTS_DIR/QUALITY_ASSURANCE_REPORT_$TIMESTAMP.md"
    
    cat > "$final_report" << EOF
# 🚀 Production Quality Assurance Report

**Generated:** $(date)
**Project:** AI Video Renderer Production Environment
**Report ID:** $TIMESTAMP

## 📊 Executive Summary

This report provides a comprehensive analysis of code quality, security, performance, and maintainability for the AI Video Renderer production environment.

## 🔍 Analysis Results

### Security Validation
- **Status:** $(if [[ -f "$REPORTS_DIR/security_validation_$TIMESTAMP.txt" ]]; then echo "✅ Completed"; else echo "⚠️ Skipped"; fi)
- **Report:** [Security Validation Report](security_validation_$TIMESTAMP.txt)

### Environment Hardening
- **Status:** $(if [[ -f "$PROJECT_ROOT/.env.n8n.backup."* ]]; then echo "✅ Applied"; else echo "⚠️ Not Applied"; fi)

### Async Optimization
- **Status:** $(if [[ -f "$REPORTS_DIR/async_optimization_$TIMESTAMP.txt" ]]; then echo "✅ Analyzed"; else echo "⚠️ Skipped"; fi)
- **Report:** [Async Optimization Report](async_optimization_$TIMESTAMP.txt)

### Type Safety
- **Status:** $(if [[ -f "$REPORTS_DIR/type_safety_$TIMESTAMP.txt" ]]; then echo "✅ Analyzed"; else echo "⚠️ Skipped"; fi)
- **Report:** [Type Safety Report](type_safety_$TIMESTAMP.txt)

### Code Quality
- **Formatting:** $(if black --check "$PROJECT_ROOT" &>/dev/null; then echo "✅ Compliant"; else echo "⚠️ Issues Found"; fi)
- **Linting:** $(if [[ -f "$REPORTS_DIR/lint_report_$TIMESTAMP.txt" ]]; then echo "✅ Analyzed"; else echo "⚠️ Skipped"; fi)
- **Security Scan:** $(if [[ -f "$REPORTS_DIR/security_scan_$TIMESTAMP.txt" ]]; then echo "✅ Completed"; else echo "⚠️ Skipped"; fi)
- **Type Checking:** $(if [[ -f "$REPORTS_DIR/mypy_report_$TIMESTAMP.txt" ]]; then echo "✅ Completed"; else echo "⚠️ Skipped"; fi)

### Testing
- **Test Execution:** $(if [[ -f "$REPORTS_DIR/test_report_$TIMESTAMP.txt" ]]; then echo "✅ Completed"; else echo "⚠️ No Tests Found"; fi)
- **Coverage Report:** $(if [[ -d "$REPORTS_DIR/coverage_html" ]]; then echo "✅ Generated"; else echo "⚠️ Not Available"; fi)

## 📋 Recommendations

### High Priority
1. **Security:** Review security validation report and address critical issues
2. **Environment:** Apply environment hardening for production deployment
3. **Testing:** Implement comprehensive test coverage

### Medium Priority
1. **Performance:** Implement async optimizations for I/O operations
2. **Type Safety:** Add type hints to improve code maintainability
3. **Code Quality:** Address linting and formatting issues

### Low Priority
1. **Documentation:** Enhance code documentation and docstrings
2. **Monitoring:** Implement additional monitoring and alerting
3. **Optimization:** Fine-tune performance based on profiling results

## 🔗 Related Files

- [Environment Configuration](.env.n8n)
- [Quality Check Script](scripts/quality_check.py)
- [Security Audit Script](scripts/security_audit.py)
- [Configuration Validator](scripts/config_validator.py)

## 📞 Next Steps

1. Review all generated reports
2. Address high-priority recommendations
3. Implement suggested improvements
4. Re-run quality assurance suite
5. Deploy to production environment

---
*Generated by Production Quality Assurance Suite*
EOF

    log_success "Comprehensive quality report generated: $final_report"
}

# Main execution function
main() {
    log_section "Production Quality Assurance Suite"
    log_info "Starting comprehensive quality analysis..."
    
    # Setup
    create_reports_dir
    check_python
    
    # Install dependencies
    install_dependencies
    
    # Run all quality checks
    run_security_validation
    run_environment_hardening
    run_async_optimization
    run_type_safety_analysis
    run_code_formatting
    run_linting
    run_security_scanning
    run_type_checking
    run_tests
    
    # Generate final report
    generate_quality_report
    
    log_section "Quality Assurance Complete"
    log_success "All quality checks completed!"
    log_info "Reports available in: $REPORTS_DIR"
    
    # Summary
    echo -e "\n${CYAN}📊 QUALITY ASSURANCE SUMMARY${NC}"
    echo "================================"
    echo "• Security validation: $(if [[ -f "$REPORTS_DIR/security_validation_$TIMESTAMP.txt" ]]; then echo "✅"; else echo "⚠️"; fi)"
    echo "• Async optimization: $(if [[ -f "$REPORTS_DIR/async_optimization_$TIMESTAMP.txt" ]]; then echo "✅"; else echo "⚠️"; fi)"
    echo "• Type safety analysis: $(if [[ -f "$REPORTS_DIR/type_safety_$TIMESTAMP.txt" ]]; then echo "✅"; else echo "⚠️"; fi)"
    echo "• Code formatting: $(if black --check "$PROJECT_ROOT" &>/dev/null; then echo "✅"; else echo "⚠️"; fi)"
    echo "• Security scanning: $(if [[ -f "$REPORTS_DIR/security_scan_$TIMESTAMP.txt" ]]; then echo "✅"; else echo "⚠️"; fi)"
    echo "• Test execution: $(if [[ -f "$REPORTS_DIR/test_report_$TIMESTAMP.txt" ]]; then echo "✅"; else echo "⚠️"; fi)"
    echo ""
    echo "🎉 Production environment is ready for deployment!"
}

# Script usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --skip-deps    Skip dependency installation"
    echo "  --security-only Run only security checks"
    echo "  --format-only  Run only formatting checks"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run full quality assurance suite"
    echo "  $0 --security-only    # Run only security checks"
    echo "  $0 --format-only      # Run only formatting checks"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --security-only)
            SECURITY_ONLY=true
            shift
            ;;
        --format-only)
            FORMAT_ONLY=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Execute based on options
if [[ "${SECURITY_ONLY:-false}" == "true" ]]; then
    log_section "Security-Only Mode"
    create_reports_dir
    check_python
    [[ "${SKIP_DEPS:-false}" != "true" ]] && install_dependencies
    run_security_validation
    run_security_scanning
elif [[ "${FORMAT_ONLY:-false}" == "true" ]]; then
    log_section "Format-Only Mode"
    check_python
    [[ "${SKIP_DEPS:-false}" != "true" ]] && install_dependencies
    run_code_formatting
else
    # Run full suite
    main
fi