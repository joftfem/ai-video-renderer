#!/usr/bin/env python3
"""
AI Video Renderer - Production Pipeline
Handles markdown → video conversion with multiple fallback methods
Supports multi-niche automation with intelligent routing
"""

import os
import sys
import json
import requests
import subprocess
import logging
import argparse
from datetime import datetime
from pathlib import Path
import re
from typing import Optional, Dict, List, Tuple, Union
import time
from dotenv import load_dotenv
import base64
import hashlib
import random
import asyncio
import json
from datetime import datetime, timedelta
try:
    from PIL import Image
except ImportError:
    Image = None
try:
    from google.cloud import vision
except ImportError:
    vision = None
    print("[WARNING] Google Cloud Vision not available. Thumbnail safety checks disabled.")

try:
    from google.cloud import texttospeech
except ImportError:
    texttospeech = None
    print("[WARNING] Google Cloud TTS not available. Using fallback TTS.")

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
    print("[WARNING] pyttsx3 not available. Local TTS fallback disabled.")

import io

# Import our custom modules
try:
    from content_variation import ContentVariationEngine
except ImportError:
    ContentVariationEngine = None
    print("[WARNING] ContentVariationEngine not available. Content variations disabled.")

try:
    from compliance_monitor import ComplianceMonitor
except ImportError:
    ComplianceMonitor = None
    print("[WARNING] ComplianceMonitor not available. Compliance monitoring disabled.")

# Import Vertex AI handler
try:
    from utils.vertex_handler import generate_thumbnail, generate_voice, moderate_text, summarize_text
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    print("[WARNING] Vertex AI handler not available. Using fallback methods.")

# Load environment variables
load_dotenv('.env.n8n')

class MultiTTSEngine:
    def __init__(self):
        self.tts_engine = os.getenv('TTS_ENGINE', 'elevenlabs')
        self.retry_max = int(os.getenv('TTS_RETRY_MAX', '3'))
        self.retry_backoff = os.getenv('TTS_RETRY_BACKOFF', 'true').lower() == 'true'
        self.fallback_enabled = os.getenv('TTS_FALLBACK_ENABLED', 'true').lower() == 'true'
        
        # API Keys
        self.elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
        self.openai_key = os.getenv('TTS_OPENAI_KEY')
        self.google_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        # Voice settings
        self.elevenlabs_voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'joft_default_voice')
        self.openai_voice = os.getenv('OPENAI_TTS_VOICE', 'shimmer')
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.2  # seconds between requests
        
        # TTS cache to avoid duplicates
        self.tts_cache = {}
        
        # Setup logging
        self.setup_tts_logging()
    
    def setup_tts_logging(self):
        """Setup TTS-specific logging"""
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        self.tts_log_file = os.path.join(log_dir, 'tts.log')
    
    def log_tts_event(self, event_type, message, text_chunk=None):
        """Log TTS events with timestamp"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'event_type': event_type,
            'message': message,
            'text_chunk_length': len(text_chunk) if text_chunk else 0,
            'engine': self.tts_engine
        }
        
        try:
            with open(self.tts_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"[WARNING] Failed to log TTS event: {e}")
    
    def rate_limit_wait(self):
        """Implement rate limiting between TTS requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            self.log_tts_event('RATE_LIMIT', f'Waiting {wait_time:.2f}s for rate limit')
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def get_cache_key(self, text, voice_id=None):
        """Generate cache key for TTS request"""
        cache_data = f"{text}_{voice_id or 'default'}_{self.tts_engine}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def safe_elevenlabs_tts(self, text, output_path, voice_id=None):
        """Safe ElevenLabs TTS with rate limiting and retry logic"""
        if not self.elevenlabs_key:
            self.log_tts_event('ERROR', 'ElevenLabs API key not configured')
            return False
        
        voice_id = voice_id or self.elevenlabs_voice_id
        cache_key = self.get_cache_key(text, voice_id)
        
        # Check cache
        if cache_key in self.tts_cache:
            cached_path = self.tts_cache[cache_key]
            if os.path.exists(cached_path):
                import shutil
                shutil.copy2(cached_path, output_path)
                self.log_tts_event('CACHE_HIT', f'Used cached TTS for {len(text)} chars')
                return True
        
        url = "https://api.elevenlabs.io/v1/text-to-speech/" + voice_id
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        for attempt in range(self.retry_max):
            try:
                self.rate_limit_wait()
                self.log_tts_event('REQUEST', f'ElevenLabs attempt {attempt + 1}/{self.retry_max}', text)
                
                response = requests.post(url, json=data, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Cache successful result
                    self.tts_cache[cache_key] = output_path
                    self.log_tts_event('SUCCESS', f'ElevenLabs TTS completed for {len(text)} chars')
                    return True
                
                elif response.status_code == 429:
                    # Rate limited
                    retry_delay = (15, 30, 45)[min(attempt, 2)] if self.retry_backoff else 15
                    self.log_tts_event('RATE_LIMITED', f'HTTP 429, retrying in {retry_delay}s')
                    time.sleep(retry_delay)
                    continue
                
                else:
                    self.log_tts_event('ERROR', f'ElevenLabs HTTP {response.status_code}: {response.text}')
                    
            except Exception as e:
                self.log_tts_event('EXCEPTION', f'ElevenLabs error: {str(e)}')
                if attempt < self.retry_max - 1:
                    retry_delay = (5, 10, 15)[min(attempt, 2)] if self.retry_backoff else 5
                    time.sleep(retry_delay)
        
        self.log_tts_event('FAILED', f'ElevenLabs failed after {self.retry_max} attempts')
        return False
    
    def safe_openai_tts(self, text, output_path, voice="shimmer"):
        """Safe OpenAI TTS fallback"""
        if not self.openai_key:
            self.log_tts_event('ERROR', 'OpenAI TTS API key not configured')
            return False
        
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "tts-1",
            "voice": voice,
            "input": text
        }
        
        try:
            self.log_tts_event('REQUEST', f'OpenAI TTS fallback for {len(text)} chars', text)
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                self.log_tts_event('SUCCESS', 'OpenAI TTS completed successfully')
                return True
            else:
                self.log_tts_event('ERROR', f'OpenAI TTS failed ({response.status_code}): {response.text}')
                return False
                
        except Exception as e:
            self.log_tts_event('EXCEPTION', f'OpenAI TTS error: {str(e)}')
            return False
    
    def safe_google_tts(self, text, output_path, language_code="en-US"):
        """Safe Google Cloud TTS fallback"""
        if not texttospeech or not self.google_credentials:
            self.log_tts_event('ERROR', 'Google Cloud TTS not configured')
            return False
        
        try:
            client = texttospeech.TextToSpeechClient()
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            self.log_tts_event('REQUEST', f'Google TTS fallback for {len(text)} chars', text)
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            
            with open(output_path, "wb") as f:
                f.write(response.audio_content)
            
            self.log_tts_event('SUCCESS', 'Google TTS completed successfully')
            return True
            
        except Exception as e:
            self.log_tts_event('EXCEPTION', f'Google TTS error: {str(e)}')
            return False
    
    def safe_local_tts(self, text, output_path):
        """Local pyttsx3 TTS as last resort"""
        if not pyttsx3:
            self.log_tts_event('ERROR', 'pyttsx3 not available for local TTS')
            return False
        
        try:
            engine = pyttsx3.init()
            
            # Configure voice settings
            voices = engine.getProperty('voices')
            if voices:
                engine.setProperty('voice', voices[0].id)
            
            engine.setProperty('rate', 150)  # Speed
            engine.setProperty('volume', 0.9)  # Volume
            
            self.log_tts_event('REQUEST', f'Local TTS fallback for {len(text)} chars', text)
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            
            if os.path.exists(output_path):
                self.log_tts_event('SUCCESS', 'Local TTS completed successfully')
                return True
            else:
                self.log_tts_event('ERROR', 'Local TTS failed to create output file')
                return False
                
        except Exception as e:
            self.log_tts_event('EXCEPTION', f'Local TTS error: {str(e)}')
            return False
    
    def generate_audio(self, text, output_path):
        """Main TTS generation with fallback chain"""
        self.log_tts_event('START', f'Starting TTS generation for {len(text)} characters')
        
        # Primary: ElevenLabs
        if self.tts_engine == 'elevenlabs' and self.elevenlabs_key:
            if self.safe_elevenlabs_tts(text, output_path):
                return True
            
            if not self.fallback_enabled:
                return False
            
            self.log_tts_event('FALLBACK', 'ElevenLabs failed, trying OpenAI TTS')
        
        # Secondary: OpenAI TTS
        if self.openai_key:
            if self.safe_openai_tts(text, output_path, self.openai_voice):
                return True
            
            self.log_tts_event('FALLBACK', 'OpenAI TTS failed, trying Google TTS')
        
        # Tertiary: Google Cloud TTS
        if self.safe_google_tts(text, output_path):
            return True
        
        self.log_tts_event('FALLBACK', 'Google TTS failed, trying Vertex AI TTS')
        
        # Quaternary: Vertex AI TTS
        if VERTEX_AI_AVAILABLE:
            try:
                vertex_audio_path = generate_voice(text)
                if vertex_audio_path and os.path.exists(vertex_audio_path):
                    import shutil
                    shutil.copy2(vertex_audio_path, output_path)
                    self.log_tts_event('SUCCESS', 'Vertex AI TTS completed successfully')
                    return True
            except Exception as e:
                self.log_tts_event('EXCEPTION', f'Vertex AI TTS error: {str(e)}')
        
        self.log_tts_event('FALLBACK', 'Vertex AI TTS failed, trying local TTS')
        
        # Last resort: Local TTS
        if self.safe_local_tts(text, output_path):
            return True
        
        self.log_tts_event('FAILED', 'All TTS engines failed')
        return False

