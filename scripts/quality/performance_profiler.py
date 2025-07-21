#!/usr/bin/env python3
"""
Performance Profiling Tool

Advanced performance analysis and optimization recommendations for the AI Video Renderer.
Provides detailed insights into:
- Memory usage patterns
- CPU utilization
- I/O operations
- Function call profiling
- Async operation analysis
- Database query performance
- API call latency
"""

import os
import sys
import time
import psutil
import asyncio
import threading
import tracemalloc
import cProfile
import pstats
import io
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from collections import defaultdict, deque
import functools
import inspect
import gc
import resource

try:
    import line_profiler
    LINE_PROFILER_AVAILABLE = True
except ImportError:
    LINE_PROFILER_AVAILABLE = False

try:
    import memory_profiler
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False

try:
    import py_spy
    PY_SPY_AVAILABLE = True
except ImportError:
    PY_SPY_AVAILABLE = False


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    timestamp: str
    duration: float
    cpu_percent: float
    memory_mb: float
    memory_peak_mb: float
    io_read_bytes: int
    io_write_bytes: int
    function_calls: int
    async_tasks: int
    gc_collections: Dict[int, int]
    custom_metrics: Dict[str, Any]


@dataclass
class FunctionProfile:
    """Profile data for a specific function."""
    name: str
    module: str
    filename: str
    line_number: int
    call_count: int
    total_time: float
    cumulative_time: float
    average_time: float
    memory_usage: float
    peak_memory: float
    children: List['FunctionProfile']


@dataclass
class AsyncTaskProfile:
    """Profile data for async tasks."""
    name: str
    creation_time: float
    start_time: Optional[float]
    end_time: Optional[float]
    duration: Optional[float]
    status: str
    memory_usage: float
    exception: Optional[str]


@dataclass
class PerformanceReport:
    """Comprehensive performance analysis report."""
    timestamp: str
    project_path: str
    total_duration: float
    overall_metrics: PerformanceMetrics
    function_profiles: List[FunctionProfile]
    async_profiles: List[AsyncTaskProfile]
    memory_timeline: List[Dict[str, Any]]
    cpu_timeline: List[Dict[str, Any]]
    io_timeline: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]
    recommendations: List[str]
    optimization_opportunities: List[Dict[str, Any]]


