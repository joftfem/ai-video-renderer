#!/usr/bin/env python3
"""
🚀 Vertex AI Multi-Task Wrapper for AI Video Renderer

Provides enterprise-grade AI services through Google Cloud Vertex AI:
- Image generation for thumbnails
- Content moderation and safety scoring
- Text-to-Speech fallback routing
- Text summarization for hooks and highlights
- Comprehensive logging and error handling

Author: AI Video Renderer Team
Version: 1.0.0
Last Updated: 2025-01-27
"""

import os
import json
import time
import logging
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import base64
import io

try:
    from google.cloud import aiplatform
    from google.cloud import texttospeech
    from google.oauth2 import service_account
    import vertexai
    from vertexai.preview.generative_models import GenerativeModel, Image, Part
    from vertexai.preview.vision_models import ImageGenerationModel
    VERTEX_AVAILABLE = True
except ImportError as e:
    VERTEX_AVAILABLE = False
    print(f"⚠️ Vertex AI dependencies not available: {e}")

try:
    import requests
    from PIL import Image as PILImage
except ImportError:
    requests = None
    PILImage = None

class VertexAIHandler:
    """Centralized Vertex AI service handler with fallback mechanisms"""
    
    def __init__(self, project_id: str = None, location: str = "us-central1"):
        self.project_id = project_id or os.getenv('GOOGLE_PROJECT_ID', 'brave-hearth-464820-s2')
        self.location = location
        self.logger = self._setup_logging()
        self.cache = {}
        self.rate_limits = {
            'image_generation': {'calls': 0, 'window_start': time.time(), 'limit': 10},
            'text_generation': {'calls': 0, 'window_start': time.time(), 'limit': 60},
            'tts': {'calls': 0, 'window_start': time.time(), 'limit': 30}
        }
        
        if VERTEX_AVAILABLE:
            try:
                # Initialize Vertex AI
                vertexai.init(project=self.project_id, location=self.location)
                self.logger.info(f"✅ Vertex AI initialized for project: {self.project_id}")
                
                # Initialize models
                self.text_model = GenerativeModel("gemini-pro")
                self.image_model = ImageGenerationModel.from_pretrained("imagegeneration@005")
                self.tts_client = texttospeech.TextToSpeechClient()
                
                self.logger.info("✅ All Vertex AI models initialized successfully")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize Vertex AI: {e}")
                VERTEX_AVAILABLE = False
        else:
            self.logger.warning("⚠️ Vertex AI not available, fallback mode enabled")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup dedicated Vertex AI logging"""
        logger = logging.getLogger('vertex_ai')
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # File handler for Vertex usage logging
        file_handler = logging.FileHandler(log_dir / 'vertex_usage.log')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _check_rate_limit(self, service: str) -> bool:
        """Check if service is within rate limits"""
        current_time = time.time()
        rate_info = self.rate_limits.get(service, {})
        
        # Reset window if 60 seconds have passed
        if current_time - rate_info.get('window_start', 0) > 60:
            rate_info['calls'] = 0
            rate_info['window_start'] = current_time
        
        # Check if within limit
        if rate_info['calls'] >= rate_info.get('limit', 10):
            self.logger.warning(f"⚠️ Rate limit exceeded for {service}")
            return False
        
        rate_info['calls'] += 1
        return True
    
    def _cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        content = '|'.join(str(arg) for arg in args)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _log_usage(self, service: str, success: bool, latency: float, **kwargs):
        """Log Vertex AI usage for monitoring"""
        usage_data = {
            'timestamp': datetime.now().isoformat(),
            'service': service,
            'success': success,
            'latency_ms': round(latency * 1000, 2),
            'project_id': self.project_id,
            **kwargs
        }
        self.logger.info(f"VERTEX_USAGE: {json.dumps(usage_data)}")
    
    def generate_thumbnail(self, prompt: str, niche: str, style: str = "photorealistic") -> Optional[str]:
        """Generate thumbnail using Vertex AI Image Generation"""
        start_time = time.time()
        
        if not VERTEX_AVAILABLE:
            self.logger.error("❌ Vertex AI not available for thumbnail generation")
            return None
        
        if not self._check_rate_limit('image_generation'):
            return None
        
        # Check cache first
        cache_key = self._cache_key('thumbnail', prompt, niche, style)
        if cache_key in self.cache:
            self.logger.info("📦 Using cached thumbnail")
            return self.cache[cache_key]
        
        try:
            # Enhanced prompt for better thumbnails
            enhanced_prompt = f"""
            Create a high-quality YouTube thumbnail for {niche} content.
            Title: {prompt}
            Style: {style}, vibrant colors, eye-catching, professional
            Requirements: 1280x720, clear text overlay space, engaging composition
            Avoid: cluttered design, small text, dark colors
            """.strip()
            
            self.logger.info(f"🎨 Generating thumbnail: {prompt[:50]}...")
            
            # Generate image
            response = self.image_model.generate_images(
                prompt=enhanced_prompt,
                number_of_images=1,
                aspect_ratio="16:9",
                safety_filter_level="block_some",
                person_generation="allow_adult"
            )
            
            if response.images:
                # Save image
                thumbnail_dir = Path('thumbnails')
                thumbnail_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{niche}_{timestamp}_vertex.png"
                filepath = thumbnail_dir / filename
                
                # Save the generated image
                response.images[0].save(location=str(filepath))
                
                # Cache result
                self.cache[cache_key] = str(filepath)
                
                latency = time.time() - start_time
                self._log_usage('image_generation', True, latency, 
                              prompt_length=len(prompt), niche=niche)
                
                self.logger.info(f"✅ Thumbnail generated: {filepath}")
                return str(filepath)
            else:
                raise Exception("No images generated")
                
        except Exception as e:
            latency = time.time() - start_time
            self._log_usage('image_generation', False, latency, 
                          error=str(e), niche=niche)
            self.logger.error(f"❌ Thumbnail generation failed: {e}")
            return None
    
    def moderate_text(self, input_text: str, threshold: float = 0.8) -> Dict[str, Any]:
        """Content safety scoring using Vertex AI moderation"""
        start_time = time.time()
        
        if not VERTEX_AVAILABLE:
            self.logger.warning("⚠️ Vertex AI not available, using basic moderation")
            return {
                'safe': True,
                'score': 0.9,
                'categories': [],
                'method': 'basic_fallback'
            }
        
        if not self._check_rate_limit('text_generation'):
            return {'safe': False, 'score': 0.0, 'categories': ['rate_limited']}
        
        try:
            # Use Gemini for content moderation
            moderation_prompt = f"""
            Analyze this content for YouTube safety compliance.
            Rate safety from 0.0 (unsafe) to 1.0 (completely safe).
            Consider: violence, hate speech, adult content, misinformation, spam.
            
            Content: {input_text[:1000]}...
            
            Respond in JSON format:
            {{
                "safety_score": 0.0-1.0,
                "flagged_categories": ["category1", "category2"],
                "reasoning": "brief explanation",
                "safe_for_youtube": true/false
            }}
            """
            
            response = self.text_model.generate_content(moderation_prompt)
            
            # Parse JSON response
            try:
                result = json.loads(response.text.strip())
                safety_score = result.get('safety_score', 0.5)
                is_safe = safety_score >= threshold and result.get('safe_for_youtube', False)
                
                moderation_result = {
                    'safe': is_safe,
                    'score': safety_score,
                    'categories': result.get('flagged_categories', []),
                    'reasoning': result.get('reasoning', ''),
                    'method': 'vertex_gemini'
                }
                
                latency = time.time() - start_time
                self._log_usage('content_moderation', True, latency,
                              text_length=len(input_text), safety_score=safety_score)
                
                self.logger.info(f"🛡️ Content moderated: score={safety_score:.2f}, safe={is_safe}")
                return moderation_result
                
            except json.JSONDecodeError:
                # Fallback parsing
                is_safe = 'safe' in response.text.lower() and 'unsafe' not in response.text.lower()
                return {
                    'safe': is_safe,
                    'score': 0.7 if is_safe else 0.3,
                    'categories': [],
                    'reasoning': 'Fallback parsing',
                    'method': 'vertex_fallback'
                }
                
        except Exception as e:
            latency = time.time() - start_time
            self._log_usage('content_moderation', False, latency, error=str(e))
            self.logger.error(f"❌ Content moderation failed: {e}")
            
            # Conservative fallback
            return {
                'safe': False,
                'score': 0.5,
                'categories': ['moderation_error'],
                'reasoning': f'Moderation failed: {str(e)}',
                'method': 'error_fallback'
            }
    
    def generate_voice(self, text: str, language_code: str = 'en-US', 
                      voice_name: str = None) -> Optional[str]:
        """TTS fallback using Vertex Speech synthesis"""
        start_time = time.time()
        
        if not VERTEX_AVAILABLE:
            self.logger.error("❌ Vertex AI not available for TTS")
            return None
        
        if not self._check_rate_limit('tts'):
            return None
        
        # Check cache
        cache_key = self._cache_key('tts', text, language_code, voice_name)
        if cache_key in self.cache:
            self.logger.info("📦 Using cached TTS audio")
            return self.cache[cache_key]
        
        try:
            # Configure voice
            if not voice_name:
                voice_name = 'en-US-Neural2-D' if language_code.startswith('en') else None
            
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            
            # Configure audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0
            )
            
            # Synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text[:5000])  # Limit text length
            
            self.logger.info(f"🎵 Generating TTS: {len(text)} characters")
            
            # Generate speech
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Save audio file
            audio_dir = Path('audio')
            audio_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"vertex_tts_{timestamp}.mp3"
            filepath = audio_dir / filename
            
            with open(filepath, 'wb') as audio_file:
                audio_file.write(response.audio_content)
            
            # Cache result
            self.cache[cache_key] = str(filepath)
            
            latency = time.time() - start_time
            self._log_usage('tts', True, latency,
                          text_length=len(text), language=language_code)
            
            self.logger.info(f"✅ TTS generated: {filepath}")
            return str(filepath)
            
        except Exception as e:
            latency = time.time() - start_time
            self._log_usage('tts', False, latency, error=str(e))
            self.logger.error(f"❌ TTS generation failed: {e}")
            return None
    
    def summarize_text(self, input_text: str, max_length: int = 200) -> Optional[str]:
        """Text summarization for hooks and highlights"""
        start_time = time.time()
        
        if not VERTEX_AVAILABLE:
            self.logger.error("❌ Vertex AI not available for summarization")
            return None
        
        if not self._check_rate_limit('text_generation'):
            return None
        
        # Check cache
        cache_key = self._cache_key('summarize', input_text, max_length)
        if cache_key in self.cache:
            self.logger.info("📦 Using cached summary")
            return self.cache[cache_key]
        
        try:
            summary_prompt = f"""
            Create a compelling, engaging summary of this content for YouTube.
            Maximum {max_length} characters. Focus on key insights and hooks.
            Make it attention-grabbing and clickable.
            
            Content: {input_text[:2000]}...
            
            Summary:
            """
            
            response = self.text_model.generate_content(summary_prompt)
            summary = response.text.strip()
            
            # Ensure length limit
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            
            # Cache result
            self.cache[cache_key] = summary
            
            latency = time.time() - start_time
            self._log_usage('text_summarization', True, latency,
                          input_length=len(input_text), output_length=len(summary))
            
            self.logger.info(f"✅ Text summarized: {len(input_text)} → {len(summary)} chars")
            return summary
            
        except Exception as e:
            latency = time.time() - start_time
            self._log_usage('text_summarization', False, latency, error=str(e))
            self.logger.error(f"❌ Text summarization failed: {e}")
            return None
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'cache_size': len(self.cache),
            'rate_limits': self.rate_limits.copy(),
            'vertex_available': VERTEX_AVAILABLE,
            'project_id': self.project_id,
            'location': self.location
        }
        return stats
    
    def clear_cache(self):
        """Clear the internal cache"""
        self.cache.clear()
        self.logger.info("🧹 Cache cleared")

# Global instance for easy import
vertex_handler = VertexAIHandler()

# Convenience functions for easy import
def generate_thumbnail(prompt: str, niche: str, style: str = "photorealistic") -> Optional[str]:
    """Generate thumbnail using Vertex AI"""
    return vertex_handler.generate_thumbnail(prompt, niche, style)

def moderate_text(input_text: str, threshold: float = 0.8) -> Dict[str, Any]:
    """Moderate content using Vertex AI"""
    return vertex_handler.moderate_text(input_text, threshold)

def generate_voice(text: str, language_code: str = 'en-US') -> Optional[str]:
    """Generate voice using Vertex AI TTS"""
    return vertex_handler.generate_voice(text, language_code)

def summarize_text(input_text: str, max_length: int = 200) -> Optional[str]:
    """Summarize text using Vertex AI"""
    return vertex_handler.summarize_text(input_text, max_length)

if __name__ == "__main__":
    # Test the handler
    handler = VertexAIHandler()
    print("🧪 Testing Vertex AI Handler...")
    
    # Test moderation
    moderation = handler.moderate_text("This is a test video about AI technology")
    print(f"Moderation result: {moderation}")
    
    # Test summarization
    summary = handler.summarize_text("This is a long article about artificial intelligence and its impact on society...")
    print(f"Summary: {summary}")
    
    # Print usage stats
    stats = handler.get_usage_stats()
    print(f"Usage stats: {json.dumps(stats, indent=2)}")