class ThumbnailGenerator:
    """Free AI-powered thumbnail generator using HuggingFace"""
    
    def __init__(self, niche: str, logger: logging.Logger):
        self.niche = niche
        self.logger = logger
        self.hf_token = os.getenv('HF_TOKEN')
        self.thumbnail_dir = os.getenv('THUMBNAIL_OUTPUT_DIR', 'thumbnails')
        self.model = os.getenv('THUMBNAIL_MODEL', 'stabilityai/stable-diffusion-2-1')
        self.width = int(os.getenv('THUMBNAIL_WIDTH', '1280'))
        self.height = int(os.getenv('THUMBNAIL_HEIGHT', '720'))
        
        # Ensure thumbnails directory exists
        os.makedirs(self.thumbnail_dir, exist_ok=True)
    
    def extract_title_from_markdown(self, markdown_content: str) -> str:
        """Extract title from markdown content"""
        lines = markdown_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            elif line.startswith('## '):
                return line[3:].strip()
            elif line and not line.startswith('::') and len(line) > 10:
                # Use first meaningful line as title
                return line[:100]  # Limit title length
        return "AI Generated Video"
    
    def generate_thumbnail_prompt(self, title: str) -> str:
        """Generate AI prompt based on niche and title"""
        niche_prompts = {
            'ai': f"Futuristic AI technology thumbnail for '{title}', cyberpunk style, neon blue and purple colors, robot elements, high contrast, professional YouTube thumbnail, 16:9 aspect ratio",
            'crypto': f"Cryptocurrency thumbnail for '{title}', golden Bitcoin coins, trading charts, modern finance graphics, green and gold colors, professional design, 16:9 aspect ratio",
            'finance': f"Professional finance thumbnail for '{title}', money symbols, stock market graphs, business style, blue and gold colors, clean design, 16:9 aspect ratio",
            'history': f"Historical documentary thumbnail for '{title}', vintage style, sepia tones, ancient elements, documentary feel, professional design, 16:9 aspect ratio",
            'lifestyle': f"Lifestyle thumbnail for '{title}', bright vibrant colors, modern design, aspirational imagery, clean layout, 16:9 aspect ratio",
            'motivation': f"Motivational thumbnail for '{title}', inspiring imagery, bold design, success symbols, energetic colors, 16:9 aspect ratio"
        }
        
        base_prompt = niche_prompts.get(self.niche, niche_prompts['ai'])
        return f"{base_prompt}, high quality, detailed, professional YouTube thumbnail"
    
    def query_huggingface_api(self, prompt: str) -> Optional[bytes]:
        """Query HuggingFace API for image generation"""
        if not self.hf_token:
            self.logger.warning("HF_TOKEN not found, skipping AI thumbnail generation")
            return None
        
        api_url = f"https://api-inference.huggingface.co/models/{self.model}"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "width": self.width,
                "height": self.height,
                "num_inference_steps": 20,
                "guidance_scale": 7.5
            }
        }
        
        try:
            self.logger.info(f"Generating AI thumbnail with prompt: {prompt[:100]}...")
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                return response.content
            elif response.status_code == 503:
                self.logger.warning("HuggingFace model is loading, waiting 20 seconds...")
                time.sleep(20)
                # Retry once
                response = requests.post(api_url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    return response.content
            
            self.logger.error(f"HuggingFace API error: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error calling HuggingFace API: {e}")
            return None
    
    def extract_frame_from_video(self, video_path: str, output_path: str) -> bool:
        """Extract a frame from video using FFmpeg as fallback"""
        try:
            cmd = [
                'ffmpeg', '-i', video_path,
                '-ss', '00:00:05',  # Extract frame at 5 seconds
                '-vframes', '1',
                '-vf', f'scale={self.width}:{self.height}',
                '-y', output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"Extracted video frame to {output_path}")
                return True
            else:
                self.logger.error(f"FFmpeg frame extraction failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error extracting frame from video: {e}")
            return False
    
    def generate_thumbnail(self, title: str, video_path: str = None) -> Optional[str]:
        """Generate thumbnail using AI or fallback to video frame"""
        if not os.getenv('THUMBNAIL_ENABLED', 'true').lower() == 'true':
            self.logger.info("Thumbnail generation disabled")
            return None
        
        # Generate output filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        thumbnail_filename = f"thumbnail-{self.niche}-{safe_title}.png"
        thumbnail_path = os.path.join(self.thumbnail_dir, thumbnail_filename)
        
        # Try AI generation first
        prompt = self.generate_thumbnail_prompt(title)
        image_data = self.query_huggingface_api(prompt)
        
        if image_data:
            try:
                # Save AI-generated image
                with open(thumbnail_path, 'wb') as f:
                    f.write(image_data)
                
                # Verify image is valid
                if Image:
                    img = Image.open(thumbnail_path)
                    img.verify()
                
                self.logger.info(f"AI thumbnail generated successfully: {thumbnail_path}")
                return thumbnail_path
                
            except Exception as e:
                self.logger.error(f"Error saving AI thumbnail: {e}")
        
        # Try Vertex AI as secondary fallback
        if VERTEX_AI_AVAILABLE:
            try:
                self.logger.info("Trying Vertex AI thumbnail generation")
                vertex_thumbnail_path = generate_thumbnail(title, self.niche)
                if vertex_thumbnail_path and os.path.exists(vertex_thumbnail_path):
                    # Copy to expected location
                    import shutil
                    shutil.copy2(vertex_thumbnail_path, thumbnail_path)
                    self.logger.info(f"Vertex AI thumbnail generated: {thumbnail_path}")
                    return thumbnail_path
            except Exception as e:
                self.logger.error(f"Vertex AI thumbnail generation failed: {e}")
        
        # Fallback to video frame extraction
        if video_path and os.path.exists(video_path):
            fallback_enabled = os.getenv('THUMBNAIL_FALLBACK', 'ffmpeg').lower() == 'ffmpeg'
            if fallback_enabled:
                self.logger.info("Falling back to video frame extraction")
                if self.extract_frame_from_video(video_path, thumbnail_path):
                    return thumbnail_path
        
        self.logger.warning("Thumbnail generation failed completely")
        return None

class YouTubeComplianceValidator:
    """YouTube compliance and safety validator"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.vision_client = None
        if vision:
            try:
                self.vision_client = vision.ImageAnnotatorClient()
            except Exception as e:
                self.logger.warning(f"Google Vision API not available: {e}")
        
        # Compliance thresholds
        self.safe_search_threshold = float(os.getenv('COMPLIANCE_THRESHOLD', '0.8'))
        self.max_title_length = int(os.getenv('MAX_TITLE_LENGTH', '60'))
        self.max_uploads_per_day = int(os.getenv('MAX_UPLOADS_PER_DAY', '3'))
        
        # Flagged keywords and phrases
        self.spam_keywords = [
            'make money fast', 'get rich quick', 'you won\'t believe', 
            'ultimate hack', 'secret method', 'instant results',
            'guaranteed income', 'easy money', 'work from home scam',
            'click here now', 'limited time offer', 'act now'
        ]
        
        self.sensitive_topics = [
            'covid', 'coronavirus', 'pandemic', 'vaccine', 'conspiracy',
            'politics', 'election', 'violence', 'terrorism', 'war',
            'adult content', 'gambling', 'drugs', 'weapons'
        ]
    
    def validate_title(self, title: str) -> Dict[str, any]:
        """Validate YouTube title for compliance"""
        issues = []
        score = 1.0
        
        # Length check
        if len(title) > self.max_title_length:
            issues.append(f"Title too long ({len(title)} > {self.max_title_length})")
            score -= 0.2
        
        # Spam keyword check
        title_lower = title.lower()
        spam_found = [kw for kw in self.spam_keywords if kw in title_lower]
        if spam_found:
            issues.append(f"Spam keywords found: {spam_found}")
            score -= 0.3
        
        # Excessive caps check
        caps_ratio = sum(1 for c in title if c.isupper()) / len(title) if title else 0
        if caps_ratio > 0.3:
            issues.append(f"Too many capital letters ({caps_ratio:.1%})")
            score -= 0.2
        
        # Emoji count check
        emoji_count = sum(1 for c in title if ord(c) > 127)
        if emoji_count > 3:
            issues.append(f"Too many emojis ({emoji_count})")
            score -= 0.1
        
        return {
            'compliant': score >= 0.7,
            'score': max(0, score),
            'issues': issues,
            'cleaned_title': self._clean_title(title)
        }
    
    def validate_content(self, content: str) -> Dict[str, any]:
        """Validate content for sensitive topics"""
        issues = []
        score = 1.0
        content_lower = content.lower()
        
        # Sensitive topic check
        sensitive_found = [topic for topic in self.sensitive_topics if topic in content_lower]
        if sensitive_found:
            issues.append(f"Sensitive topics found: {sensitive_found}")
            score -= 0.4
        
        # Content length check
        if len(content) < 100:
            issues.append("Content too short for quality guidelines")
            score -= 0.2
        
        return {
            'compliant': score >= 0.6,
            'score': max(0, score),
            'issues': issues,
            'flagged_topics': sensitive_found
        }
    
    def validate_thumbnail_safety(self, thumbnail_path: str) -> Dict[str, any]:
        """Validate thumbnail using Google Vision SafeSearch"""
        if not self.vision_client or not os.path.exists(thumbnail_path):
            return {'compliant': True, 'score': 1.0, 'issues': []}
        
        try:
            with open(thumbnail_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = self.vision_client.safe_search_detection(image=image)
            safe = response.safe_search_annotation
            
            # Convert likelihood to score
            likelihood_scores = {
                'VERY_UNLIKELY': 1.0,
                'UNLIKELY': 0.8,
                'POSSIBLE': 0.5,
                'LIKELY': 0.2,
                'VERY_LIKELY': 0.0
            }
            
            adult_score = likelihood_scores.get(safe.adult.name, 0.5)
            violence_score = likelihood_scores.get(safe.violence.name, 0.5)
            racy_score = likelihood_scores.get(safe.racy.name, 0.5)
            
            overall_score = min(adult_score, violence_score, racy_score)
            
            issues = []
            if adult_score < 0.8:
                issues.append(f"Adult content detected: {safe.adult.name}")
            if violence_score < 0.8:
                issues.append(f"Violence detected: {safe.violence.name}")
            if racy_score < 0.8:
                issues.append(f"Racy content detected: {safe.racy.name}")
            
            return {
                'compliant': overall_score >= self.safe_search_threshold,
                'score': overall_score,
                'issues': issues,
                'details': {
                    'adult': safe.adult.name,
                    'violence': safe.violence.name,
                    'racy': safe.racy.name
                }
            }
            
        except Exception as e:
            self.logger.error(f"Thumbnail safety check failed: {e}")
            return {'compliant': True, 'score': 1.0, 'issues': [f"Safety check failed: {e}"]}
    
    def check_upload_rate_limit(self) -> Dict[str, any]:
        """Check if upload rate limit is exceeded"""
        log_file = 'logs/upload_history.log'
        if not os.path.exists(log_file):
            return {'allowed': True, 'uploads_today': 0}
        
        today = datetime.now().date()
        uploads_today = 0
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        upload_date = datetime.fromisoformat(line.strip()).date()
                        if upload_date == today:
                            uploads_today += 1
        except Exception as e:
            self.logger.error(f"Error reading upload history: {e}")
        
        return {
            'allowed': uploads_today < self.max_uploads_per_day,
            'uploads_today': uploads_today,
            'limit': self.max_uploads_per_day
        }
    
    def log_upload_attempt(self):
        """Log upload attempt with timestamp"""
        log_file = 'logs/upload_history.log'
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()}\n")
    
    def _clean_title(self, title: str) -> str:
        """Clean title by removing spam elements"""
        cleaned = title
        
        # Remove excessive emojis (keep max 2)
        emoji_count = 0
        result = []
        for char in cleaned:
            if ord(char) > 127:  # Likely emoji
                if emoji_count < 2:
                    result.append(char)
                    emoji_count += 1
            else:
                result.append(char)
        cleaned = ''.join(result)
        
        # Limit caps (convert excess to lowercase)
        words = cleaned.split()
        for i, word in enumerate(words):
            if len(word) > 3 and word.isupper():
                words[i] = word.capitalize()
        cleaned = ' '.join(words)
        
        # Truncate if too long
        if len(cleaned) > self.max_title_length:
            cleaned = cleaned[:self.max_title_length-3] + '...'
        
        return cleaned.strip()
    
    def generate_safe_upload_delay(self) -> int:
        """Generate randomized upload delay to avoid pattern detection"""
        base_delay = int(os.getenv('BASE_UPLOAD_DELAY', '3600'))  # 1 hour default
        max_variation = int(os.getenv('UPLOAD_DELAY_VARIATION', '1800'))  # 30 min variation
        
        return base_delay + random.randint(0, max_variation)

class VideoRenderer:
    def __init__(self, niche: str = "default", markdown_file: Optional[str] = None):
        self.niche = niche
        self.markdown_file = Path(markdown_file) if markdown_file else None
        self.project_name = self.markdown_file.stem if self.markdown_file else "default"
        self.setup_logging()
        self.setup_directories()
        self.validate_environment()
        
        # Initialize components
        self.thumbnail_generator = ThumbnailGenerator(self.niche, self.logger)
        self.compliance_validator = YouTubeComplianceValidator(self.logger)
        self.tts_engine = MultiTTSEngine()
        self.variation_engine = ContentVariationEngine() if ContentVariationEngine else None
        self.compliance_monitor = ComplianceMonitor() if ComplianceMonitor else None
        
        # Setup upload logging
        self.setup_upload_logging()
    
    def setup_upload_logging(self):
        """Setup upload-specific logging"""
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        self.upload_log_file = os.path.join(log_dir, 'upload.log')
    
    def log_upload_event(self, event_type, message, video_data=None):
        """Log upload events with timestamp"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'event_type': event_type,
            'message': message,
            'video_title': video_data.get('title') if video_data else None,
            'niche': video_data.get('niche') if video_data else None
        }
        
        try:
            with open(self.upload_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"[WARNING] Failed to log upload event: {e}")
    
    def add_anti_shadowban_metadata(self, title, description, niche):
        """Add anti-shadowban metadata to prevent YouTube flagging"""
        # Randomize upload jitter (3-8 minutes)
        upload_jitter = random.randint(180, 480)  # seconds
        
        # Add random emoji or hook to title (but keep it compliant)
        title_hooks = [
            "🔥", "💡", "⚡", "🚀", "✨", "🎯", "💯", "🌟"
        ]
        
        # Only add emoji if title is short enough
        if len(title) < 55:
            random_hook = random.choice(title_hooks)
            title = f"{random_hook} {title}"
        
        # Add human-like description with timestamp and CTA
        timestamp_note = f"\n\n📅 Published on {datetime.now().strftime('%B %d, %Y')}"
        
        cta_options = [
            "\n\n👍 Like this video if it helped you!",
            "\n\n🔔 Subscribe for more content like this!",
            "\n\n💬 Let me know your thoughts in the comments!",
            "\n\n📢 Share this with someone who needs to see it!"
        ]
        
        random_cta = random.choice(cta_options)
        enhanced_description = description + timestamp_note + random_cta
        
        # Generate unique hashtags for niche
        niche_hashtags = {
            'technology': ['#TechTrends', '#Innovation', '#TechNews', '#DigitalLife', '#TechReview'],
            'finance': ['#FinanceEducation', '#MoneyTips', '#InvestmentAdvice', '#WealthBuilding', '#FinancialFreedom'],
            'health': ['#HealthTips', '#Wellness', '#HealthyLiving', '#Fitness', '#MentalHealth'],
            'education': ['#Learning', '#Education', '#KnowledgeSharing', '#StudyTips', '#SkillBuilding'],
            'entertainment': ['#Entertainment', '#Fun', '#Trending', '#Viral', '#MustWatch'],
            'lifestyle': ['#Lifestyle', '#LifeHacks', '#Motivation', '#SelfImprovement', '#LifeGoals']
        }
        
        hashtags = niche_hashtags.get(niche, ['#Content', '#Educational', '#Informative'])
        selected_hashtags = random.sample(hashtags, min(3, len(hashtags)))
        hashtag_string = ' '.join(selected_hashtags)
        
        enhanced_description += f"\n\n{hashtag_string}"
        
        return title, enhanced_description, upload_jitter
        
    def detect_niche(self) -> str:
        """Auto-detect niche from file path or content"""
        if self.markdown_file and "niches/" in str(self.markdown_file):
            return str(self.markdown_file).split("niches/")[1].split("/")[0]
        return "default"
        
    def setup_logging(self, log_file: Optional[str] = None):
        """Configure comprehensive logging"""
        if not hasattr(self, 'logs_dir'):
            self.logs_dir = Path("logs")
            self.logs_dir.mkdir(exist_ok=True)
            
        if log_file:
            log_path = Path(log_file)
        else:
            log_path = self.logs_dir / f"render_{self.project_name}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def setup_directories(self):
        """Create required directory structure"""
        # Base directories
        self.staging_dir = Path("staging")
        self.enhanced_dir = Path("enhanced")
        self.final_dir = Path("final")
        self.logs_dir = Path("logs")
        
        # Create base directories
        for dir_path in [self.staging_dir, self.enhanced_dir, self.final_dir, self.logs_dir]:
            dir_path.mkdir(exist_ok=True)
            
        # Create niche-specific directories
        self.niche_staging = self.staging_dir / self.niche
        self.niche_enhanced = self.enhanced_dir / self.niche
        self.niche_final = self.final_dir / self.niche
        
        for niche_dir in [self.niche_staging, self.niche_enhanced, self.niche_final]:
            niche_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"📁 Directory structure created for niche: {self.niche}")
        
    def validate_environment(self):
        """Validate all required environment variables"""
        required_vars = [
            'VIDEO_RENDER_API',
            'YOUTUBE_UPLOAD_TRIGGER', 
            'TELEGRAM_ALERT_WEBHOOK',
            'GOOGLE_API_KEY',
            'ELEVENLABS_API_KEY',
            'ELEVENLABS_VOICE_ID',
            'JSON2VIDEO_KEY'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            self.logger.error(f"Missing environment variables: {missing_vars}")
            raise ValueError(f"Missing required environment variables: {missing_vars}")
            
        self.logger.info("✅ Environment validation passed")
        
    def extract_hook(self, content: str) -> str:
        """Extract viral hook from content"""
        # Look for explicit hook markers
        hook_patterns = [
            r'\[HOOK\]\s*([^\n]+)',
            r'\*\*HOOK:\*\*\s*([^\n]+)',
            r'::hook=([^\n]+)'
        ]
        
        for pattern in hook_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: use first meaningful line
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
        return lines[0] if lines else "Attention-grabbing hook needed"
        
    def parse_markdown(self, md_file: str) -> Dict:
        """Parse Markdown file for video cues and content with enhanced cue detection and variations"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Apply content variations if engine is available
            if self.variation_engine:
                content = self.variation_engine.apply_content_variations(original_content, self.niche)
                self.logger.info(f"Applied content variations for niche: {self.niche}")
            else:
                content = original_content
                self.logger.warning("Content variation engine not available, using original content")
                
            # Extract TTS cues with multiple formats
            tts_patterns = [
                r'::tts=([^\n]+)',
                r'\[TTS\]\s*([^\n]+)',
                r'\*\*TTS:\*\*\s*([^\n]+)'
            ]
            tts_matches = []
            for pattern in tts_patterns:
                tts_matches.extend(re.findall(pattern, content, re.IGNORECASE))
            
            # Extract B-roll cues with multiple formats
            broll_patterns = [
                r'::broll=([^\n]+)',
                r'\[BROLL\]\s*([^\n]+)',
                r'\*\*B-ROLL:\*\*\s*([^\n]+)',
                r'\[B-ROLL\]\s*([^\n]+)'
            ]
            broll_matches = []
            for pattern in broll_patterns:
                broll_matches.extend(re.findall(pattern, content, re.IGNORECASE))
            
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            
            # Extract title using thumbnail generator's method for consistency
            title = self.thumbnail_generator.extract_title_from_markdown(content)
            
            # Get varied title if variation engine is available
            if self.variation_engine:
                # Extract topic from original title for variation
                topic = title.replace('Understanding', '').replace('The Complete Guide to', '').strip()
                if topic:
                    varied_title = self.variation_engine.get_varied_title(topic, self.niche)
                    self.logger.info(f"Generated varied title: {varied_title}")
                    title = varied_title
            
            # Extract hook (first 3 lines or explicit hook marker)
            hook = self.extract_hook(content)
            
            # Clean content for processing
            clean_content = re.sub(r'::(?:broll|tts)=[^\n]+', '', content)
            clean_content = re.sub(r'\[(?:TTS|BROLL|B-ROLL)\][^\n]*', '', clean_content, flags=re.IGNORECASE)
            clean_content = re.sub(r'\*\*(?:TTS|B-ROLL):\*\*[^\n]*', '', clean_content, flags=re.IGNORECASE)
            clean_content = re.sub(r'\n\s*\n', '\n\n', clean_content)
            
            parsed_data = {
                'title': title,
                'content': clean_content.strip(),
                'broll_cues': broll_matches,
                'tts_cues': tts_matches,
                'hook': hook,
                'niche': self.niche,
                'timestamp': datetime.now().isoformat(),
                'original_content': original_content,
                'variations_applied': self.variation_engine is not None
            }
            
            self.logger.info(f"✅ Parsed markdown: {len(broll_matches)} b-roll cues, {len(tts_matches)} TTS cues")
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to parse markdown: {e}")
            raise
            
    def preprocess_with_ai(self, content: str) -> str:
        """Use Google AI Studio to enhance and clean content"""
        try:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                self.logger.warning("⚠️ Google AI API key not found, using raw content")
                return content
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            
            prompt = f"""
Optimize this YouTube video script for maximum engagement and $75K revenue potential:

{content}

Enhance with:
- Hook-heavy opening (first 15 seconds)
- Emotional triggers and urgency
- Clear value propositions
- Engagement retention techniques
- Strong call-to-actions

Return only the enhanced script, no explanations.
"""
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                enhanced_content = result['candidates'][0]['content']['parts'][0]['text']
                self.logger.info("✅ Content enhanced with Google AI")
                return enhanced_content
            else:
                self.logger.warning(f"⚠️ AI enhancement failed: {response.status_code}")
                return content
                
        except Exception as e:
            self.logger.warning(f"⚠️ AI preprocessing failed: {e}, using original content")
            return content
            
    def render_with_json2video(self, video_data: Dict) -> Optional[str]:
        """Primary rendering with JSON2Video API"""
        try:
            api_key = os.getenv('JSON2VIDEO_KEY')
            api_url = os.getenv('VIDEO_RENDER_API', 'https://json2video.com/api/render')
            
            # Prepare JSON2Video payload
            payload = {
                "template": "youtube_automation",
                "data": {
                    "title": video_data['title'],
                    "content": video_data['content'],
                    "broll_cues": video_data['broll_cues'],
                    "tts_voice": os.getenv('ELEVENLABS_VOICE_ID'),
                    "niche": self.niche,
                    "style": "cinematic_youtube"
                },
                "settings": {
                    "resolution": "1920x1080",
                    "fps": 30,
                    "duration": "auto",
                    "format": "mp4"
                }
            }
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            self.logger.info("🎬 Starting JSON2Video rendering...")
            response = requests.post(api_url, json=payload, headers=headers, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                video_url = result.get('video_url')
                
                if video_url:
                    # Download rendered video
                    video_response = requests.get(video_url, timeout=600)
                    output_path = f"staging/{self.niche}_json2video.mp4"
                    
                    with open(output_path, 'wb') as f:
                        f.write(video_response.content)
                        
                    self.logger.info(f"✅ JSON2Video rendering complete: {output_path}")
                    return output_path
                    
            self.logger.error(f"❌ JSON2Video failed: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ JSON2Video rendering failed: {e}")
            return None
            
    def fallback_capcut(self, video_data: Dict) -> Optional[str]:
        """Fallback rendering with CapCut CLI"""
        try:
            self.logger.info("🎞️ Falling back to CapCut CLI...")
            
            # Generate CapCut project JSON
            capcut_project = {
                "version": "1.0",
                "project": {
                    "name": f"{self.niche}_video",
                    "timeline": {
                        "tracks": [
                            {
                                "type": "video",
                                "clips": [
                                    {
                                        "source": "generated_background.mp4",
                                        "duration": 60,
                                        "effects": ["cinematic_transition", "zoom_effect"]
                                    }
                                ]
                            },
                            {
                                "type": "audio", 
                                "clips": [
                                    {
                                        "source": "tts_audio.mp3",
                                        "volume": 0.8
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
            
            # Save CapCut project
            project_path = f"staging/{self.niche}_capcut_project.json"
            with open(project_path, 'w') as f:
                json.dump(capcut_project, f, indent=2)
                
            # Call CapCut CLI fallback script
            result = subprocess.run(
                ['./capcut_fallback.sh', project_path, self.niche],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                output_path = f"enhanced/{self.niche}_capcut.mp4"
                if os.path.exists(output_path):
                    self.logger.info(f"✅ CapCut rendering complete: {output_path}")
                    return output_path
                    
            self.logger.error(f"❌ CapCut fallback failed: {result.stderr}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ CapCut fallback failed: {e}")
            return None
            
    def fallback_ffmpeg(self, video_data: Dict) -> Optional[str]:
        """Last resort: FFmpeg stitching"""
        try:
            self.logger.info("🎥 Last resort: FFmpeg stitching...")
            
            # Call FFmpeg fallback script
            result = subprocess.run(
                ['./fallback_ffmpeg.sh', self.niche, video_data['title']],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                output_path = f"final/{self.niche}/rendered.mp4"
                if os.path.exists(output_path):
                    self.logger.info(f"✅ FFmpeg fallback complete: {output_path}")
                    return output_path
                    
            self.logger.error(f"❌ FFmpeg fallback failed: {result.stderr}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ FFmpeg fallback failed: {e}")
            return None
            
    def post_process_video(self, video_path: str) -> str:
        """Apply final post-processing with FFmpeg"""
        try:
            output_path = f"final/{self.niche}/rendered.mp4"
            
            # Apply watermark, compression, and optimization
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                '-y', output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info(f"✅ Post-processing complete: {output_path}")
                return output_path
            else:
                self.logger.error(f"❌ Post-processing failed: {result.stderr}")
                return video_path
                
        except Exception as e:
            self.logger.error(f"❌ Post-processing failed: {e}")
            return video_path
            
    def trigger_upload(self, video_path: str, video_data: Dict) -> bool:
        """Trigger YouTube upload via n8n webhook with compliance data, variations, and anti-shadowban protection"""
        try:
            webhook_url = os.getenv('YOUTUBE_UPLOAD_TRIGGER')
            
            # Step 0: Vertex AI Content Moderation
            if VERTEX_AI_AVAILABLE:
                self.logger.info("🛡️ Running Vertex AI content moderation...")
                moderation_result = moderate_text(video_data['content'])
                
                if not moderation_result['safe']:
                    self.logger.error(f"❌ Content blocked by Vertex AI moderation: {moderation_result['reasoning']}")
                    self.logger.error(f"Safety score: {moderation_result['score']:.2f}, Categories: {moderation_result['categories']}")
                    
                    # Log moderation failure
                    self.log_upload_event('MODERATION_BLOCKED', f"Content blocked: {moderation_result['reasoning']}", video_data)
                    
                    # Send alert
                    alert_message = f"Content moderation BLOCKED upload\n\nReason: {moderation_result['reasoning']}\nSafety Score: {moderation_result['score']:.2f}\nCategories: {', '.join(moderation_result['categories'])}"
                    self.send_notification(alert_message, False)
                    
                    return False
                else:
                    self.logger.info(f"✅ Content passed Vertex AI moderation (score: {moderation_result['score']:.2f})")
                    video_data['moderation_score'] = moderation_result['score']
                    video_data['moderation_method'] = moderation_result['method']
            
            # Generate varied description if variation engine is available
            description = f"Educational content about {self.niche}.\n\n{video_data['content'][:500]}..."
            if self.variation_engine:
                topic = video_data.get('title', 'this topic')
                key_points = "important insights and valuable information"
                description = self.variation_engine.get_varied_description(topic, key_points)
                self.logger.info("Generated varied description for upload")
            
            # Apply anti-shadowban metadata
            enhanced_title, enhanced_description, upload_jitter = self.add_anti_shadowban_metadata(
                video_data['title'], description, self.niche
            )
            
            # Log anti-shadowban application
            self.log_upload_event('ANTI_SHADOWBAN', f'Applied metadata enhancements with {upload_jitter}s jitter', video_data)
            
            # Generate varied tags with anti-pattern measures
            base_tags = [self.niche, 'educational']
            if self.variation_engine:
                # Add some variation to tags to avoid patterns
                varied_tags = base_tags + random.sample([
                    'informative', 'learning', 'knowledge', 'insights', 'explained',
                    'guide', 'tutorial', 'facts', 'analysis', 'overview', 'tips',
                    'howto', 'beginner', 'advanced', 'complete', 'ultimate'
                ], k=min(4, 10 - len(base_tags)))
            else:
                varied_tags = base_tags + ['automation', 'ai', 'youtube']
            
            # Add upload jitter to delay
            final_upload_delay = video_data.get('upload_delay', 0) + upload_jitter
            
            payload = {
                'video_path': video_path,
                'title': enhanced_title,
                'description': enhanced_description,
                'tags': varied_tags,
                'category': '22',  # People & Blogs
                'privacy': video_data.get('privacy', 'public'),
                'upload_delay': final_upload_delay,
                'compliance_score': video_data.get('compliance_score', 1.0),
                'niche': self.niche,
                'thumbnail_path': video_data.get('thumbnail_path'),
                'timestamp': datetime.now().isoformat(),
                'variations_applied': video_data.get('variations_applied', False),
                'upload_strategy': video_data.get('upload_strategy'),
                'anti_shadowban_applied': True,
                'upload_jitter': upload_jitter
            }
            
            # Add voice style if available
            if hasattr(self, 'current_voice_style'):
                payload['voice_style'] = self.current_voice_style
            
            # Enhanced upload logging
            self.log_upload_event('UPLOAD_TRIGGER', f'Triggering upload with enhanced metadata', video_data)
            self.logger.info(f"Triggering upload for: {payload['title']}")
            self.logger.info(f"Privacy: {payload['privacy']}, Total Delay: {payload['upload_delay']}s (base: {video_data.get('upload_delay', 0)}s + jitter: {upload_jitter}s)")
            self.logger.info(f"Compliance Score: {payload['compliance_score']:.2f}")
            self.logger.info(f"Variations Applied: {payload['variations_applied']}")
            self.logger.info(f"Anti-Shadowban Applied: {payload['anti_shadowban_applied']}")
            
            # Delay webhook alert to avoid pattern detection
            webhook_delay = random.randint(30, 120)  # 30-120 seconds
            self.logger.info(f"Delaying webhook alert by {webhook_delay}s for anti-pattern protection")
            
            response = requests.post(webhook_url, json=payload, timeout=60)
            
            if response.status_code == 200:
                self.log_upload_event('UPLOAD_SUCCESS', f'Upload triggered successfully with {len(varied_tags)} tags', video_data)
                self.logger.info("✅ Upload triggered successfully")
                
                # Schedule delayed notification
                import threading
                def delayed_notification():
                    time.sleep(webhook_delay)
                    success_message = f"Video upload initiated successfully!\n\nTitle: {enhanced_title}\nPrivacy: {payload['privacy']}\nDelay: {final_upload_delay}s\nCompliance: {payload['compliance_score']:.2f}"
                    self.send_notification(success_message, True)
                
                notification_thread = threading.Thread(target=delayed_notification)
                notification_thread.daemon = True
                notification_thread.start()
                
                return True
            else:
                self.log_upload_event('UPLOAD_FAILED', f'Upload trigger failed: HTTP {response.status_code}', video_data)
                self.logger.error(f"❌ Upload trigger failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_upload_event('UPLOAD_ERROR', f'Upload trigger exception: {str(e)}', video_data)
            self.logger.error(f"❌ Upload trigger failed: {e}")
            return False
    
    def _log_compliance_issue(self, compliance_log: Dict):
        """Log compliance validation results"""
        try:
            log_file = 'logs/compliance.log'
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            with open(log_file, 'a') as f:
                f.write(f"{json.dumps(compliance_log)}\n")
                
        except Exception as e:
            self.logger.error(f"Failed to log compliance data: {e}")
            
    def send_notification(self, message: str, success: bool = True):
        """Send Telegram notification"""
        try:
            webhook_url = os.getenv('TELEGRAM_ALERT_WEBHOOK')
            
            emoji = "✅" if success else "❌"
            full_message = f"{emoji} {self.niche.upper()} Video Pipeline\n\n{message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            response = requests.get(f"{webhook_url}{full_message}", timeout=30)
            
            if response.status_code == 200:
                self.logger.info("📱 Notification sent")
            else:
                self.logger.warning(f"⚠️ Notification failed: {response.status_code}")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Notification failed: {e}")
            
    def render_video(self, md_file: str) -> bool:
        """Main rendering pipeline orchestrator"""
        start_time = time.time()
        
        try:
            self.logger.info(f"🚀 Starting video rendering pipeline for {self.niche}")
            
            # Step 1: Parse Markdown
            video_data = self.parse_markdown(md_file)
            
            # Step 1.5: Compliance validation
            compliance_log = {'timestamp': datetime.now().isoformat(), 'niche': self.niche}
            
            # Validate title
            title_validation = self.compliance_validator.validate_title(video_data['title'])
            compliance_log['title_validation'] = title_validation
            
            if not title_validation['compliant']:
                self.logger.warning(f"Title compliance issues: {title_validation['issues']}")
                video_data['title'] = title_validation['cleaned_title']
                self.logger.info(f"Title cleaned to: {video_data['title']}")
            
            # Validate content
            content_validation = self.compliance_validator.validate_content(video_data['content'])
            compliance_log['content_validation'] = content_validation
            
            if not content_validation['compliant']:
                self.logger.error(f"Content flagged for sensitive topics: {content_validation['flagged_topics']}")
                self._log_compliance_issue(compliance_log)
                if os.getenv('STRICT_COMPLIANCE', 'false').lower() == 'true':
                    raise Exception(f"Content rejected due to compliance issues: {content_validation['issues']}")
            
            # Check upload rate limit
            rate_limit = self.compliance_validator.check_upload_rate_limit()
            compliance_log['rate_limit'] = rate_limit
            
            if not rate_limit['allowed']:
                self.logger.error(f"Upload rate limit exceeded: {rate_limit['uploads_today']}/{rate_limit['limit']}")
                raise Exception(f"Daily upload limit reached ({rate_limit['uploads_today']}/{rate_limit['limit']})")
            
            # Step 2: AI Enhancement
            video_data['content'] = self.preprocess_with_ai(video_data['content'])
            
            # Step 2.5: Generate TTS Audio with Multi-Engine Fallback
            self.logger.info("🎵 Generating TTS audio...")
            audio_path = None
            if video_data.get('tts_segments'):
                # Combine all TTS segments into one text
                full_text = ' '.join([segment.get('text', '') for segment in video_data['tts_segments']])
                if full_text.strip():
                    audio_path = self.tts_engine.generate_audio(full_text, f"{self.niche}_audio")
                    if audio_path:
                        video_data['audio_path'] = audio_path
                        self.logger.info(f"✅ TTS audio generated: {audio_path}")
                    else:
                        self.logger.error("❌ All TTS engines failed")
            
            # Step 3: Primary rendering (JSON2Video)
            video_path = self.render_with_json2video(video_data)
            
            # Step 4: Fallback to CapCut if needed
            if not video_path:
                video_path = self.fallback_capcut(video_data)
                
            # Step 5: Last resort FFmpeg
            if not video_path:
                video_path = self.fallback_ffmpeg(video_data)
                
            if not video_path:
                raise Exception("All rendering methods failed")
                
            # Step 6: Post-processing
            final_video = self.post_process_video(video_path)
            
            # Step 6.5: Generate and validate thumbnail
            thumbnail_path = self.thumbnail_generator.generate_thumbnail(
                video_data['title'], 
                final_video
            )
            
            if thumbnail_path:
                # Validate thumbnail safety
                thumbnail_validation = self.compliance_validator.validate_thumbnail_safety(thumbnail_path)
                compliance_log['thumbnail_validation'] = thumbnail_validation
                
                if thumbnail_validation['compliant']:
                    video_data['thumbnail_path'] = thumbnail_path
                    self.logger.info(f"Thumbnail passed safety check: {thumbnail_validation['score']:.2f}")
                else:
                    self.logger.warning(f"Thumbnail failed safety check: {thumbnail_validation['issues']}")
                    # Remove unsafe thumbnail
                    try:
                        os.remove(thumbnail_path)
                    except:
                        pass
            
            # Step 7: Get upload strategy from variation engine
            upload_strategy = None
            if self.variation_engine:
                upload_strategy = self.variation_engine.get_upload_strategy()
                self.logger.info(f"Using varied upload strategy: {upload_strategy['description']}")
            
            # Calculate final compliance score
            video_data['compliance_score'] = min(
                title_validation['score'],
                content_validation['score'],
                thumbnail_validation.get('score', 1.0) if thumbnail_path else 1.0
            )
            
            # Validate compliance and determine upload strategy
            compliance_data = {
                'title_validation': title_validation,
                'content_validation': content_validation,
                'rate_limit': rate_limit,
                'niche': self.niche,
                'timestamp': datetime.now().isoformat(),
                'upload_strategy': upload_strategy,
                'final_score': video_data['compliance_score']
            }
            
            # Determine upload privacy and delay based on compliance and variation
            if upload_strategy and video_data['compliance_score'] >= 0.7:
                # Use varied strategy if compliance is acceptable
                upload_privacy = upload_strategy['privacy']
                upload_delay = upload_strategy['delay_hours'] * 3600  # Convert to seconds
                self.logger.info(f"Using varied upload strategy: {upload_strategy['description']} (compliance: {video_data['compliance_score']:.2f})")
            elif video_data['compliance_score'] < 0.7:
                upload_privacy = 'private'
                upload_delay = self.compliance_validator.generate_safe_upload_delay() * 2  # Double delay for low compliance
                self.logger.warning(f"Low compliance score ({video_data['compliance_score']:.2f}), overriding with private upload and extended delay")
            elif video_data['compliance_score'] < 0.85:
                upload_privacy = 'unlisted'
                upload_delay = self.compliance_validator.generate_safe_upload_delay()
                self.logger.info(f"Medium compliance score ({video_data['compliance_score']:.2f}), using unlisted upload")
            else:
                upload_privacy = os.getenv('DEFAULT_UPLOAD_PRIVACY', 'private')
                upload_delay = self.compliance_validator.generate_safe_upload_delay()
                self.logger.info(f"High compliance score ({video_data['compliance_score']:.2f}), using default upload strategy")
            
            video_data['privacy'] = upload_privacy
            video_data['upload_delay'] = upload_delay
            
            # Log compliance results
            compliance_log['final_score'] = video_data['compliance_score']
            compliance_log['upload_strategy'] = upload_strategy
            self._log_compliance_issue(compliance_log)
            
            # Step 8: Trigger upload with compliance data
            self.compliance_validator.log_upload_attempt()
            upload_success = self.trigger_upload(final_video, video_data)
            
            # Step 8: Notifications
            duration = time.time() - start_time
            
            if upload_success:
                message = f"Video rendered and uploaded successfully!\n\nTitle: {video_data['title']}\nDuration: {duration:.1f}s\nPath: {final_video}"
                self.send_notification(message, True)
                self.logger.info(f"🎉 Pipeline completed successfully in {duration:.1f}s")
                return True
            else:
                message = f"Video rendered but upload failed\n\nTitle: {video_data['title']}\nPath: {final_video}"
                self.send_notification(message, False)
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            error_message = f"Pipeline failed: {str(e)}\n\nDuration: {duration:.1f}s"
            self.send_notification(error_message, False)
            self.logger.error(f"💥 Pipeline failed: {e}")
            return False

def main():
    """Main execution function with enhanced argument parsing"""
    parser = argparse.ArgumentParser(description='AI Video Renderer - Multi-Niche Automation')
    parser.add_argument('markdown_file', help='Path to the markdown script file')
    parser.add_argument('--niche', help='Target niche (auto-detected if not specified)')
    parser.add_argument('--log-file', help='Custom log file path')
    parser.add_argument('--force-method', choices=['json2video', 'capcut', 'ffmpeg'], 
                       help='Force specific rendering method')
    parser.add_argument('--skip-upload', action='store_true', help='Skip YouTube upload')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.markdown_file):
        print(f"❌ Error: File '{args.markdown_file}' not found")
        sys.exit(1)
    
    # Auto-detect niche if not provided
    niche = args.niche
    if not niche:
        if "niches/" in args.markdown_file:
            niche = args.markdown_file.split("niches/")[1].split("/")[0]
        else:
            niche = "general"
    
    print(f"🚀 Starting AI Video Renderer")
    print(f"📄 File: {args.markdown_file}")
    print(f"🎯 Niche: {niche}")
    
    renderer = VideoRenderer(
        niche=niche, 
        markdown_file=args.markdown_file
    )
    
    if args.log_file:
        renderer.setup_logging(args.log_file)
    
    success = renderer.render_video(args.markdown_file)
    
    sys.exit(0 if success else 1)

def create_niche_folders():
    """Create the multi-niche folder structure"""
    niches = ['ai', 'crypto', 'finance', 'history', 'lifestyle', 'motivation']
    base_path = Path('scripts/niches')
    
    for niche in niches:
        niche_path = base_path / niche
        niche_path.mkdir(parents=True, exist_ok=True)
        
        # Create sample template if it doesn't exist
        template_file = niche_path / 'template.md'
        if not template_file.exists():
            template_content = f"""# {niche.title()} Video Template

[HOOK] Attention-grabbing opening for {niche} content

::tts=Welcome to our {niche} channel
::broll=Relevant {niche} footage

## Main Content

Your {niche}-specific content goes here...

::tts=Key point about {niche}
::broll=Supporting visuals

## Conclusion

::tts=Don't forget to subscribe for more {niche} content!
::broll=Subscribe button animation
"""
            template_file.write_text(template_content)
    
    print(f"✅ Created niche folders: {', '.join(niches)}")

if __name__ == "__main__":
    # Create niche folders on first run
    create_niche_folders()
    main()