class MemoryTracker:
    """Advanced memory usage tracking."""
    
    def __init__(self):
        self.snapshots = []
        self.peak_memory = 0
        self.baseline_memory = 0
        self.tracking_active = False
        
    def start_tracking(self):
        """Start memory tracking."""
        tracemalloc.start()
        self.baseline_memory = self._get_current_memory()
        self.tracking_active = True
        
    def stop_tracking(self):
        """Stop memory tracking."""
        if self.tracking_active:
            tracemalloc.stop()
            self.tracking_active = False
    
    def take_snapshot(self, label: str = ""):
        """Take a memory snapshot."""
        if not self.tracking_active:
            return
            
        current_memory = self._get_current_memory()
        self.peak_memory = max(self.peak_memory, current_memory)
        
        snapshot = {
            'timestamp': time.time(),
            'label': label,
            'memory_mb': current_memory,
            'memory_diff_mb': current_memory - self.baseline_memory,
            'tracemalloc_snapshot': tracemalloc.take_snapshot() if tracemalloc.is_tracing() else None
        }
        
        self.snapshots.append(snapshot)
        return snapshot
    
    def _get_current_memory(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def analyze_memory_leaks(self) -> List[Dict[str, Any]]:
        """Analyze potential memory leaks."""
        leaks = []
        
        if len(self.snapshots) < 2:
            return leaks
        
        # Check for consistent memory growth
        memory_values = [s['memory_mb'] for s in self.snapshots]
        growth_rate = (memory_values[-1] - memory_values[0]) / len(memory_values)
        
        if growth_rate > 1.0:  # More than 1MB growth per snapshot
            leaks.append({
                'type': 'consistent_growth',
                'growth_rate_mb': growth_rate,
                'total_growth_mb': memory_values[-1] - memory_values[0],
                'severity': 'high' if growth_rate > 5.0 else 'medium'
            })
        
        # Analyze tracemalloc data if available
        if self.snapshots[-1]['tracemalloc_snapshot']:
            snapshot = self.snapshots[-1]['tracemalloc_snapshot']
            top_stats = snapshot.statistics('lineno')[:10]
            
            for stat in top_stats:
                if stat.size > 1024 * 1024:  # More than 1MB
                    leaks.append({
                        'type': 'large_allocation',
                        'size_mb': stat.size / 1024 / 1024,
                        'filename': stat.traceback.format()[0] if stat.traceback else 'unknown',
                        'count': stat.count,
                        'severity': 'high' if stat.size > 10 * 1024 * 1024 else 'medium'
                    })
        
        return leaks


class CPUProfiler:
    """CPU usage profiling and analysis."""
    
    def __init__(self):
        self.cpu_samples = deque(maxlen=1000)
        self.profiler = None
        self.profiling_active = False
        
    def start_profiling(self):
        """Start CPU profiling."""
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        self.profiling_active = True
        
        # Start CPU sampling in background
        self._start_cpu_sampling()
    
    def stop_profiling(self):
        """Stop CPU profiling."""
        if self.profiling_active:
            self.profiler.disable()
            self.profiling_active = False
    
    def _start_cpu_sampling(self):
        """Start background CPU sampling."""
        def sample_cpu():
            while self.profiling_active:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.cpu_samples.append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent
                })
                time.sleep(0.1)
        
        thread = threading.Thread(target=sample_cpu, daemon=True)
        thread.start()
    
    def get_function_stats(self) -> List[FunctionProfile]:
        """Get function-level performance statistics."""
        if not self.profiler:
            return []
        
        # Capture profiler output
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(50)  # Top 50 functions
        
        # Parse profiler output
        profiles = []
        lines = s.getvalue().split('\n')
        
        for line in lines:
            if '(' in line and ')' in line and '.py:' in line:
                try:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        ncalls = int(parts[0].split('/')[0])
                        tottime = float(parts[1])
                        cumtime = float(parts[3])
                        
                        # Extract filename and function name
                        func_info = line[line.find('('):line.find(')')]
                        if ':' in func_info:
                            filename, line_num = func_info.split(':')[:2]
                            filename = filename.strip('(')
                            line_num = int(line_num) if line_num.isdigit() else 0
                        else:
                            filename = 'unknown'
                            line_num = 0
                        
                        func_name = line[line.find(')') + 1:].strip()
                        
                        profile = FunctionProfile(
                            name=func_name,
                            module=Path(filename).stem if filename != 'unknown' else 'unknown',
                            filename=filename,
                            line_number=line_num,
                            call_count=ncalls,
                            total_time=tottime,
                            cumulative_time=cumtime,
                            average_time=tottime / ncalls if ncalls > 0 else 0,
                            memory_usage=0,  # Would need memory profiler integration
                            peak_memory=0,
                            children=[]
                        )
                        
                        profiles.append(profile)
                        
                except (ValueError, IndexError):
                    continue
        
        return profiles
    
    def analyze_cpu_bottlenecks(self) -> List[Dict[str, Any]]:
        """Analyze CPU usage patterns for bottlenecks."""
        bottlenecks = []
        
        if not self.cpu_samples:
            return bottlenecks
        
        cpu_values = [sample['cpu_percent'] for sample in self.cpu_samples]
        avg_cpu = sum(cpu_values) / len(cpu_values)
        max_cpu = max(cpu_values)
        
        # High average CPU usage
        if avg_cpu > 80:
            bottlenecks.append({
                'type': 'high_average_cpu',
                'average_cpu': avg_cpu,
                'max_cpu': max_cpu,
                'severity': 'high' if avg_cpu > 90 else 'medium',
                'recommendation': 'Consider optimizing CPU-intensive operations or adding parallelization'
            })
        
        # CPU spikes
        spikes = [cpu for cpu in cpu_values if cpu > 95]
        if len(spikes) > len(cpu_values) * 0.1:  # More than 10% spikes
            bottlenecks.append({
                'type': 'cpu_spikes',
                'spike_count': len(spikes),
                'spike_percentage': len(spikes) / len(cpu_values) * 100,
                'severity': 'medium',
                'recommendation': 'Investigate functions causing CPU spikes'
            })
        
        return bottlenecks


