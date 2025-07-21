#!/usr/bin/env python3
"""
Hybrid Long-Term Memory System with Pinecone + Firestore

Tracks video history, TTS usage, moderation scores, and engagement metrics.
Provides intelligent querying and automatic TTL cleanup (45 days).

Author: AI Video Renderer System
Version: 1.0.0
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import uuid

# Pinecone for vector embeddings
import pinecone
from pinecone import Pinecone, ServerlessSpec

# Firestore for structured data
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Text embeddings
from sentence_transformers import SentenceTransformer
import numpy as np

# Utilities
from tenacity import retry, stop_after_attempt, wait_exponential
import schedule
import time
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MemoryEvent:
    """Memory event data structure"""
    event_id: str
    event_type: str  # video_upload, tts_usage, moderation, engagement
    timestamp: datetime
    
    # Video Information
    video_id: Optional[str] = None
    upload_id: Optional[str] = None
    title: Optional[str] = None
    niche: Optional[str] = None
    
    # TTS Information
    tts_engine: Optional[str] = None
    tts_cost: Optional[float] = None
    tts_duration: Optional[float] = None
    tts_quality_score: Optional[float] = None
    
    # Moderation Scores
    moderation_score: Optional[float] = None
    content_safety: Optional[str] = None
    thumbnail_score: Optional[float] = None
    thumbnail_source: Optional[str] = None
    
    # Engagement Success
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    ctr: Optional[float] = None
    engagement_rate: Optional[float] = None
    success_score: Optional[float] = None
    
    # Metadata
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))

class HybridMemorySystem:
    """Hybrid long-term memory system using Pinecone + Firestore"""
    
    def __init__(self):
        # Configuration
        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.pinecone_api_key = os.getenv('PINECONE_API_KEY')
        self.pinecone_environment = os.getenv('PINECONE_ENVIRONMENT', 'us-west1-gcp')
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'ai-video-memory')
        self.collection_name = 'video_memory'
        
        # TTL Configuration (45 days)
        self.ttl_days = int(os.getenv('MEMORY_TTL_DAYS', '45'))
        self.cleanup_enabled = os.getenv('MEMORY_CLEANUP_ENABLED', 'true').lower() == 'true'
        
        # Initialize clients
        self.firestore_client = None
        self.pinecone_client = None
        self.pinecone_index = None
        self.embedding_model = None
        
        # Setup
        self._setup_firestore()
        self._setup_pinecone()
        self._setup_embedding_model()
        
        # Start cleanup scheduler if enabled
        if self.cleanup_enabled:
            self._schedule_cleanup()
    
    def _setup_firestore(self):
        """Initialize Firestore client"""
        try:
            self.firestore_client = firestore.Client(project=self.project_id)
            logger.info("Firestore client initialized")
        except Exception as e:
            logger.error(f"Error setting up Firestore: {e}")
    
    def _setup_pinecone(self):
        """Initialize Pinecone client and index"""
        try:
            if not self.pinecone_api_key:
                logger.warning("Pinecone API key not found")
                return
            
            # Initialize Pinecone
            self.pinecone_client = Pinecone(api_key=self.pinecone_api_key)
            
            # Create index if it doesn't exist
            existing_indexes = [index.name for index in self.pinecone_client.list_indexes()]
            
            if self.index_name not in existing_indexes:
                self.pinecone_client.create_index(
                    name=self.index_name,
                    dimension=384,  # sentence-transformers/all-MiniLM-L6-v2 dimension
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='gcp',
                        region=self.pinecone_environment
                    )
                )
                logger.info(f"Created Pinecone index: {self.index_name}")
            
            # Connect to index
            self.pinecone_index = self.pinecone_client.Index(self.index_name)
            logger.info("Pinecone client initialized")
            
        except Exception as e:
            logger.error(f"Error setting up Pinecone: {e}")
    
    def _setup_embedding_model(self):
        """Initialize sentence transformer model for embeddings"""
        try:
            model_name = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Embedding model loaded: {model_name}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self.embedding_model:
            return [0.0] * 384  # Default dimension
        
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * 384
    
    def _create_searchable_text(self, event: MemoryEvent) -> str:
        """Create searchable text from event data"""
        text_parts = []
        
        if event.title:
            text_parts.append(event.title)
        if event.niche:
            text_parts.append(f"niche:{event.niche}")
        if event.tts_engine:
            text_parts.append(f"tts:{event.tts_engine}")
        if event.content_safety:
            text_parts.append(f"safety:{event.content_safety}")
        if event.thumbnail_source:
            text_parts.append(f"thumbnail:{event.thumbnail_source}")
        if event.tags:
            text_parts.extend(event.tags)
        
        return " ".join(text_parts)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def log_event(self, data: Dict[str, Any]) -> bool:
        """Log an event to the memory system"""
        try:
            # Create memory event
            event = MemoryEvent(
                event_type=data.get('event_type', 'unknown'),
                timestamp=data.get('timestamp', datetime.utcnow()),
                video_id=data.get('video_id'),
                upload_id=data.get('upload_id'),
                title=data.get('title'),
                niche=data.get('niche'),
                tts_engine=data.get('tts_engine'),
                tts_cost=data.get('tts_cost'),
                tts_duration=data.get('tts_duration'),
                tts_quality_score=data.get('tts_quality_score'),
                moderation_score=data.get('moderation_score'),
                content_safety=data.get('content_safety'),
                thumbnail_score=data.get('thumbnail_score'),
                thumbnail_source=data.get('thumbnail_source'),
                views=data.get('views'),
                likes=data.get('likes'),
                comments=data.get('comments'),
                ctr=data.get('ctr'),
                engagement_rate=data.get('engagement_rate'),
                success_score=data.get('success_score'),
                tags=data.get('tags', []),
                metadata=data.get('metadata', {})
            )
            
            # Store in Firestore
            await self._store_in_firestore(event)
            
            # Store in Pinecone for vector search
            await self._store_in_pinecone(event)
            
            logger.info(f"Logged event {event.event_id} to memory system")
            return True
            
        except Exception as e:
            logger.error(f"Error logging event to memory system: {e}")
            return False
    
    async def _store_in_firestore(self, event: MemoryEvent):
        """Store event in Firestore"""
        if not self.firestore_client:
            return
        
        try:
            # Convert event to dict
            event_data = asdict(event)
            
            # Convert datetime to timestamp
            if isinstance(event_data['timestamp'], datetime):
                event_data['timestamp'] = event_data['timestamp']
            
            # Add TTL field for automatic cleanup
            ttl_date = event.timestamp + timedelta(days=self.ttl_days)
            event_data['ttl_date'] = ttl_date
            
            # Store document
            doc_ref = self.firestore_client.collection(self.collection_name).document(event.event_id)
            doc_ref.set(event_data)
            
            logger.debug(f"Stored event {event.event_id} in Firestore")
            
        except Exception as e:
            logger.error(f"Error storing in Firestore: {e}")
    
    async def _store_in_pinecone(self, event: MemoryEvent):
        """Store event in Pinecone for vector search"""
        if not self.pinecone_index or not self.embedding_model:
            return
        
        try:
            # Create searchable text
            searchable_text = self._create_searchable_text(event)
            
            if not searchable_text.strip():
                return  # Skip if no searchable content
            
            # Generate embedding
            embedding = self._generate_embedding(searchable_text)
            
            # Prepare metadata for Pinecone
            metadata = {
                'event_type': event.event_type,
                'timestamp': event.timestamp.isoformat(),
                'niche': event.niche or 'unknown',
                'tts_engine': event.tts_engine or 'unknown',
                'content_safety': event.content_safety or 'unknown',
                'thumbnail_source': event.thumbnail_source or 'unknown',
                'ttl_date': (event.timestamp + timedelta(days=self.ttl_days)).isoformat()
            }
            
            # Add numeric metadata
            if event.success_score is not None:
                metadata['success_score'] = float(event.success_score)
            if event.moderation_score is not None:
                metadata['moderation_score'] = float(event.moderation_score)
            if event.thumbnail_score is not None:
                metadata['thumbnail_score'] = float(event.thumbnail_score)
            
            # Upsert to Pinecone
            self.pinecone_index.upsert(
                vectors=[(event.event_id, embedding, metadata)]
            )
            
            logger.debug(f"Stored event {event.event_id} in Pinecone")
            
        except Exception as e:
            logger.error(f"Error storing in Pinecone: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def query_history(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query historical data with filters"""
        try:
            results = []
            
            # Query Firestore for structured data
            firestore_results = await self._query_firestore(filters)
            results.extend(firestore_results)
            
            # Query Pinecone for semantic search if text query provided
            if 'text_query' in filters:
                pinecone_results = await self._query_pinecone(filters)
                
                # Merge results, avoiding duplicates
                existing_ids = {r.get('event_id') for r in results}
                for pr in pinecone_results:
                    if pr.get('event_id') not in existing_ids:
                        results.append(pr)
            
            # Apply additional filters and sorting
            results = self._apply_filters(results, filters)
            
            logger.info(f"Query returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error querying history: {e}")
            return []
    
    async def _query_firestore(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query Firestore with filters"""
        if not self.firestore_client:
            return []
        
        try:
            query = self.firestore_client.collection(self.collection_name)
            
            # Apply filters
            if 'event_type' in filters:
                query = query.where('event_type', '==', filters['event_type'])
            
            if 'niche' in filters:
                query = query.where('niche', '==', filters['niche'])
            
            if 'tts_engine' in filters:
                query = query.where('tts_engine', '==', filters['tts_engine'])
            
            if 'video_id' in filters:
                query = query.where('video_id', '==', filters['video_id'])
            
            # Date range filters
            if 'start_date' in filters:
                start_date = filters['start_date']
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date)
                query = query.where('timestamp', '>=', start_date)
            
            if 'end_date' in filters:
                end_date = filters['end_date']
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date)
                query = query.where('timestamp', '<=', end_date)
            
            # Limit results
            limit = filters.get('limit', 100)
            query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            
            results = []
            for doc in docs:
                data = doc.to_dict()
                data['event_id'] = doc.id
                results.append(data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying Firestore: {e}")
            return []
    
    async def _query_pinecone(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query Pinecone for semantic search"""
        if not self.pinecone_index or not self.embedding_model:
            return []
        
        try:
            text_query = filters.get('text_query', '')
            if not text_query:
                return []
            
            # Generate query embedding
            query_embedding = self._generate_embedding(text_query)
            
            # Prepare Pinecone filters
            pinecone_filter = {}
            if 'niche' in filters and filters['niche'] != 'all':
                pinecone_filter['niche'] = filters['niche']
            if 'tts_engine' in filters and filters['tts_engine'] != 'all':
                pinecone_filter['tts_engine'] = filters['tts_engine']
            
            # Query Pinecone
            top_k = filters.get('limit', 50)
            response = self.pinecone_index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=pinecone_filter if pinecone_filter else None
            )
            
            # Convert to standard format
            results = []
            for match in response.matches:
                result = {
                    'event_id': match.id,
                    'similarity_score': float(match.score),
                    **match.metadata
                }
                
                # Convert timestamp back to datetime
                if 'timestamp' in result:
                    result['timestamp'] = datetime.fromisoformat(result['timestamp'])
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying Pinecone: {e}")
            return []
    
    def _apply_filters(self, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply additional filters and sorting to results"""
        try:
            # Filter by success score range
            if 'min_success_score' in filters:
                min_score = filters['min_success_score']
                results = [r for r in results if r.get('success_score', 0) >= min_score]
            
            if 'max_success_score' in filters:
                max_score = filters['max_success_score']
                results = [r for r in results if r.get('success_score', 0) <= max_score]
            
            # Sort results
            sort_by = filters.get('sort_by', 'timestamp')
            sort_order = filters.get('sort_order', 'desc')
            
            if sort_by in ['timestamp', 'success_score', 'moderation_score', 'thumbnail_score']:
                reverse = sort_order == 'desc'
                results.sort(
                    key=lambda x: x.get(sort_by, 0) if sort_by != 'timestamp' else x.get(sort_by, datetime.min),
                    reverse=reverse
                )
            
            # Apply final limit
            final_limit = filters.get('final_limit', len(results))
            results = results[:final_limit]
            
            return results
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            return results
    
    async def cleanup_expired_data(self):
        """Clean up expired data based on TTL"""
        if not self.cleanup_enabled:
            return
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.ttl_days)
            
            # Cleanup Firestore
            await self._cleanup_firestore(cutoff_date)
            
            # Cleanup Pinecone
            await self._cleanup_pinecone(cutoff_date)
            
            logger.info(f"Completed TTL cleanup for data older than {cutoff_date}")
            
        except Exception as e:
            logger.error(f"Error during TTL cleanup: {e}")
    
    async def _cleanup_firestore(self, cutoff_date: datetime):
        """Clean up expired Firestore documents"""
        if not self.firestore_client:
            return
        
        try:
            # Query expired documents
            query = self.firestore_client.collection(self.collection_name)
            query = query.where('timestamp', '<', cutoff_date)
            
            docs = query.stream()
            
            # Delete in batches
            batch = self.firestore_client.batch()
            batch_count = 0
            total_deleted = 0
            
            for doc in docs:
                batch.delete(doc.reference)
                batch_count += 1
                
                if batch_count >= 500:  # Firestore batch limit
                    batch.commit()
                    total_deleted += batch_count
                    batch = self.firestore_client.batch()
                    batch_count = 0
            
            # Commit remaining
            if batch_count > 0:
                batch.commit()
                total_deleted += batch_count
            
            logger.info(f"Deleted {total_deleted} expired documents from Firestore")
            
        except Exception as e:
            logger.error(f"Error cleaning up Firestore: {e}")
    
    async def _cleanup_pinecone(self, cutoff_date: datetime):
        """Clean up expired Pinecone vectors"""
        if not self.pinecone_index:
            return
        
        try:
            # Query expired vectors
            cutoff_iso = cutoff_date.isoformat()
            
            # Pinecone doesn't support direct date comparison in filters
            # We'll need to query and filter manually
            response = self.pinecone_index.query(
                vector=[0.0] * 384,  # Dummy vector
                top_k=10000,  # Large number to get all
                include_metadata=True,
                filter={'timestamp': {'$lt': cutoff_iso}} if self.pinecone_index else None
            )
            
            # Extract IDs of expired vectors
            expired_ids = []
            for match in response.matches:
                timestamp_str = match.metadata.get('timestamp', '')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if timestamp < cutoff_date:
                            expired_ids.append(match.id)
                    except ValueError:
                        continue
            
            # Delete expired vectors in batches
            batch_size = 1000
            total_deleted = 0
            
            for i in range(0, len(expired_ids), batch_size):
                batch_ids = expired_ids[i:i + batch_size]
                self.pinecone_index.delete(ids=batch_ids)
                total_deleted += len(batch_ids)
            
            logger.info(f"Deleted {total_deleted} expired vectors from Pinecone")
            
        except Exception as e:
            logger.error(f"Error cleaning up Pinecone: {e}")
    
    def _schedule_cleanup(self):
        """Schedule automatic cleanup"""
        try:
            # Schedule daily cleanup at 2 AM
            schedule.every().day.at("02:00").do(lambda: asyncio.run(self.cleanup_expired_data()))
            
            # Start scheduler in background thread
            def run_scheduler():
                while True:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
            
            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(run_scheduler)
            
            logger.info("Scheduled automatic TTL cleanup")
            
        except Exception as e:
            logger.error(f"Error scheduling cleanup: {e}")
    
    async def get_performance_insights(self, niche: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get performance insights from memory data"""
        try:
            filters = {
                'start_date': datetime.utcnow() - timedelta(days=days),
                'end_date': datetime.utcnow(),
                'limit': 1000
            }
            
            if niche:
                filters['niche'] = niche
            
            results = await self.query_history(filters)
            
            # Analyze results
            insights = {
                'total_events': len(results),
                'period_days': days,
                'niche': niche or 'all',
                'tts_usage': {},
                'thumbnail_performance': {},
                'engagement_trends': {},
                'cost_analysis': {},
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Analyze TTS usage
            tts_engines = {}
            for result in results:
                engine = result.get('tts_engine')
                if engine and engine != 'unknown':
                    if engine not in tts_engines:
                        tts_engines[engine] = {'count': 0, 'total_cost': 0, 'avg_quality': 0}
                    tts_engines[engine]['count'] += 1
                    tts_engines[engine]['total_cost'] += result.get('tts_cost', 0)
                    if result.get('tts_quality_score'):
                        tts_engines[engine]['avg_quality'] += result.get('tts_quality_score', 0)
            
            # Calculate averages
            for engine_data in tts_engines.values():
                if engine_data['count'] > 0:
                    engine_data['avg_quality'] /= engine_data['count']
                    engine_data['avg_cost'] = engine_data['total_cost'] / engine_data['count']
            
            insights['tts_usage'] = tts_engines
            
            # Analyze thumbnail performance
            thumbnail_sources = {}
            for result in results:
                source = result.get('thumbnail_source')
                if source and source != 'unknown':
                    if source not in thumbnail_sources:
                        thumbnail_sources[source] = {'count': 0, 'avg_score': 0, 'success_rate': 0}
                    thumbnail_sources[source]['count'] += 1
                    thumbnail_sources[source]['avg_score'] += result.get('thumbnail_score', 0)
                    if result.get('success_score', 0) > 0.7:  # Consider >0.7 as successful
                        thumbnail_sources[source]['success_rate'] += 1
            
            # Calculate averages
            for source_data in thumbnail_sources.values():
                if source_data['count'] > 0:
                    source_data['avg_score'] /= source_data['count']
                    source_data['success_rate'] = source_data['success_rate'] / source_data['count'] * 100
            
            insights['thumbnail_performance'] = thumbnail_sources
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating performance insights: {e}")
            return {}

# Global instance
_memory_system = None

def get_memory_system() -> HybridMemorySystem:
    """Get global memory system instance"""
    global _memory_system
    if _memory_system is None:
        _memory_system = HybridMemorySystem()
    return _memory_system

# Convenience functions
async def log_event(data: Dict[str, Any]) -> bool:
    """Log an event to the memory system"""
    memory_system = get_memory_system()
    return await memory_system.log_event(data)

async def query_history(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Query historical data with filters"""
    memory_system = get_memory_system()
    return await memory_system.query_history(filters)

# CLI for testing and maintenance
async def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hybrid Memory System CLI')
    parser.add_argument('--cleanup', action='store_true', help='Run TTL cleanup')
    parser.add_argument('--insights', type=str, help='Generate insights for niche')
    parser.add_argument('--test', action='store_true', help='Run test operations')
    
    args = parser.parse_args()
    
    memory_system = get_memory_system()
    
    if args.cleanup:
        await memory_system.cleanup_expired_data()
    
    elif args.insights:
        insights = await memory_system.get_performance_insights(niche=args.insights)
        print(json.dumps(insights, indent=2, default=str))
    
    elif args.test:
        # Test logging
        test_event = {
            'event_type': 'video_upload',
            'title': 'Test Video',
            'niche': 'technology',
            'tts_engine': 'elevenlabs',
            'tts_cost': 0.05,
            'moderation_score': 0.95,
            'thumbnail_source': 'vertex_ai',
            'thumbnail_score': 0.87,
            'success_score': 0.82
        }
        
        success = await log_event(test_event)
        print(f"Test event logged: {success}")
        
        # Test querying
        results = await query_history({'niche': 'technology', 'limit': 5})
        print(f"Query returned {len(results)} results")

if __name__ == "__main__":
    asyncio.run(main())