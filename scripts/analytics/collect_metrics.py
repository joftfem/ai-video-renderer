#!/usr/bin/env python3
"""
YouTube Analytics & Performance Metrics Collection System

Tracks video performance, thumbnail variants, TTS usage, and engagement metrics.
Logs to BigQuery, local files, and optionally syncs to Google Sheets.

Author: AI Video Renderer System
Version: 1.0.0
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# Google Cloud & Analytics
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Utilities
import pandas as pd
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VideoMetrics:
    """Video performance metrics data structure"""
    video_id: str
    upload_id: str
    title: str
    description: str
    tags: List[str]
    niche: str
    upload_date: datetime
    
    # YouTube Performance
    views: int = 0
    impressions: int = 0
    ctr: float = 0.0
    avg_view_duration: float = 0.0
    watch_time_minutes: float = 0.0
    
    # Engagement
    likes: int = 0
    comments: int = 0
    shares: int = 0
    subscribers_gained: int = 0
    engagement_rate: float = 0.0
    
    # Thumbnail Analytics
    thumbnail_variant: str = "default"
    thumbnail_source: str = "unknown"  # huggingface, vertex_ai, ffmpeg
    thumbnail_score: float = 0.0
    
    # TTS Analytics
    tts_engine: str = "unknown"
    tts_cost: float = 0.0
    tts_duration: float = 0.0
    
    # Moderation
    moderation_score: float = 0.0
    content_safety: str = "unknown"
    
    # Metadata
    collected_at: datetime = None
    
    def __post_init__(self):
        if self.collected_at is None:
            self.collected_at = datetime.utcnow()

class YouTubeAnalyticsCollector:
    """Comprehensive YouTube analytics and metrics collection system"""
    
    def __init__(self):
        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.dataset_id = 'ai_renderer'
        self.table_id = 'analytics'
        
        # Initialize clients
        self.bq_client = bigquery.Client(project=self.project_id)
        self.youtube_service = None
        self.sheets_client = None
        
        # Paths
        self.log_dir = Path('/Users/joft/Downloads/Muliti Niche automation/ai-video-renderer/logs')
        self.log_dir.mkdir(exist_ok=True)
        self.analytics_log = self.log_dir / 'analytics.log'
        
        # Configuration
        self.sheets_enabled = os.getenv('GOOGLE_SHEETS_SYNC', 'false').lower() == 'true'
        self.spreadsheet_id = os.getenv('ANALYTICS_SPREADSHEET_ID')
        
        self._setup_bigquery_table()
        self._setup_youtube_api()
        if self.sheets_enabled:
            self._setup_sheets_client()
    
    def _setup_bigquery_table(self):
        """Create BigQuery table if it doesn't exist"""
        try:
            table_ref = self.bq_client.dataset(self.dataset_id).table(self.table_id)
            
            # Check if table exists
            try:
                self.bq_client.get_table(table_ref)
                logger.info(f"BigQuery table {self.dataset_id}.{self.table_id} already exists")
                return
            except NotFound:
                pass
            
            # Create table schema
            schema = [
                bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("upload_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("title", "STRING"),
                bigquery.SchemaField("description", "STRING"),
                bigquery.SchemaField("tags", "STRING", mode="REPEATED"),
                bigquery.SchemaField("niche", "STRING"),
                bigquery.SchemaField("upload_date", "TIMESTAMP"),
                
                # Performance metrics
                bigquery.SchemaField("views", "INTEGER"),
                bigquery.SchemaField("impressions", "INTEGER"),
                bigquery.SchemaField("ctr", "FLOAT"),
                bigquery.SchemaField("avg_view_duration", "FLOAT"),
                bigquery.SchemaField("watch_time_minutes", "FLOAT"),
                
                # Engagement
                bigquery.SchemaField("likes", "INTEGER"),
                bigquery.SchemaField("comments", "INTEGER"),
                bigquery.SchemaField("shares", "INTEGER"),
                bigquery.SchemaField("subscribers_gained", "INTEGER"),
                bigquery.SchemaField("engagement_rate", "FLOAT"),
                
                # Thumbnail & TTS
                bigquery.SchemaField("thumbnail_variant", "STRING"),
                bigquery.SchemaField("thumbnail_source", "STRING"),
                bigquery.SchemaField("thumbnail_score", "FLOAT"),
                bigquery.SchemaField("tts_engine", "STRING"),
                bigquery.SchemaField("tts_cost", "FLOAT"),
                bigquery.SchemaField("tts_duration", "FLOAT"),
                
                # Moderation
                bigquery.SchemaField("moderation_score", "FLOAT"),
                bigquery.SchemaField("content_safety", "STRING"),
                
                # Metadata
                bigquery.SchemaField("collected_at", "TIMESTAMP"),
            ]
            
            # Create partitioned table
            table = bigquery.Table(table_ref, schema=schema)
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="collected_at"
            )
            
            table = self.bq_client.create_table(table)
            logger.info(f"Created BigQuery table {table.project}.{table.dataset_id}.{table.table_id}")
            
        except Exception as e:
            logger.error(f"Error setting up BigQuery table: {e}")
    
    def _setup_youtube_api(self):
        """Initialize YouTube Data API client"""
        try:
            api_key = os.getenv('YOUTUBE_API_KEY')
            if api_key:
                self.youtube_service = build('youtube', 'v3', developerKey=api_key)
                logger.info("YouTube Data API client initialized")
            else:
                logger.warning("YouTube API key not found")
        except Exception as e:
            logger.error(f"Error setting up YouTube API: {e}")
    
    def _setup_sheets_client(self):
        """Initialize Google Sheets client"""
        try:
            credentials_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                scope = ['https://spreadsheets.google.com/feeds',
                        'https://www.googleapis.com/auth/drive']
                creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
                self.sheets_client = gspread.authorize(creds)
                logger.info("Google Sheets client initialized")
            else:
                logger.warning("Google Sheets credentials not found")
        except Exception as e:
            logger.error(f"Error setting up Google Sheets: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def collect_video_metrics(self, video_id: str, upload_id: str) -> Optional[VideoMetrics]:
        """Collect comprehensive metrics for a video"""
        try:
            # Get video details from YouTube API
            video_info = await self._get_video_info(video_id)
            if not video_info:
                return None
            
            # Get analytics data (requires YouTube Analytics API)
            analytics_data = await self._get_analytics_data(video_id)
            
            # Load additional metadata from logs
            metadata = await self._load_video_metadata(upload_id)
            
            # Create metrics object
            metrics = VideoMetrics(
                video_id=video_id,
                upload_id=upload_id,
                title=video_info.get('title', ''),
                description=video_info.get('description', ''),
                tags=video_info.get('tags', []),
                niche=metadata.get('niche', 'unknown'),
                upload_date=datetime.fromisoformat(video_info.get('publishedAt', '').replace('Z', '+00:00')),
                
                # YouTube metrics
                views=int(video_info.get('viewCount', 0)),
                likes=int(video_info.get('likeCount', 0)),
                comments=int(video_info.get('commentCount', 0)),
                
                # Analytics data
                impressions=analytics_data.get('impressions', 0),
                ctr=analytics_data.get('ctr', 0.0),
                avg_view_duration=analytics_data.get('avgViewDuration', 0.0),
                watch_time_minutes=analytics_data.get('watchTimeMinutes', 0.0),
                
                # Metadata
                thumbnail_variant=metadata.get('thumbnail_variant', 'default'),
                thumbnail_source=metadata.get('thumbnail_source', 'unknown'),
                thumbnail_score=metadata.get('thumbnail_score', 0.0),
                tts_engine=metadata.get('tts_engine', 'unknown'),
                tts_cost=metadata.get('tts_cost', 0.0),
                tts_duration=metadata.get('tts_duration', 0.0),
                moderation_score=metadata.get('moderation_score', 0.0),
                content_safety=metadata.get('content_safety', 'unknown')
            )
            
            # Calculate derived metrics
            if metrics.views > 0:
                metrics.engagement_rate = (metrics.likes + metrics.comments) / metrics.views * 100
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics for video {video_id}: {e}")
            return None
    
    async def _get_video_info(self, video_id: str) -> Optional[Dict]:
        """Get video information from YouTube Data API"""
        if not self.youtube_service:
            return None
        
        try:
            request = self.youtube_service.videos().list(
                part='snippet,statistics',
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                item = response['items'][0]
                return {
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'tags': item['snippet'].get('tags', []),
                    'publishedAt': item['snippet']['publishedAt'],
                    'viewCount': item['statistics'].get('viewCount', 0),
                    'likeCount': item['statistics'].get('likeCount', 0),
                    'commentCount': item['statistics'].get('commentCount', 0)
                }
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
        
        return None
    
    async def _get_analytics_data(self, video_id: str) -> Dict:
        """Get analytics data (placeholder for YouTube Analytics API)"""
        # Note: YouTube Analytics API requires additional setup and OAuth
        # This is a placeholder that returns mock data
        return {
            'impressions': 0,
            'ctr': 0.0,
            'avgViewDuration': 0.0,
            'watchTimeMinutes': 0.0
        }
    
    async def _load_video_metadata(self, upload_id: str) -> Dict:
        """Load video metadata from logs or database"""
        try:
            # Try to load from analytics log first
            if self.analytics_log.exists():
                with open(self.analytics_log, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if data.get('upload_id') == upload_id:
                                return data
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Error loading metadata for {upload_id}: {e}")
        
        return {}
    
    async def log_metrics(self, metrics: VideoMetrics):
        """Log metrics to all configured destinations"""
        # Log to BigQuery
        await self._log_to_bigquery(metrics)
        
        # Log to file
        await self._log_to_file(metrics)
        
        # Sync to Google Sheets if enabled
        if self.sheets_enabled:
            await self._sync_to_sheets(metrics)
    
    async def _log_to_bigquery(self, metrics: VideoMetrics):
        """Log metrics to BigQuery"""
        try:
            table_ref = self.bq_client.dataset(self.dataset_id).table(self.table_id)
            
            # Convert metrics to BigQuery format
            row_data = asdict(metrics)
            
            # Convert datetime objects to strings
            for key, value in row_data.items():
                if isinstance(value, datetime):
                    row_data[key] = value.isoformat()
            
            # Insert row
            errors = self.bq_client.insert_rows_json(table_ref, [row_data])
            
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
            else:
                logger.info(f"Logged metrics for video {metrics.video_id} to BigQuery")
                
        except Exception as e:
            logger.error(f"Error logging to BigQuery: {e}")
    
    async def _log_to_file(self, metrics: VideoMetrics):
        """Log metrics to local file"""
        try:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'video_metrics',
                **asdict(metrics)
            }
            
            # Convert datetime objects to strings
            for key, value in log_entry.items():
                if isinstance(value, datetime):
                    log_entry[key] = value.isoformat()
            
            with open(self.analytics_log, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.info(f"Logged metrics for video {metrics.video_id} to file")
            
        except Exception as e:
            logger.error(f"Error logging to file: {e}")
    
    async def _sync_to_sheets(self, metrics: VideoMetrics):
        """Sync metrics to Google Sheets"""
        if not self.sheets_client or not self.spreadsheet_id:
            return
        
        try:
            spreadsheet = self.sheets_client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet('Analytics')
            
            # Prepare row data
            row_data = [
                metrics.video_id,
                metrics.title,
                metrics.niche,
                metrics.views,
                metrics.impressions,
                metrics.ctr,
                metrics.avg_view_duration,
                metrics.likes,
                metrics.comments,
                metrics.engagement_rate,
                metrics.thumbnail_source,
                metrics.thumbnail_score,
                metrics.tts_engine,
                metrics.tts_cost,
                metrics.collected_at.isoformat()
            ]
            
            worksheet.append_row(row_data)
            logger.info(f"Synced metrics for video {metrics.video_id} to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error syncing to Google Sheets: {e}")
    
    async def generate_performance_report(self, days: int = 30) -> Dict:
        """Generate performance report for the last N days"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            query = f"""
            SELECT 
                niche,
                COUNT(*) as video_count,
                AVG(views) as avg_views,
                AVG(ctr) as avg_ctr,
                AVG(engagement_rate) as avg_engagement,
                AVG(thumbnail_score) as avg_thumbnail_score,
                SUM(tts_cost) as total_tts_cost,
                thumbnail_source,
                tts_engine
            FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
            WHERE collected_at >= '{start_date.isoformat()}'
            AND collected_at <= '{end_date.isoformat()}'
            GROUP BY niche, thumbnail_source, tts_engine
            ORDER BY avg_views DESC
            """
            
            query_job = self.bq_client.query(query)
            results = query_job.result()
            
            report_data = []
            for row in results:
                report_data.append(dict(row))
            
            return {
                'period': f"{start_date.date()} to {end_date.date()}",
                'total_videos': len(report_data),
                'performance_by_niche': report_data,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {}
    
    async def collect_daily_metrics(self):
        """Collect metrics for all videos uploaded in the last 24 hours"""
        try:
            # This would typically query your video database or logs
            # For now, we'll use a placeholder implementation
            logger.info("Starting daily metrics collection...")
            
            # Get list of recent uploads
            recent_uploads = await self._get_recent_uploads()
            
            for upload_info in recent_uploads:
                video_id = upload_info.get('video_id')
                upload_id = upload_info.get('upload_id')
                
                if video_id and upload_id:
                    metrics = await self.collect_video_metrics(video_id, upload_id)
                    if metrics:
                        await self.log_metrics(metrics)
            
            logger.info(f"Completed daily metrics collection for {len(recent_uploads)} videos")
            
        except Exception as e:
            logger.error(f"Error in daily metrics collection: {e}")
    
    async def _get_recent_uploads(self) -> List[Dict]:
        """Get list of recent video uploads"""
        # Placeholder implementation
        # This should query your video database or upload logs
        return []

# CLI and Scheduler Integration
async def main():
    """Main function for CLI usage and GCP Scheduler"""
    collector = YouTubeAnalyticsCollector()
    
    # Run daily collection
    await collector.collect_daily_metrics()
    
    # Generate performance report
    report = await collector.generate_performance_report()
    if report:
        logger.info(f"Performance report generated: {report['total_videos']} videos analyzed")

if __name__ == "__main__":
    asyncio.run(main())