class AsyncProfiler:
    """Async operation profiling and analysis."""
    
    def __init__(self):
        self.task_profiles = {}
        self.active_tasks = set()
        self.completed_tasks = []
        
    def track_task(self, task: asyncio.Task, name: str = None):
        """Track an async task."""
        task_id = id(task)
        task_name = name or getattr(task, '__name__', f'Task-{task_id}')
        
        profile = AsyncTaskProfile(
            name=task_name,
            creation_time=time.time(),
            start_time=None,
            end_time=None,
            duration=None,
            status='created',
            memory_usage=0,
            exception=None
        )
        
        self.task_profiles[task_id] = profile
        self.active_tasks.add(task_id)
        
        # Add callbacks to track task lifecycle
        task.add_done_callback(lambda t: self._task_completed(task_id, t))
        
        return profile
    
    def _task_completed(self, task_id: int, task: asyncio.Task):
        """Handle task completion."""
        if task_id in self.task_profiles:
            profile = self.task_profiles[task_id]
            profile.end_time = time.time()
            
            if profile.start_time:
                profile.duration = profile.end_time - profile.start_time
            
            if task.cancelled():
                profile.status = 'cancelled'
            elif task.exception():
                profile.status = 'failed'
                profile.exception = str(task.exception())
            else:
                profile.status = 'completed'
            
            self.active_tasks.discard(task_id)
            self.completed_tasks.append(profile)
    
    def analyze_async_performance(self) -> List[Dict[str, Any]]:
        """Analyze async operation performance."""
        analysis = []
        
        if not self.completed_tasks:
            return analysis
        
        # Calculate statistics
        durations = [t.duration for t in self.completed_tasks if t.duration]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            
            # Long-running tasks
            long_tasks = [t for t in self.completed_tasks if t.duration and t.duration > avg_duration * 3]
            if long_tasks:
                analysis.append({
                    'type': 'long_running_tasks',
                    'count': len(long_tasks),
                    'average_duration': avg_duration,
                    'max_duration': max_duration,
                    'tasks': [{'name': t.name, 'duration': t.duration} for t in long_tasks[:5]],
                    'recommendation': 'Consider breaking down long-running tasks or adding progress indicators'
                })
        
        # Failed tasks
        failed_tasks = [t for t in self.completed_tasks if t.status == 'failed']
        if failed_tasks:
            analysis.append({
                'type': 'failed_tasks',
                'count': len(failed_tasks),
                'failure_rate': len(failed_tasks) / len(self.completed_tasks) * 100,
                'common_exceptions': self._get_common_exceptions(failed_tasks),
                'recommendation': 'Implement better error handling and retry mechanisms'
            })
        
        # Cancelled tasks
        cancelled_tasks = [t for t in self.completed_tasks if t.status == 'cancelled']
        if cancelled_tasks:
            analysis.append({
                'type': 'cancelled_tasks',
                'count': len(cancelled_tasks),
                'cancellation_rate': len(cancelled_tasks) / len(self.completed_tasks) * 100,
                'recommendation': 'Review task cancellation patterns and timeout settings'
            })
        
        return analysis
    
    def _get_common_exceptions(self, failed_tasks: List[AsyncTaskProfile]) -> Dict[str, int]:
        """Get common exception types from failed tasks."""
        exceptions = defaultdict(int)
        for task in failed_tasks:
            if task.exception:
                exc_type = task.exception.split(':')[0] if ':' in task.exception else task.exception
                exceptions[exc_type] += 1
        return dict(exceptions)


