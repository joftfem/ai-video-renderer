#!/usr/bin/env python3
"""
Analytics & Memory System Integration

Integrates analytics collection and memory system with the existing render pipeline.
Provides automatic logging, performance tracking, and data correlation.

Author: AI Video Renderer System
Version: 1.0.0
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import uuid

# Import our systems
try:
    from .memory_system import get_memory_system, log_event as memory_log_event
except ImportError:
    from memory_system import get_memory_system, log_event as memory_log_event

try:
    from ..analytics.collect_metrics import YouTubeAnalyticsCollector, VideoMetrics
except ImportError:
    from analytics.collect_metrics import YouTubeAnalyticsCollector, VideoMetrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsIntegration:
    """Integration layer for analytics and memory systems"""
    
    def __init__(self):
        self.analytics_collector = YouTubeAnalyticsCollector()
        self.memory_system = get_memory_system()
        self.session_id = str(uuid.uuid4())
        
        # Configuration
        self.auto_collect_enabled = os.getenv('AUTO_ANALYTICS_ENABLED', 'true').lower() == 'true'
        self.memory_logging_enabled = os.getenv('MEMORY_LOGGING_ENABLED', 'true').lower() == 'true'
        
        # Tracking state
        self.current_render_session = {}
        self.performance_cache = {}
        
        logger.info(f"Analytics integration initialized (session: {self.session_id})")
    
    async def start_render_session(self, render_config: Dict[str, Any]) -> str:
        """Start a new render session and begin tracking"""
        try:
            session_id = str(uuid.uuid4())
            
            self.current_render_session = {
                'session_id': session_id,
                'start_time': datetime.utcnow(),
                'config': render_config,
                'niche': render_config.get('niche', 'unknown'),
                'title': render_config.get('title', ''),
                'stages': {},
                'costs': {},
                'performance_metrics': {}
            }
            
            # Log session start to memory system
            if self.memory_logging_enabled:
                await memory_log_event({
                    'event_type': 'render_session_start',
                    'session_id': session_id,
                    'niche': self.current_render_session['niche'],
                    'title': self.current_render_session['title'],
                    'timestamp': self.current_render_session['start_time'],
                    'metadata': {'config': render_config}
                })
            
            logger.info(f"Started render session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting render session: {e}")
            return str(uuid.uuid4())  # Fallback
    
    async def log_tts_usage(self, engine: str, text: str, cost: float, duration: float, 
                           quality_score: Optional[float] = None, audio_file: Optional[str] = None):
        """Log TTS engine usage and performance"""
        try:
            event_data = {
                'event_type': 'tts_usage',
                'session_id': self.current_render_session.get('session_id'),
                'tts_engine': engine,
                'tts_cost': cost,
                'tts_duration': duration,
                'tts_quality_score': quality_score,
                'text_length': len(text),
                'niche': self.current_render_session.get('niche'),
                'timestamp': datetime.utcnow(),
                'metadata': {
                    'audio_file': audio_file,
                    'text_preview': text[:100] + '...' if len(text) > 100 else text
                }
            }
            
            # Update session tracking
            if 'tts' not in self.current_render_session['stages']:
                self.current_render_session['stages']['tts'] = []
            self.current_render_session['stages']['tts'].append(event_data)
            
            # Update costs
            if 'tts' not in self.current_render_session['costs']:
                self.current_render_session['costs']['tts'] = 0
            self.current_render_session['costs']['tts'] += cost
            
            # Log to memory system
            if self.memory_logging_enabled:
                await memory_log_event(event_data)
            
            logger.info(f"Logged TTS usage: {engine} (${cost:.4f}, {duration:.2f}s)")
            
        except Exception as e:
            logger.error(f"Error logging TTS usage: {e}")
    
    async def log_thumbnail_generation(self, source: str, variant: str, score: float, 
                                     cost: float = 0.0, generation_time: float = 0.0,
                                     thumbnail_path: Optional[str] = None):
        """Log thumbnail generation and scoring"""
        try:
            event_data = {
                'event_type': 'thumbnail_generation',
                'session_id': self.current_render_session.get('session_id'),
                'thumbnail_source': source,
                'thumbnail_variant': variant,
                'thumbnail_score': score,
                'generation_cost': cost,
                'generation_time': generation_time,
                'niche': self.current_render_session.get('niche'),
                'timestamp': datetime.utcnow(),
                'metadata': {
                    'thumbnail_path': thumbnail_path,
                    'title': self.current_render_session.get('title')
                }
            }
            
            # Update session tracking
            if 'thumbnail' not in self.current_render_session['stages']:
                self.current_render_session['stages']['thumbnail'] = []
            self.current_render_session['stages']['thumbnail'].append(event_data)
            
            # Update costs
            if 'thumbnail' not in self.current_render_session['costs']:
                self.current_render_session['costs']['thumbnail'] = 0
            self.current_render_session['costs']['thumbnail'] += cost
            
            # Log to memory system
            if self.memory_logging_enabled:
                await memory_log_event(event_data)
            
            logger.info(f"Logged thumbnail generation: {source}/{variant} (score: {score:.3f})")
            
        except Exception as e:
            logger.error(f"Error logging thumbnail generation: {e}")
    
    async def log_content_moderation(self, moderation_score: float, content_safety: str,
                                   moderation_details: Optional[Dict] = None):
        """Log content moderation results"""
        try:
            event_data = {
                'event_type': 'content_moderation',
                'session_id': self.current_render_session.get('session_id'),
                'moderation_score': moderation_score,
                'content_safety': content_safety,
                'niche': self.current_render_session.get('niche'),
                'timestamp': datetime.utcnow(),
                'metadata': {
                    'moderation_details': moderation_details or {},
                    'title': self.current_render_session.get('title')
                }
            }
            
            # Update session tracking
            self.current_render_session['performance_metrics']['moderation_score'] = moderation_score
            self.current_render_session['performance_metrics']['content_safety'] = content_safety
            
            # Log to memory system
            if self.memory_logging_enabled:
                await memory_log_event(event_data)
            
            logger.info(f"Logged content moderation: {content_safety} (score: {moderation_score:.3f})")
            
        except Exception as e:
            logger.error(f"Error logging content moderation: {e}")
    
    async def log_video_upload(self, video_id: str, upload_id: str, upload_success: bool,
                             upload_time: float, file_size: int):
        """Log video upload completion"""
        try:
            event_data = {
                'event_type': 'video_upload',
                'session_id': self.current_render_session.get('session_id'),
                'video_id': video_id,
                'upload_id': upload_id,
                'title': self.current_render_session.get('title'),
                'niche': self.current_render_session.get('niche'),
                'upload_success': upload_success,
                'upload_time': upload_time,
                'file_size': file_size,
                'timestamp': datetime.utcnow(),
                'metadata': {
                    'total_cost': sum(self.current_render_session.get('costs', {}).values()),
                    'stages_completed': list(self.current_render_session.get('stages', {}).keys()),
                    'session_duration': (datetime.utcnow() - self.current_render_session.get('start_time', datetime.utcnow())).total_seconds()
                }
            }
            
            # Add performance metrics
            event_data.update(self.current_render_session.get('performance_metrics', {}))
            
            # Log to memory system
            if self.memory_logging_enabled:
                await memory_log_event(event_data)
            
            # Schedule analytics collection if auto-collect is enabled
            if self.auto_collect_enabled and upload_success and video_id:
                asyncio.create_task(self._schedule_analytics_collection(video_id, upload_id))
            
            logger.info(f"Logged video upload: {video_id} (success: {upload_success})")
            
        except Exception as e:
            logger.error(f"Error logging video upload: {e}")
    
    async def _schedule_analytics_collection(self, video_id: str, upload_id: str):
        """Schedule analytics collection for a newly uploaded video"""
        try:
            # Wait for initial processing (YouTube needs time to process)
            await asyncio.sleep(300)  # 5 minutes
            
            # Collect initial metrics
            await self.collect_video_analytics(video_id, upload_id)
            
            # Schedule follow-up collections
            collection_intervals = [3600, 7200, 21600, 86400]  # 1h, 2h, 6h, 24h
            
            for interval in collection_intervals:
                await asyncio.sleep(interval)
                await self.collect_video_analytics(video_id, upload_id)
            
        except Exception as e:
            logger.error(f"Error in scheduled analytics collection: {e}")
    
    async def collect_video_analytics(self, video_id: str, upload_id: str) -> Optional[VideoMetrics]:
        """Collect analytics for a specific video"""
        try:
            # Collect metrics using analytics collector
            metrics = await self.analytics_collector.collect_video_metrics(video_id, upload_id)
            
            if metrics:
                # Log metrics
                await self.analytics_collector.log_metrics(metrics)
                
                # Calculate success score
                success_score = self._calculate_success_score(metrics)
                
                # Log engagement event to memory system
                if self.memory_logging_enabled:
                    await memory_log_event({
                        'event_type': 'engagement_update',
                        'video_id': video_id,
                        'upload_id': upload_id,
                        'title': metrics.title,
                        'niche': metrics.niche,
                        'views': metrics.views,
                        'likes': metrics.likes,
                        'comments': metrics.comments,
                        'ctr': metrics.ctr,
                        'engagement_rate': metrics.engagement_rate,
                        'success_score': success_score,
                        'timestamp': datetime.utcnow(),
                        'metadata': {
                            'collection_type': 'scheduled',
                            'thumbnail_variant': metrics.thumbnail_variant,
                            'thumbnail_source': metrics.thumbnail_source,
                            'tts_engine': metrics.tts_engine
                        }
                    })
                
                logger.info(f"Collected analytics for video {video_id}: {metrics.views} views, {metrics.engagement_rate:.2f}% engagement")
                return metrics
            
        except Exception as e:
            logger.error(f"Error collecting video analytics: {e}")
        
        return None
    
    def _calculate_success_score(self, metrics: VideoMetrics) -> float:
        """Calculate a normalized success score (0-1) based on multiple factors"""
        try:
            score = 0.0
            
            # Views component (30%)
            if metrics.views > 0:
                # Normalize views (log scale, max at 100k views = 1.0)
                import math
                views_score = min(math.log10(metrics.views + 1) / 5.0, 1.0)
                score += views_score * 0.3
            
            # Engagement rate component (25%)
            if metrics.engagement_rate > 0:
                # Normalize engagement rate (max at 10% = 1.0)
                engagement_score = min(metrics.engagement_rate / 10.0, 1.0)
                score += engagement_score * 0.25
            
            # CTR component (20%)
            if metrics.ctr > 0:
                # Normalize CTR (max at 15% = 1.0)
                ctr_score = min(metrics.ctr / 15.0, 1.0)
                score += ctr_score * 0.2
            
            # Average view duration component (15%)
            if metrics.avg_view_duration > 0:
                # Normalize AVD (assume 5 minutes = 1.0)
                avd_score = min(metrics.avg_view_duration / 300.0, 1.0)
                score += avd_score * 0.15
            
            # Thumbnail score component (10%)
            if metrics.thumbnail_score > 0:
                score += metrics.thumbnail_score * 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating success score: {e}")
            return 0.0
    
    async def get_performance_recommendations(self, niche: Optional[str] = None, 
                                            days: int = 30) -> Dict[str, Any]:
        """Get AI-powered performance recommendations based on historical data"""
        try:
            # Get performance insights from memory system
            insights = await self.memory_system.get_performance_insights(niche=niche, days=days)
            
            recommendations = {
                'niche': niche or 'all',
                'analysis_period': f"{days} days",
                'recommendations': [],
                'insights': insights,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Analyze TTS performance
            tts_usage = insights.get('tts_usage', {})
            if tts_usage:
                best_tts = max(tts_usage.items(), key=lambda x: x[1].get('avg_quality', 0))
                cheapest_tts = min(tts_usage.items(), key=lambda x: x[1].get('avg_cost', float('inf')))
                
                recommendations['recommendations'].append({
                    'type': 'tts_optimization',
                    'priority': 'high',
                    'message': f"Best quality TTS: {best_tts[0]} (quality: {best_tts[1].get('avg_quality', 0):.2f})",
                    'action': f"Consider using {best_tts[0]} for high-priority content"
                })
                
                if cheapest_tts[0] != best_tts[0]:
                    recommendations['recommendations'].append({
                        'type': 'cost_optimization',
                        'priority': 'medium',
                        'message': f"Most cost-effective TTS: {cheapest_tts[0]} (${cheapest_tts[1].get('avg_cost', 0):.4f} avg)",
                        'action': f"Use {cheapest_tts[0]} for bulk content generation"
                    })
            
            # Analyze thumbnail performance
            thumbnail_perf = insights.get('thumbnail_performance', {})
            if thumbnail_perf:
                best_thumbnail = max(thumbnail_perf.items(), key=lambda x: x[1].get('success_rate', 0))
                
                recommendations['recommendations'].append({
                    'type': 'thumbnail_optimization',
                    'priority': 'high',
                    'message': f"Best performing thumbnail source: {best_thumbnail[0]} ({best_thumbnail[1].get('success_rate', 0):.1f}% success rate)",
                    'action': f"Prioritize {best_thumbnail[0]} for thumbnail generation"
                })
            
            # General recommendations based on data volume
            total_events = insights.get('total_events', 0)
            if total_events < 10:
                recommendations['recommendations'].append({
                    'type': 'data_collection',
                    'priority': 'low',
                    'message': f"Limited data available ({total_events} events in {days} days)",
                    'action': "Continue content creation to gather more performance data"
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating performance recommendations: {e}")
            return {'error': str(e), 'recommendations': []}
    
    async def generate_cost_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate detailed cost analysis report"""
        try:
            # Query cost-related events from memory system
            filters = {
                'start_date': datetime.utcnow() - timedelta(days=days),
                'end_date': datetime.utcnow(),
                'limit': 1000
            }
            
            events = await self.memory_system.query_history(filters)
            
            cost_report = {
                'period_days': days,
                'total_costs': {
                    'tts': 0.0,
                    'thumbnail': 0.0,
                    'vertex_ai': 0.0,
                    'total': 0.0
                },
                'cost_per_video': 0.0,
                'cost_breakdown': {},
                'efficiency_metrics': {},
                'generated_at': datetime.utcnow().isoformat()
            }
            
            video_count = 0
            tts_costs = {}
            thumbnail_costs = {}
            
            for event in events:
                event_type = event.get('event_type')
                
                if event_type == 'tts_usage':
                    cost = event.get('tts_cost', 0)
                    engine = event.get('tts_engine', 'unknown')
                    
                    cost_report['total_costs']['tts'] += cost
                    
                    if engine not in tts_costs:
                        tts_costs[engine] = {'total': 0, 'count': 0}
                    tts_costs[engine]['total'] += cost
                    tts_costs[engine]['count'] += 1
                
                elif event_type == 'thumbnail_generation':
                    cost = event.get('generation_cost', 0)
                    source = event.get('thumbnail_source', 'unknown')
                    
                    cost_report['total_costs']['thumbnail'] += cost
                    
                    if source not in thumbnail_costs:
                        thumbnail_costs[source] = {'total': 0, 'count': 0}
                    thumbnail_costs[source]['total'] += cost
                    thumbnail_costs[source]['count'] += 1
                
                elif event_type == 'video_upload':
                    video_count += 1
            
            # Calculate totals and averages
            cost_report['total_costs']['total'] = (
                cost_report['total_costs']['tts'] + 
                cost_report['total_costs']['thumbnail'] + 
                cost_report['total_costs']['vertex_ai']
            )
            
            if video_count > 0:
                cost_report['cost_per_video'] = cost_report['total_costs']['total'] / video_count
            
            # Add detailed breakdowns
            cost_report['cost_breakdown']['tts_engines'] = {
                engine: {
                    'total_cost': data['total'],
                    'avg_cost': data['total'] / data['count'] if data['count'] > 0 else 0,
                    'usage_count': data['count']
                }
                for engine, data in tts_costs.items()
            }
            
            cost_report['cost_breakdown']['thumbnail_sources'] = {
                source: {
                    'total_cost': data['total'],
                    'avg_cost': data['total'] / data['count'] if data['count'] > 0 else 0,
                    'usage_count': data['count']
                }
                for source, data in thumbnail_costs.items()
            }
            
            # Calculate efficiency metrics
            cost_report['efficiency_metrics'] = {
                'videos_per_day': video_count / days if days > 0 else 0,
                'avg_daily_cost': cost_report['total_costs']['total'] / days if days > 0 else 0,
                'cost_efficiency_score': self._calculate_cost_efficiency(cost_report, video_count)
            }
            
            return cost_report
            
        except Exception as e:
            logger.error(f"Error generating cost report: {e}")
            return {'error': str(e)}
    
    def _calculate_cost_efficiency(self, cost_report: Dict, video_count: int) -> float:
        """Calculate cost efficiency score (0-1, higher is better)"""
        try:
            if video_count == 0:
                return 0.0
            
            cost_per_video = cost_report['cost_per_video']
            
            # Efficiency score based on cost per video
            # Assume $0.50 per video is excellent (score = 1.0)
            # $2.00 per video is poor (score = 0.0)
            if cost_per_video <= 0.5:
                return 1.0
            elif cost_per_video >= 2.0:
                return 0.0
            else:
                return 1.0 - ((cost_per_video - 0.5) / 1.5)
            
        except Exception as e:
            logger.error(f"Error calculating cost efficiency: {e}")
            return 0.0

