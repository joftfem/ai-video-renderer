#!/usr/bin/env python3
"""
Async Performance Optimizer

Enhances the codebase with async/await patterns for better performance.
Identifies synchronous operations that can benefit from async implementation.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import logging
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AsyncOpportunity:
    """Represents an opportunity for async optimization."""
    file_path: str
    line_number: int
    function_name: str
    operation_type: str
    description: str
    priority: str  # 'high', 'medium', 'low'
    suggested_change: str


class AsyncAnalyzer(ast.NodeVisitor):
    """AST visitor to identify async optimization opportunities."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.opportunities: List[AsyncOpportunity] = []
        self.current_function = None
        self.current_class = None
        
        # Patterns that indicate async opportunities
        self.io_operations = {
            'requests.get', 'requests.post', 'requests.put', 'requests.delete',
            'urllib.request.urlopen', 'urllib.request.urlretrieve',
            'open', 'file.read', 'file.write',
            'time.sleep', 'threading.sleep',
            'subprocess.run', 'subprocess.call', 'subprocess.Popen',
            'sqlite3.connect', 'psycopg2.connect', 'pymongo.MongoClient'
        }
        
        self.api_calls = {
            'youtube', 'google', 'openai', 'elevenlabs', 'telegram', 'discord',
            'vertex', 'bigquery', 'firestore', 'pinecone'
        }
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        old_function = self.current_function
        self.current_function = node.name
        
        # Check if function should be async
        if not node.name.startswith('async_') and not any(
            isinstance(decorator, ast.Name) and decorator.id == 'asyncio'
            for decorator in node.decorator_list
        ):
            self._analyze_function_for_async(node)
        
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to identify I/O operations."""
        call_name = self._get_call_name(node)
        
        if call_name:
            # Check for I/O operations
            if any(io_op in call_name.lower() for io_op in self.io_operations):
                self._add_opportunity(
                    node.lineno,
                    self.current_function or 'global',
                    'io_operation',
                    f'Synchronous I/O operation: {call_name}',
                    'high',
                    f'Replace with async equivalent (e.g., aiohttp, aiofiles)'
                )
            
            # Check for API calls
            elif any(api in call_name.lower() for api in self.api_calls):
                self._add_opportunity(
                    node.lineno,
                    self.current_function or 'global',
                    'api_call',
                    f'API call that could be async: {call_name}',
                    'medium',
                    f'Use async HTTP client for {call_name}'
                )
            
            # Check for database operations
            elif any(db_op in call_name.lower() for db_op in ['execute', 'query', 'fetch', 'commit']):
                self._add_opportunity(
                    node.lineno,
                    self.current_function or 'global',
                    'database_operation',
                    f'Database operation: {call_name}',
                    'medium',
                    f'Use async database driver for {call_name}'
                )
        
        self.generic_visit(node)
    
    def visit_For(self, node: ast.For) -> None:
        """Visit for loops to identify potential async iteration."""
        # Check if loop contains I/O operations
        io_in_loop = False
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child)
                if call_name and any(io_op in call_name.lower() for io_op in self.io_operations):
                    io_in_loop = True
                    break
        
        if io_in_loop:
            self._add_opportunity(
                node.lineno,
                self.current_function or 'global',
                'loop_with_io',
                'Loop contains I/O operations',
                'high',
                'Convert to async for loop with asyncio.gather() or asyncio.as_completed()'
            )
        
        self.generic_visit(node)
    
    def _analyze_function_for_async(self, node: ast.FunctionDef) -> None:
        """Analyze if entire function should be async."""
        io_operations_count = 0
        api_calls_count = 0
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child)
                if call_name:
                    if any(io_op in call_name.lower() for io_op in self.io_operations):
                        io_operations_count += 1
                    elif any(api in call_name.lower() for api in self.api_calls):
                        api_calls_count += 1
        
        if io_operations_count >= 2 or api_calls_count >= 2:
            self._add_opportunity(
                node.lineno,
                node.name,
                'function_async_conversion',
                f'Function with {io_operations_count} I/O ops and {api_calls_count} API calls',
                'high',
                f'Convert entire function to async def {node.name}()'
            )
    
    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract the name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
            elif isinstance(node.func.value, ast.Attribute):
                # Handle nested attributes like module.submodule.function
                parts = []
                current = node.func
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                return '.'.join(reversed(parts))
        return None
    
    def _add_opportunity(self, line_number: int, function_name: str, 
                        operation_type: str, description: str, 
                        priority: str, suggested_change: str) -> None:
        """Add an async optimization opportunity."""
        self.opportunities.append(AsyncOpportunity(
            file_path=self.file_path,
            line_number=line_number,
            function_name=function_name,
            operation_type=operation_type,
            description=description,
            priority=priority,
            suggested_change=suggested_change
        ))


class AsyncOptimizer:
    """Main class for async performance optimization analysis."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.opportunities: List[AsyncOpportunity] = []
        
    def analyze_project(self) -> List[AsyncOpportunity]:
        """Analyze entire project for async opportunities."""
        logger.info("🔍 Analyzing project for async optimization opportunities...")
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            # Skip virtual environments and build directories
            if any(skip in str(file_path) for skip in ['venv', '.venv', '__pycache__', 'build', 'dist']):
                continue
            
            try:
                self._analyze_file(file_path)
            except Exception as e:
                logger.warning(f"Error analyzing {file_path}: {e}")
        
        return self.opportunities
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            analyzer = AsyncAnalyzer(str(file_path))
            analyzer.visit(tree)
            
            self.opportunities.extend(analyzer.opportunities)
            
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Error parsing {file_path}: {e}")
    
    def generate_async_examples(self) -> Dict[str, str]:
        """Generate code examples for async conversions."""
        examples = {
            'requests_to_aiohttp': '''
# Before (synchronous)
import requests

def fetch_data(url):
    response = requests.get(url)
    return response.json()

# After (asynchronous)
import aiohttp
import asyncio

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
''',
            
            'file_io_to_aiofiles': '''
# Before (synchronous)
def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()

# After (asynchronous)
import aiofiles

async def read_file(filename):
    async with aiofiles.open(filename, 'r') as f:
        return await f.read()
''',
            
            'loop_with_io': '''
# Before (synchronous)
def process_urls(urls):
    results = []
    for url in urls:
        response = requests.get(url)
        results.append(response.json())
    return results

# After (asynchronous)
async def process_urls(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_data(session, url) for url in urls]
        return await asyncio.gather(*tasks)

async def fetch_data(session, url):
    async with session.get(url) as response:
        return await response.json()
''',
            
            'database_async': '''
# Before (synchronous)
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

# After (asynchronous)
import aiosqlite

async def get_user(user_id):
    async with aiosqlite.connect('database.db') as conn:
        cursor = await conn.cursor()
        await cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        result = await cursor.fetchone()
        return result
'''
        }
        return examples
    
    def generate_optimization_report(self) -> str:
        """Generate comprehensive async optimization report."""
        report = []
        report.append("⚡ ASYNC PERFORMANCE OPTIMIZATION REPORT")
        report.append("=" * 55)
        report.append(f"Total Opportunities Found: {len(self.opportunities)}")
        report.append("")
        
        # Group by priority
        by_priority = {}
        for opp in self.opportunities:
            if opp.priority not in by_priority:
                by_priority[opp.priority] = []
            by_priority[opp.priority].append(opp)
        
        priority_order = ['high', 'medium', 'low']
        priority_icons = {'high': '🔴', 'medium': '🟡', 'low': '🔵'}
        
        for priority in priority_order:
            if priority in by_priority:
                opportunities = by_priority[priority]
                report.append(f"{priority_icons[priority]} {priority.upper()} PRIORITY ({len(opportunities)} items)")
                report.append("-" * 40)
                
                for opp in opportunities:
                    report.append(f"📁 File: {opp.file_path}")
                    report.append(f"📍 Line: {opp.line_number}")
                    report.append(f"🔧 Function: {opp.function_name}")
                    report.append(f"📝 Issue: {opp.description}")
                    report.append(f"💡 Solution: {opp.suggested_change}")
                    report.append("")
        
        # Add implementation guide
        report.append("📚 IMPLEMENTATION GUIDE")
        report.append("=" * 25)
        report.append("1. Install async dependencies:")
        report.append("   pip install aiohttp aiofiles aiosqlite asyncio-mqtt")
        report.append("")
        report.append("2. Convert high-priority items first")
        report.append("3. Test each conversion thoroughly")
        report.append("4. Update error handling for async operations")
        report.append("5. Consider using asyncio.gather() for concurrent operations")
        report.append("")
        
        # Add performance benefits
        report.append("🚀 EXPECTED PERFORMANCE BENEFITS")
        report.append("=" * 35)
        report.append("• Improved I/O throughput (2-10x faster)")
        report.append("• Better resource utilization")
        report.append("• Reduced blocking operations")
        report.append("• Enhanced scalability")
        report.append("• Lower memory usage under load")
        
        return "\n".join(report)
    
    def generate_migration_plan(self) -> str:
        """Generate step-by-step migration plan."""
        plan = []
        plan.append("📋 ASYNC MIGRATION PLAN")
        plan.append("=" * 25)
        
        # Group by file for easier migration
        by_file = {}
        for opp in self.opportunities:
            if opp.file_path not in by_file:
                by_file[opp.file_path] = []
            by_file[opp.file_path].append(opp)
        
        # Sort files by number of high-priority opportunities
        file_priorities = []
        for file_path, opportunities in by_file.items():
            high_priority_count = sum(1 for opp in opportunities if opp.priority == 'high')
            file_priorities.append((high_priority_count, file_path, opportunities))
        
        file_priorities.sort(reverse=True)
        
        for i, (high_count, file_path, opportunities) in enumerate(file_priorities[:10], 1):
            plan.append(f"Phase {i}: {file_path}")
            plan.append(f"  High Priority Items: {high_count}")
            plan.append(f"  Total Items: {len(opportunities)}")
            
            # List specific changes
            for opp in opportunities[:3]:  # Show top 3 items
                plan.append(f"  • {opp.function_name}: {opp.description}")
            
            if len(opportunities) > 3:
                plan.append(f"  • ... and {len(opportunities) - 3} more items")
            
            plan.append("")
        
        return "\n".join(plan)


def main():
    """Main entry point for async optimization analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Async Performance Optimizer")
    parser.add_argument(
        '--project-root',
        default='.',
        help='Root directory of the project to analyze'
    )
    parser.add_argument(
        '--output',
        help='Output file for optimization report'
    )
    parser.add_argument(
        '--examples',
        action='store_true',
        help='Generate code examples for async conversions'
    )
    
    args = parser.parse_args()
    
    # Run analysis
    optimizer = AsyncOptimizer(args.project_root)
    opportunities = optimizer.analyze_project()
    
    if not opportunities:
        print("✅ No async optimization opportunities found!")
        return
    
    # Generate reports
    report = optimizer.generate_optimization_report()
    migration_plan = optimizer.generate_migration_plan()
    
    output_content = f"{report}\n\n{migration_plan}"
    
    if args.examples:
        examples = optimizer.generate_async_examples()
        output_content += "\n\n📝 CODE EXAMPLES\n" + "=" * 20 + "\n"
        for example_name, code in examples.items():
            output_content += f"\n{example_name.upper()}:\n{code}\n"
    
    # Save or print output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_content)
        print(f"Optimization report saved to: {args.output}")
    else:
        print(output_content)


if __name__ == "__main__":
    main()