class IOProfiler:
    """I/O operation profiling and analysis."""
    
    def __init__(self):
        self.io_operations = []
        self.baseline_io = None
        
    def start_monitoring(self):
        """Start I/O monitoring."""
        process = psutil.Process()
        self.baseline_io = process.io_counters()
    
    def record_operation(self, operation_type: str, size_bytes: int, duration: float, path: str = None):
        """Record an I/O operation."""
        operation = {
            'timestamp': time.time(),
            'type': operation_type,
            'size_bytes': size_bytes,
            'duration': duration,
            'path': path,
            'throughput_mbps': (size_bytes / 1024 / 1024) / duration if duration > 0 else 0
        }
        
        self.io_operations.append(operation)
        return operation
    
    def get_io_stats(self) -> Dict[str, Any]:
        """Get I/O statistics."""
        if not self.baseline_io:
            return {}
        
        process = psutil.Process()
        current_io = process.io_counters()
        
        return {
            'read_bytes': current_io.read_bytes - self.baseline_io.read_bytes,
            'write_bytes': current_io.write_bytes - self.baseline_io.write_bytes,
            'read_count': current_io.read_count - self.baseline_io.read_count,
            'write_count': current_io.write_count - self.baseline_io.write_count
        }
    
    def analyze_io_patterns(self) -> List[Dict[str, Any]]:
        """Analyze I/O operation patterns."""
        analysis = []
        
        if not self.io_operations:
            return analysis
        
        # Group operations by type
        by_type = defaultdict(list)
        for op in self.io_operations:
            by_type[op['type']].append(op)
        
        for op_type, operations in by_type.items():
            total_size = sum(op['size_bytes'] for op in operations)
            total_duration = sum(op['duration'] for op in operations)
            avg_throughput = sum(op['throughput_mbps'] for op in operations) / len(operations)
            
            # Slow operations
            slow_ops = [op for op in operations if op['throughput_mbps'] < avg_throughput * 0.5]
            if slow_ops:
                analysis.append({
                    'type': f'slow_{op_type}_operations',
                    'count': len(slow_ops),
                    'total_operations': len(operations),
                    'average_throughput_mbps': avg_throughput,
                    'slow_operations': slow_ops[:5],
                    'recommendation': f'Optimize {op_type} operations or consider caching'
                })
            
            # Large operations
            large_ops = [op for op in operations if op['size_bytes'] > 10 * 1024 * 1024]  # > 10MB
            if large_ops:
                analysis.append({
                    'type': f'large_{op_type}_operations',
                    'count': len(large_ops),
                    'total_size_mb': sum(op['size_bytes'] for op in large_ops) / 1024 / 1024,
                    'recommendation': f'Consider streaming or chunking large {op_type} operations'
                })
        
        return analysis