# Global instance
_analytics_integration = None

def get_analytics_integration() -> AnalyticsIntegration:
    """Get global analytics integration instance"""
    global _analytics_integration
    if _analytics_integration is None:
        _analytics_integration = AnalyticsIntegration()
    return _analytics_integration

# Convenience functions for easy integration
async def start_render_session(render_config: Dict[str, Any]) -> str:
    """Start a new render session"""
    integration = get_analytics_integration()
    return await integration.start_render_session(render_config)

async def log_tts_usage(engine: str, text: str, cost: float, duration: float, 
                       quality_score: Optional[float] = None, audio_file: Optional[str] = None):
    """Log TTS usage"""
    integration = get_analytics_integration()
    await integration.log_tts_usage(engine, text, cost, duration, quality_score, audio_file)

async def log_thumbnail_generation(source: str, variant: str, score: float, 
                                 cost: float = 0.0, generation_time: float = 0.0,
                                 thumbnail_path: Optional[str] = None):
    """Log thumbnail generation"""
    integration = get_analytics_integration()
    await integration.log_thumbnail_generation(source, variant, score, cost, generation_time, thumbnail_path)

async def log_content_moderation(moderation_score: float, content_safety: str,
                               moderation_details: Optional[Dict] = None):
    """Log content moderation"""
    integration = get_analytics_integration()
    await integration.log_content_moderation(moderation_score, content_safety, moderation_details)

