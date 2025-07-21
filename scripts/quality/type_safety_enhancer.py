#!/usr/bin/env python3
"""
Comprehensive Type Safety Enhancer

Automatically adds type hints, validates existing types, and improves type safety
across the codebase using modern Python typing features.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TypeHint:
    """Represents a type hint suggestion."""
    file_path: str
    line_number: int
    element_type: str  # 'function', 'method', 'variable', 'class'
    element_name: str
    current_hint: Optional[str]
    suggested_hint: str
    confidence: str  # 'high', 'medium', 'low'
    reasoning: str


class TypeAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze and suggest type hints."""
    
    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.source_lines = source_code.split('\n')
        self.suggestions: List[TypeHint] = []
        self.current_class = None
        self.imports = set()
        self.typing_imports = set()
        
        # Common type patterns
        self.type_patterns = {
            'str': ['string', 'text', 'name', 'title', 'description', 'message', 'url', 'path'],
            'int': ['count', 'number', 'size', 'length', 'index', 'id', 'port', 'timeout'],
            'float': ['rate', 'score', 'percentage', 'ratio', 'price', 'weight'],
            'bool': ['enabled', 'active', 'valid', 'success', 'flag', 'is_', 'has_', 'can_'],
            'List': ['list', 'items', 'results', 'data', 'entries'],
            'Dict': ['config', 'settings', 'params', 'metadata', 'headers', 'mapping'],
            'Optional': ['default', 'fallback', 'backup']
        }
    
    def visit_Import(self, node: ast.Import) -> None:
        """Track imports for type hint suggestions."""
        for alias in node.names:
            self.imports.add(alias.name)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track typing imports."""
        if node.module == 'typing':
            for alias in node.names:
                self.typing_imports.add(alias.name)
        elif node.module:
            self.imports.add(node.module)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        old_class = self.current_class
        self.current_class = node.name
        
        # Analyze class for type hints
        self._analyze_class(node)
        
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to suggest type hints."""
        self._analyze_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        self._analyze_function(node)
        self.generic_visit(node)
    
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignments to validate types."""
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            current_hint = ast.unparse(node.annotation)
            
            # Validate the type hint
            self._validate_type_hint(node.lineno, var_name, current_hint)
        
        self.generic_visit(node)
    
    def _analyze_class(self, node: ast.ClassDef) -> None:
        """Analyze class for type improvements."""
        # Check if class should inherit from Protocol or ABC
        has_abstract_methods = any(
            isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and
            any(isinstance(decorator, ast.Name) and decorator.id == 'abstractmethod' 
                for decorator in child.decorator_list)
            for child in node.body
        )
        
        if has_abstract_methods and not any(
            isinstance(base, ast.Name) and base.id in ['ABC', 'Protocol']
            for base in node.bases
        ):
            self.suggestions.append(TypeHint(
                file_path=self.file_path,
                line_number=node.lineno,
                element_type='class',
                element_name=node.name,
                current_hint=None,
                suggested_hint='from abc import ABC',
                confidence='high',
                reasoning='Class has abstract methods but doesn\'t inherit from ABC'
            ))
    
    def _analyze_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> None:
        """Analyze function for type hint suggestions."""
        func_name = node.name
        
        # Skip magic methods and private methods for now
        if func_name.startswith('__') and func_name.endswith('__'):
            return
        
        # Analyze parameters
        for arg in node.args.args:
            if not arg.annotation:
                suggested_type = self._infer_parameter_type(arg.arg, node)
                if suggested_type:
                    self.suggestions.append(TypeHint(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        element_type='parameter',
                        element_name=f"{func_name}.{arg.arg}",
                        current_hint=None,
                        suggested_hint=suggested_type,
                        confidence='medium',
                        reasoning=f'Inferred from parameter name and usage patterns'
                    ))
        
        # Analyze return type
        if not node.returns:
            return_type = self._infer_return_type(node)
            if return_type:
                self.suggestions.append(TypeHint(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    element_type='return',
                    element_name=func_name,
                    current_hint=None,
                    suggested_hint=return_type,
                    confidence='medium',
                    reasoning='Inferred from return statements and function behavior'
                ))
    
    def _infer_parameter_type(self, param_name: str, func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Optional[str]:
        """Infer parameter type from name and usage."""
        param_lower = param_name.lower()
        
        # Check name patterns
        for type_name, patterns in self.type_patterns.items():
            if any(pattern in param_lower for pattern in patterns):
                if type_name == 'Optional' and param_name in self._get_default_params(func_node):
                    return f'Optional[str]'  # Default to Optional[str] for now
                return type_name
        
        # Check usage in function body
        usage_type = self._analyze_parameter_usage(param_name, func_node)
        if usage_type:
            return usage_type
        
        return None
    
    def _analyze_parameter_usage(self, param_name: str, func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Optional[str]:
        """Analyze how parameter is used to infer type."""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                # Check if parameter is used with specific methods
                if isinstance(node.func.value, ast.Name) and node.func.value.id == param_name:
                    method_name = node.func.attr
                    
                    # String methods
                    if method_name in ['split', 'strip', 'replace', 'format', 'lower', 'upper']:
                        return 'str'
                    
                    # List methods
                    elif method_name in ['append', 'extend', 'pop', 'remove', 'index']:
                        return 'List[Any]'
                    
                    # Dict methods
                    elif method_name in ['get', 'keys', 'values', 'items', 'update']:
                        return 'Dict[str, Any]'
            
            # Check if used in arithmetic operations
            elif isinstance(node, ast.BinOp):
                if isinstance(node.left, ast.Name) and node.left.id == param_name:
                    if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                        return 'Union[int, float]'
        
        return None
    
    def _infer_return_type(self, func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Optional[str]:
        """Infer return type from return statements."""
        return_types = set()
        has_none_return = False
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Return):
                if node.value is None:
                    has_none_return = True
                else:
                    inferred_type = self._infer_expression_type(node.value)
                    if inferred_type:
                        return_types.add(inferred_type)
        
        # Determine return type
        if not return_types and has_none_return:
            return 'None'
        elif len(return_types) == 1 and not has_none_return:
            return list(return_types)[0]
        elif len(return_types) == 1 and has_none_return:
            return f'Optional[{list(return_types)[0]}]'
        elif len(return_types) > 1:
            return f'Union[{", ".join(sorted(return_types))}]'
        
        return None
    
    def _infer_expression_type(self, node: ast.expr) -> Optional[str]:
        """Infer type from expression."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return 'str'
            elif isinstance(node.value, int):
                return 'int'
            elif isinstance(node.value, float):
                return 'float'
            elif isinstance(node.value, bool):
                return 'bool'
        
        elif isinstance(node, ast.List):
            return 'List[Any]'
        
        elif isinstance(node, ast.Dict):
            return 'Dict[str, Any]'
        
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in ['str', 'int', 'float', 'bool', 'list', 'dict']:
                    return func_name if func_name != 'list' else 'List[Any]'
        
        return None
    
    def _get_default_params(self, func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Set[str]:
        """Get parameters with default values."""
        defaults_count = len(func_node.args.defaults)
        if defaults_count == 0:
            return set()
        
        args_with_defaults = func_node.args.args[-defaults_count:]
        return {arg.arg for arg in args_with_defaults}
    
    def _validate_type_hint(self, line_number: int, var_name: str, type_hint: str) -> None:
        """Validate existing type hints for improvements."""
        # Check for overly broad types
        if type_hint == 'Any':
            self.suggestions.append(TypeHint(
                file_path=self.file_path,
                line_number=line_number,
                element_type='variable',
                element_name=var_name,
                current_hint=type_hint,
                suggested_hint='More specific type',
                confidence='low',
                reasoning='Consider using more specific type instead of Any'
            ))
        
        # Check for missing Union/Optional
        if 'None' in type_hint and not type_hint.startswith('Optional'):
            suggested = f'Optional[{type_hint.replace(" | None", "").replace("None | ", "")}]'
            self.suggestions.append(TypeHint(
                file_path=self.file_path,
                line_number=line_number,
                element_type='variable',
                element_name=var_name,
                current_hint=type_hint,
                suggested_hint=suggested,
                confidence='high',
                reasoning='Use Optional for nullable types'
            ))


class TypeSafetyEnhancer:
    """Main class for type safety enhancement."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.suggestions: List[TypeHint] = []
        
    def analyze_project(self) -> List[TypeHint]:
        """Analyze entire project for type safety improvements."""
        logger.info("🔍 Analyzing project for type safety improvements...")
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            # Skip virtual environments and build directories
            if any(skip in str(file_path) for skip in ['venv', '.venv', '__pycache__', 'build', 'dist']):
                continue
            
            try:
                self._analyze_file(file_path)
            except Exception as e:
                logger.warning(f"Error analyzing {file_path}: {e}")
        
        return self.suggestions
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            analyzer = TypeAnalyzer(str(file_path), content)
            analyzer.visit(tree)
            
            self.suggestions.extend(analyzer.suggestions)
            
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Error parsing {file_path}: {e}")
    
    def generate_type_stubs(self, output_dir: str = "stubs") -> None:
        """Generate .pyi stub files for better type checking."""
        stub_dir = Path(output_dir)
        stub_dir.mkdir(exist_ok=True)
        
        # Group suggestions by file
        by_file = {}
        for suggestion in self.suggestions:
            if suggestion.file_path not in by_file:
                by_file[suggestion.file_path] = []
            by_file[suggestion.file_path].append(suggestion)
        
        for file_path, suggestions in by_file.items():
            stub_content = self._generate_stub_content(file_path, suggestions)
            if stub_content:
                stub_file = stub_dir / f"{Path(file_path).stem}.pyi"
                with open(stub_file, 'w') as f:
                    f.write(stub_content)
                logger.info(f"Generated stub file: {stub_file}")
    
    def _generate_stub_content(self, file_path: str, suggestions: List[TypeHint]) -> str:
        """Generate content for a stub file."""
        lines = []
        lines.append("# Type stub file generated by TypeSafetyEnhancer")
        lines.append(f"# Source: {file_path}")
        lines.append("")
        
        # Add necessary imports
        typing_imports = set()
        for suggestion in suggestions:
            if 'Optional' in suggestion.suggested_hint:
                typing_imports.add('Optional')
            if 'Union' in suggestion.suggested_hint:
                typing_imports.add('Union')
            if 'List' in suggestion.suggested_hint:
                typing_imports.add('List')
            if 'Dict' in suggestion.suggested_hint:
                typing_imports.add('Dict')
            if 'Any' in suggestion.suggested_hint:
                typing_imports.add('Any')
        
        if typing_imports:
            lines.append(f"from typing import {', '.join(sorted(typing_imports))}")
            lines.append("")
        
        # Add function signatures
        for suggestion in suggestions:
            if suggestion.element_type in ['function', 'method']:
                lines.append(f"def {suggestion.element_name}(...) -> {suggestion.suggested_hint}: ...")
            elif suggestion.element_type == 'variable':
                lines.append(f"{suggestion.element_name}: {suggestion.suggested_hint}")
        
        return "\n".join(lines) if len(lines) > 3 else ""
    
    def generate_mypy_config(self) -> str:
        """Generate mypy configuration for strict type checking."""
        config = """[mypy]
# Type checking configuration generated by TypeSafetyEnhancer

# Import discovery
mypy_path = stubs
namespace_packages = True
explicit_package_bases = True

# Platform configuration
python_version = 3.8
platform = linux

# Disallow dynamic typing
disallow_any_unimported = True
disallow_any_expr = False
disallow_any_decorated = False
disallow_any_explicit = False
disallow_any_generics = True
disallow_subclassing_any = True

# Untyped definitions and calls
disallow_untyped_calls = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True

# None and Optional handling
no_implicit_optional = True
strict_optional = True

# Configuring warnings
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_return_any = True
warn_unreachable = True

# Miscellaneous strictness flags
allow_untyped_globals = False
allow_redefinition = False
local_partial_types = False
implicit_reexport = False
strict_equality = True

# Configuring error messages
show_error_context = True
show_column_numbers = True
show_error_codes = True
pretty = True
color_output = True
error_summary = True

# Incremental mode
incremental = True
cache_dir = .mypy_cache
sqlite_cache = True

# Advanced options
pdb = False
show_traceback = False
raise_exceptions = False

# Per-module options
[mypy-tests.*]
disallow_untyped_defs = False

[mypy-scripts.*]
disallow_untyped_defs = False
"""
        return config
    
    def generate_enhancement_report(self) -> str:
        """Generate comprehensive type safety enhancement report."""
        report = []
        report.append("🔒 TYPE SAFETY ENHANCEMENT REPORT")
        report.append("=" * 40)
        report.append(f"Total Suggestions: {len(self.suggestions)}")
        report.append("")
        
        # Group by confidence level
        by_confidence = {}
        for suggestion in self.suggestions:
            if suggestion.confidence not in by_confidence:
                by_confidence[suggestion.confidence] = []
            by_confidence[suggestion.confidence].append(suggestion)
        
        confidence_order = ['high', 'medium', 'low']
        confidence_icons = {'high': '🟢', 'medium': '🟡', 'low': '🔴'}
        
        for confidence in confidence_order:
            if confidence in by_confidence:
                suggestions = by_confidence[confidence]
                report.append(f"{confidence_icons[confidence]} {confidence.upper()} CONFIDENCE ({len(suggestions)} items)")
                report.append("-" * 35)
                
                # Group by element type
                by_type = {}
                for suggestion in suggestions:
                    if suggestion.element_type not in by_type:
                        by_type[suggestion.element_type] = []
                    by_type[suggestion.element_type].append(suggestion)
                
                for element_type, type_suggestions in by_type.items():
                    report.append(f"  📝 {element_type.title()} ({len(type_suggestions)} items):")
                    
                    for suggestion in type_suggestions[:5]:  # Show top 5
                        report.append(f"    • {suggestion.element_name}")
                        report.append(f"      Current: {suggestion.current_hint or 'None'}")
                        report.append(f"      Suggested: {suggestion.suggested_hint}")
                        report.append(f"      Reason: {suggestion.reasoning}")
                        report.append("")
                    
                    if len(type_suggestions) > 5:
                        report.append(f"    ... and {len(type_suggestions) - 5} more items")
                        report.append("")
                
                report.append("")
        
        # Add implementation guide
        report.append("📚 IMPLEMENTATION GUIDE")
        report.append("=" * 25)
        report.append("1. Install type checking tools:")
        report.append("   pip install mypy pyright")
        report.append("")
        report.append("2. Start with high-confidence suggestions")
        report.append("3. Add typing imports as needed:")
        report.append("   from typing import Optional, Union, List, Dict, Any")
        report.append("")
        report.append("4. Run type checker:")
        report.append("   mypy your_project/")
        report.append("")
        report.append("5. Use stub files for gradual typing")
        report.append("")
        
        # Add benefits
        report.append("🚀 TYPE SAFETY BENEFITS")
        report.append("=" * 25)
        report.append("• Catch bugs at development time")
        report.append("• Better IDE support and autocomplete")
        report.append("• Improved code documentation")
        report.append("• Enhanced refactoring safety")
        report.append("• Better team collaboration")
        
        return "\n".join(report)


def main():
    """Main entry point for type safety enhancement."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Type Safety Enhancer")
    parser.add_argument(
        '--project-root',
        default='.',
        help='Root directory of the project to analyze'
    )
    parser.add_argument(
        '--output',
        help='Output file for enhancement report'
    )
    parser.add_argument(
        '--generate-stubs',
        action='store_true',
        help='Generate .pyi stub files'
    )
    parser.add_argument(
        '--generate-mypy-config',
        action='store_true',
        help='Generate mypy.ini configuration file'
    )
    
    args = parser.parse_args()
    
    # Run analysis
    enhancer = TypeSafetyEnhancer(args.project_root)
    suggestions = enhancer.analyze_project()
    
    if not suggestions:
        print("✅ No type safety improvements needed!")
        return
    
    # Generate report
    report = enhancer.generate_enhancement_report()
    
    # Save or print output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Enhancement report saved to: {args.output}")
    else:
        print(report)
    
    # Generate stub files if requested
    if args.generate_stubs:
        enhancer.generate_type_stubs()
        print("✅ Type stub files generated in 'stubs' directory")
    
    # Generate mypy config if requested
    if args.generate_mypy_config:
        config = enhancer.generate_mypy_config()
        with open('mypy.ini', 'w') as f:
            f.write(config)
        print("✅ mypy.ini configuration file generated")


if __name__ == "__main__":
    main()