class PerformanceProfiler:
    """Main performance profiler orchestrator."""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.memory_tracker = MemoryTracker()
        self.cpu_profiler = CPUProfiler()
        self.async_profiler = AsyncProfiler()
        self.io_profiler = IOProfiler()
        
        self.start_time = None
        self.end_time = None
        self.custom_metrics = {}
        
    @contextmanager
    def profile_context(self, label: str = "performance_analysis"):
        """Context manager for profiling a code block."""
        self.start_profiling(label)
        try:
            yield self
        finally:
            self.stop_profiling()
    
    def start_profiling(self, label: str = "performance_analysis"):
        """Start comprehensive profiling."""
        print(f"🚀 Starting performance profiling: {label}")
        
        self.start_time = time.time()
        
        # Start all profilers
        self.memory_tracker.start_tracking()
        self.cpu_profiler.start_profiling()
        self.io_profiler.start_monitoring()
        
        # Take initial snapshots
        self.memory_tracker.take_snapshot("profiling_start")
        
        # Force garbage collection for clean baseline
        gc.collect()
    
    def stop_profiling(self):
        """Stop profiling and generate report."""
        self.end_time = time.time()
        
        print(f"⏹️ Stopping performance profiling")
        
        # Take final snapshots
        self.memory_tracker.take_snapshot("profiling_end")
        
        # Stop all profilers
        self.memory_tracker.stop_tracking()
        self.cpu_profiler.stop_profiling()
        
        # Force final garbage collection
        gc.collect()
    
    def add_custom_metric(self, name: str, value: Any, timestamp: float = None):
        """Add a custom performance metric."""
        if timestamp is None:
            timestamp = time.time()
        
        if name not in self.custom_metrics:
            self.custom_metrics[name] = []
        
        self.custom_metrics[name].append({
            'timestamp': timestamp,
            'value': value
        })
    
    def profile_function(self, func: Callable, *args, **kwargs):
        """Profile a specific function call."""
        with self.profile_context(f"function_{func.__name__}"):
            start_memory = self.memory_tracker._get_current_memory()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
            
            end_time = time.time()
            end_memory = self.memory_tracker._get_current_memory()
            
            # Record function metrics
            self.add_custom_metric(f"{func.__name__}_duration", end_time - start_time)
            self.add_custom_metric(f"{func.__name__}_memory_delta", end_memory - start_memory)
            self.add_custom_metric(f"{func.__name__}_success", success)
            
            if error:
                self.add_custom_metric(f"{func.__name__}_error", error)
            
            return result
    
    async def profile_async_function(self, coro):
        """Profile an async function or coroutine."""
        task = asyncio.create_task(coro)
        self.async_profiler.track_task(task, getattr(coro, '__name__', 'async_function'))
        
        start_memory = self.memory_tracker._get_current_memory()
        start_time = time.time()
        
        try:
            result = await task
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        end_memory = self.memory_tracker._get_current_memory()
        
        # Record async function metrics
        func_name = getattr(coro, '__name__', 'async_function')
        self.add_custom_metric(f"{func_name}_duration", end_time - start_time)
        self.add_custom_metric(f"{func_name}_memory_delta", end_memory - start_memory)
        self.add_custom_metric(f"{func_name}_success", success)
        
        if error:
            self.add_custom_metric(f"{func_name}_error", error)
        
        return result
    
    def generate_report(self) -> PerformanceReport:
        """Generate comprehensive performance report."""
        if not self.start_time or not self.end_time:
            raise ValueError("Profiling not completed. Call start_profiling() and stop_profiling() first.")
        
        total_duration = self.end_time - self.start_time
        
        print(f"📊 Generating performance report...")
        
        # Collect overall metrics
        process = psutil.Process()
        memory_info = process.memory_info()
        
        overall_metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            duration=total_duration,
            cpu_percent=process.cpu_percent(),
            memory_mb=memory_info.rss / 1024 / 1024,
            memory_peak_mb=self.memory_tracker.peak_memory,
            io_read_bytes=0,  # Will be filled from IO profiler
            io_write_bytes=0,
            function_calls=len(self.cpu_profiler.get_function_stats()),
            async_tasks=len(self.async_profiler.completed_tasks),
            gc_collections={i: gc.get_count()[i] for i in range(3)},
            custom_metrics=self.custom_metrics
        )
        
        # Update IO stats
        io_stats = self.io_profiler.get_io_stats()
        overall_metrics.io_read_bytes = io_stats.get('read_bytes', 0)
        overall_metrics.io_write_bytes = io_stats.get('write_bytes', 0)
        
        # Collect detailed profiles
        function_profiles = self.cpu_profiler.get_function_stats()
        async_profiles = self.async_profiler.completed_tasks
        
        # Create timelines
        memory_timeline = [{
            'timestamp': snapshot['timestamp'],
            'memory_mb': snapshot['memory_mb'],
            'label': snapshot['label']
        } for snapshot in self.memory_tracker.snapshots]
        
        cpu_timeline = [{
            'timestamp': sample['timestamp'],
            'cpu_percent': sample['cpu_percent']
        } for sample in self.cpu_profiler.cpu_samples]
        
        io_timeline = [{
            'timestamp': op['timestamp'],
            'type': op['type'],
            'size_bytes': op['size_bytes'],
            'duration': op['duration'],
            'throughput_mbps': op['throughput_mbps']
        } for op in self.io_profiler.io_operations]
        
        # Analyze bottlenecks
        bottlenecks = []
        bottlenecks.extend(self.memory_tracker.analyze_memory_leaks())
        bottlenecks.extend(self.cpu_profiler.analyze_cpu_bottlenecks())
        bottlenecks.extend(self.async_profiler.analyze_async_performance())
        bottlenecks.extend(self.io_profiler.analyze_io_patterns())
        
        # Generate recommendations
        recommendations = self._generate_recommendations(overall_metrics, bottlenecks)
        
        # Find optimization opportunities
        optimization_opportunities = self._find_optimization_opportunities(
            function_profiles, async_profiles, bottlenecks
        )
        
        return PerformanceReport(
            timestamp=datetime.now().isoformat(),
            project_path=str(self.project_path),
            total_duration=total_duration,
            overall_metrics=overall_metrics,
            function_profiles=function_profiles,
            async_profiles=async_profiles,
            memory_timeline=memory_timeline,
            cpu_timeline=cpu_timeline,
            io_timeline=io_timeline,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            optimization_opportunities=optimization_opportunities
        )
    
    def _generate_recommendations(self, metrics: PerformanceMetrics, bottlenecks: List[Dict]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Memory recommendations
        if metrics.memory_peak_mb > 1000:  # > 1GB
            recommendations.append(
                f"🧠 High memory usage detected ({metrics.memory_peak_mb:.1f}MB peak). "
                "Consider implementing memory pooling or streaming for large data."
            )
        
        # CPU recommendations
        if metrics.cpu_percent > 80:
            recommendations.append(
                f"⚡ High CPU usage detected ({metrics.cpu_percent:.1f}%). "
                "Consider parallelization or algorithm optimization."
            )
        
        # Async recommendations
        if metrics.async_tasks > 100:
            recommendations.append(
                f"🔄 Many async tasks detected ({metrics.async_tasks}). "
                "Consider task pooling or batching to reduce overhead."
            )
        
        # I/O recommendations
        if metrics.io_read_bytes + metrics.io_write_bytes > 100 * 1024 * 1024:  # > 100MB
            recommendations.append(
                f"💾 High I/O activity detected. Consider caching, compression, or async I/O."
            )
        
        # Bottleneck-specific recommendations
        for bottleneck in bottlenecks:
            if 'recommendation' in bottleneck:
                recommendations.append(f"🎯 {bottleneck['recommendation']}")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ Performance looks good! Consider setting up continuous monitoring.")
        
        return recommendations
    
    def _find_optimization_opportunities(self, function_profiles: List[FunctionProfile], 
                                       async_profiles: List[AsyncTaskProfile], 
                                       bottlenecks: List[Dict]) -> List[Dict[str, Any]]:
        """Find specific optimization opportunities."""
        opportunities = []
        
        # Slow functions
        slow_functions = [f for f in function_profiles if f.average_time > 0.1]  # > 100ms
        if slow_functions:
            opportunities.append({
                'type': 'slow_functions',
                'count': len(slow_functions),
                'functions': [{
                    'name': f.name,
                    'average_time': f.average_time,
                    'call_count': f.call_count,
                    'total_time': f.total_time
                } for f in slow_functions[:5]],
                'impact': 'high',
                'effort': 'medium',
                'description': 'Optimize slow functions to improve overall performance'
            })
        
        # Frequently called functions
        frequent_functions = [f for f in function_profiles if f.call_count > 1000]
        if frequent_functions:
            opportunities.append({
                'type': 'frequent_functions',
                'count': len(frequent_functions),
                'functions': [{
                    'name': f.name,
                    'call_count': f.call_count,
                    'total_time': f.total_time,
                    'average_time': f.average_time
                } for f in frequent_functions[:5]],
                'impact': 'medium',
                'effort': 'low',
                'description': 'Cache results or optimize frequently called functions'
            })
        
        # Long-running async tasks
        long_async = [t for t in async_profiles if t.duration and t.duration > 5.0]  # > 5 seconds
        if long_async:
            opportunities.append({
                'type': 'long_async_tasks',
                'count': len(long_async),
                'tasks': [{
                    'name': t.name,
                    'duration': t.duration,
                    'status': t.status
                } for t in long_async[:5]],
                'impact': 'high',
                'effort': 'high',
                'description': 'Break down long-running async tasks or add progress tracking'
            })
        
        # Memory optimization opportunities
        memory_bottlenecks = [b for b in bottlenecks if 'memory' in b.get('type', '')]
        if memory_bottlenecks:
            opportunities.append({
                'type': 'memory_optimization',
                'bottlenecks': memory_bottlenecks,
                'impact': 'high',
                'effort': 'medium',
                'description': 'Implement memory optimization strategies'
            })
        
        return opportunities
    
    def save_report(self, report: PerformanceReport, output_file: str):
        """Save performance report to file."""
        output_path = Path(output_file)
        
        # Convert report to dictionary for JSON serialization
        report_dict = asdict(report)
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        print(f"💾 Performance report saved to: {output_path}")
    
    def print_summary(self, report: PerformanceReport):
        """Print performance analysis summary."""
        print("\n" + "=" * 60)
        print("⚡ PERFORMANCE ANALYSIS SUMMARY")
        print("=" * 60)
        
        metrics = report.overall_metrics
        
        print(f"\n📊 Overall Metrics:")
        print(f"   ⏱️ Duration: {metrics.duration:.2f}s")
        print(f"   🧠 Memory Peak: {metrics.memory_peak_mb:.1f}MB")
        print(f"   ⚡ CPU Usage: {metrics.cpu_percent:.1f}%")
        print(f"   📁 I/O Read: {metrics.io_read_bytes / 1024 / 1024:.1f}MB")
        print(f"   📁 I/O Write: {metrics.io_write_bytes / 1024 / 1024:.1f}MB")
        print(f"   🔧 Function Calls: {metrics.function_calls}")
        print(f"   🔄 Async Tasks: {metrics.async_tasks}")
        
        # Top slow functions
        if report.function_profiles:
            print(f"\n🐌 Slowest Functions:")
            slow_funcs = sorted(report.function_profiles, key=lambda f: f.total_time, reverse=True)[:5]
            for i, func in enumerate(slow_funcs, 1):
                print(f"   {i}. {func.name}: {func.total_time:.3f}s ({func.call_count} calls)")
        
        # Bottlenecks
        if report.bottlenecks:
            print(f"\n🎯 Performance Bottlenecks:")
            for i, bottleneck in enumerate(report.bottlenecks[:5], 1):
                severity = bottleneck.get('severity', 'unknown')
                severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(severity, '⚪')
                print(f"   {i}. {severity_emoji} {bottleneck.get('type', 'Unknown')}: {bottleneck.get('recommendation', 'No recommendation')}")
        
        # Top recommendations
        if report.recommendations:
            print(f"\n💡 Top Recommendations:")
            for i, rec in enumerate(report.recommendations[:5], 1):
                print(f"   {i}. {rec}")
        
        # Optimization opportunities
        if report.optimization_opportunities:
            print(f"\n🚀 Optimization Opportunities:")
            for i, opp in enumerate(report.optimization_opportunities[:3], 1):
                impact = opp.get('impact', 'unknown')
                effort = opp.get('effort', 'unknown')
                impact_emoji = {'high': '🔥', 'medium': '⚡', 'low': '💡'}.get(impact, '⚪')
                print(f"   {i}. {impact_emoji} {opp.get('description', 'Unknown')} (Impact: {impact}, Effort: {effort})")
        
        print("\n" + "=" * 60)


def profile_decorator(profiler: PerformanceProfiler):
    """Decorator to profile function calls."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return profiler.profile_function(func, *args, **kwargs)
        return wrapper
    return decorator


def async_profile_decorator(profiler: PerformanceProfiler):
    """Decorator to profile async function calls."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            coro = func(*args, **kwargs)
            return await profiler.profile_async_function(coro)
        return wrapper
    return decorator


def main():
    """Main entry point for performance profiler."""
    parser = argparse.ArgumentParser(
        description="Advanced performance profiling tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python performance_profiler.py --duration 30        # Profile for 30 seconds
  python performance_profiler.py --output perf.json  # Save report to file
  python performance_profiler.py --function main     # Profile specific function
        """
    )
    
    parser.add_argument(
        'project_path',
        nargs='?',
        default='.',
        help='Path to project directory (default: current directory)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        default=10.0,
        help='Profiling duration in seconds (default: 10)'
    )
    
    parser.add_argument(
        '--output',
        help='Output file for performance report (JSON format)'
    )
    
    parser.add_argument(
        '--function',
        help='Specific function to profile (module.function format)'
    )
    
    parser.add_argument(
        '--memory-only',
        action='store_true',
        help='Only perform memory profiling'
    )
    
    parser.add_argument(
        '--cpu-only',
        action='store_true',
        help='Only perform CPU profiling'
    )
    
    args = parser.parse_args()
    
    try:
        profiler = PerformanceProfiler(args.project_path)
        
        if args.function:
            # Profile specific function
            module_name, func_name = args.function.rsplit('.', 1)
            module = __import__(module_name, fromlist=[func_name])
            func = getattr(module, func_name)
            
            print(f"🎯 Profiling function: {args.function}")
            with profiler.profile_context(f"function_{func_name}"):
                result = func()
                print(f"✅ Function completed with result: {result}")
        else:
            # General profiling
            print(f"🔍 Starting {args.duration}s performance profiling session...")
            profiler.start_profiling("general_profiling")
            
            # Simulate some work or wait for user code
            time.sleep(args.duration)
            
            profiler.stop_profiling()
        
        # Generate and display report
        report = profiler.generate_report()
        profiler.print_summary(report)
        
        # Save report if requested
        if args.output:
            profiler.save_report(report, args.output)
        
    except Exception as e:
        print(f"❌ Performance profiling failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()