async def log_video_upload(video_id: str, upload_id: str, upload_success: bool,
                         upload_time: float, file_size: int):
    """Log video upload"""
    integration = get_analytics_integration()
    await integration.log_video_upload(video_id, upload_id, upload_success, upload_time, file_size)

# CLI for testing and reports
async def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analytics Integration CLI')
    parser.add_argument('--recommendations', type=str, help='Get recommendations for niche')
    parser.add_argument('--cost-report', type=int, default=30, help='Generate cost report for N days')
    parser.add_argument('--collect', type=str, help='Collect analytics for video_id:upload_id')
    
    args = parser.parse_args()
    
    integration = get_analytics_integration()
    
    if args.recommendations:
        recommendations = await integration.get_performance_recommendations(niche=args.recommendations)
        print(json.dumps(recommendations, indent=2, default=str))
    
    elif args.cost_report:
        cost_report = await integration.generate_cost_report(days=args.cost_report)
        print(json.dumps(cost_report, indent=2, default=str))
    
    elif args.collect:
        try:
            video_id, upload_id = args.collect.split(':')
            metrics = await integration.collect_video_analytics(video_id, upload_id)
            if metrics:
                print(f"Collected metrics for {video_id}: {metrics.views} views")
            else:
                print(f"Failed to collect metrics for {video_id}")
        except ValueError:
            print("Invalid format. Use: video_id:upload_id")

if __name__ == "__main__":
    asyncio.run(main())