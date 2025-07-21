#!/usr/bin/env python3
"""
Trend to Markdown Generator
Uses Google AI Studio to generate viral hooks and content from trending topics
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.n8n')

# Import Vertex AI handler
try:
    from utils.vertex_handler import summarize_text
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    print("[WARNING] Vertex AI handler not available for trend_to_md.py")

class TrendToMarkdown:
    def __init__(self, niche: str = "general"):
        self.niche = niche
        self.google_ai_key = os.getenv('GOOGLE_AI_API_KEY')
        self.newsapi_key = os.getenv('NEWSAPI_KEY')
        self.gnews_key = os.getenv('GNEWS_KEY')
        
        if not self.google_ai_key:
            raise ValueError("GOOGLE_AI_API_KEY not found in environment")
    
    def get_trending_topics(self, niche: str) -> List[Dict]:
        """Fetch trending topics for the specified niche"""
        topics = []
        
        # Try NewsAPI first
        if self.newsapi_key:
            try:
                url = f"https://newsapi.org/v2/everything"
                params = {
                    'q': niche,
                    'sortBy': 'popularity',
                    'pageSize': 5,
                    'apiKey': self.newsapi_key
                }
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for article in data.get('articles', []):
                        topics.append({
                            'title': article['title'],
                            'description': article['description'],
                            'source': 'NewsAPI'
                        })
            except Exception as e:
                print(f"NewsAPI error: {e}")
        
        # Try GNews as fallback
        if not topics and self.gnews_key:
            try:
                url = f"https://gnews.io/api/v4/search"
                params = {
                    'q': niche,
                    'lang': 'en',
                    'country': 'us',
                    'max': 5,
                    'apikey': self.gnews_key
                }
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for article in data.get('articles', []):
                        topics.append({
                            'title': article['title'],
                            'description': article['description'],
                            'source': 'GNews'
                        })
            except Exception as e:
                print(f"GNews error: {e}")
        
        return topics
    
    def generate_viral_hook(self, title: str, description: str) -> str:
        """Generate a viral 3-second hook using Google AI Studio"""
        prompt = f"""
Create a viral 3-second hook for a YouTube video about: {title}

Description: {description}
Niche: {self.niche}

Requirements:
- Must grab attention in first 3 seconds
- Use psychological triggers (curiosity, fear of missing out, controversy)
- Keep it under 15 words
- Make it clickable and shareable
- Include emotional words

Examples of viral hooks:
- "This {self.niche} secret will blow your mind..."
- "Nobody talks about this {self.niche} truth"
- "I wish I knew this {self.niche} hack earlier"

Generate only the hook text, no explanations:
"""
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.google_ai_key}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.9,
                    "topK": 1,
                    "topP": 1,
                    "maxOutputTokens": 50
                }
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                hook = data['candidates'][0]['content']['parts'][0]['text'].strip()
                return hook.replace('"', '').replace('\n', ' ')
            else:
                print(f"Google AI API error: {response.status_code}")
                return f"This {self.niche} discovery will change everything"
                
        except Exception as e:
            print(f"Hook generation error: {e}")
            return f"You won't believe this {self.niche} secret"
    
    def generate_content_outline(self, title: str, description: str, hook: str) -> str:
        """Generate full content outline using Google AI Studio"""
        prompt = f"""
Create a detailed YouTube video script outline for:

Title: {title}
Description: {description}
Hook: {hook}
Niche: {self.niche}
Target Duration: 8-12 minutes

Structure the script with:
1. Hook (already provided)
2. Introduction (30 seconds)
3. Main content (3-4 key points, 6-8 minutes)
4. Call to action (30 seconds)

Include TTS and B-roll cues using this format:
::tts=Text to be spoken
::broll=Visual description

Make it engaging, informative, and optimized for retention.
"""
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.google_ai_key}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 1,
                    "topP": 1,
                    "maxOutputTokens": 2000
                }
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                print(f"Google AI API error: {response.status_code}")
                # Try Vertex AI as fallback
                if VERTEX_AI_AVAILABLE:
                    print("🔄 Attempting Vertex AI fallback for content generation...")
                    try:
                        vertex_content = summarize_text(f"Create a YouTube script outline for: {title}. {description}. Hook: {hook}")
                        if vertex_content:
                            print("✅ Vertex AI content generation successful")
                            # Log Vertex usage
                            self._log_vertex_usage("content_generation", "success")
                            return vertex_content
                    except Exception as vertex_e:
                        print(f"❌ Vertex AI fallback failed: {vertex_e}")
                        self._log_vertex_usage("content_generation", "failed")
                return self.generate_fallback_content(title, hook)
                
        except Exception as e:
            print(f"Content generation error: {e}")
            # Try Vertex AI as fallback
            if VERTEX_AI_AVAILABLE:
                print("🔄 Attempting Vertex AI fallback for content generation...")
                try:
                    vertex_content = summarize_text(f"Create a YouTube script outline for: {title}. {description}. Hook: {hook}")
                    if vertex_content:
                        print("✅ Vertex AI content generation successful")
                        self._log_vertex_usage("content_generation", "success")
                        return vertex_content
                except Exception as vertex_e:
                    print(f"❌ Vertex AI fallback failed: {vertex_e}")
                    self._log_vertex_usage("content_generation", "failed")
            return self.generate_fallback_content(title, hook)
    
    def _log_vertex_usage(self, operation: str, status: str) -> None:
        """Log Vertex AI usage to logs/vertex_usage.log"""
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            log_file = log_dir / "vertex_usage.log"
            timestamp = datetime.now().isoformat()
            
            log_entry = f"{timestamp} | trend_to_md.py | {operation} | {status} | niche={self.niche}\n"
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
                
        except Exception as e:
            print(f"[WARNING] Failed to log Vertex usage: {e}")
    
    def generate_fallback_content(self, title: str, hook: str) -> str:
        """Generate fallback content when AI fails"""
        return f"""# {title}

[HOOK] {hook}

::tts=Welcome back to our {self.niche} channel
::broll=Channel intro animation

## Introduction

::tts=Today we're diving deep into {title.lower()}
::broll=Relevant {self.niche} footage

## Main Content

### Key Point 1
::tts=First, let's understand the basics
::broll=Explanatory graphics

### Key Point 2
::tts=Here's what most people don't know
::broll=Supporting visuals

### Key Point 3
::tts=This is the game-changer
::broll=Dramatic reveal footage

## Conclusion

::tts=If you found this valuable, smash that like button and subscribe for more {self.niche} content
::broll=Subscribe button animation

::tts=Let me know your thoughts in the comments below
::broll=Comments section highlight
"""
    
    def create_markdown_file(self, content: str, title: str) -> str:
        """Create markdown file with timestamp"""
        # Create niche directory
        niche_dir = Path(f"scripts/niches/{self.niche}")
        niche_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
        
        filename = f"video-{timestamp}_{safe_title}.md"
        filepath = niche_dir / filename
        
        # Write content to file
        filepath.write_text(content, encoding='utf-8')
        
        print(f"✅ Created: {filepath}")
        return str(filepath)
    
    def generate_from_trend(self, topic_index: int = 0) -> str:
        """Generate markdown from trending topic"""
        print(f"🔍 Fetching trending topics for: {self.niche}")
        topics = self.get_trending_topics(self.niche)
        
        if not topics:
            print("❌ No trending topics found. Using fallback.")
            title = f"Latest {self.niche.title()} Insights You Need to Know"
            description = f"Comprehensive guide to {self.niche} trends and strategies"
        else:
            if topic_index >= len(topics):
                topic_index = 0
            
            topic = topics[topic_index]
            title = topic['title']
            description = topic['description'] or title
            print(f"📰 Selected topic: {title}")
        
        print("🎯 Generating viral hook...")
        hook = self.generate_viral_hook(title, description)
        print(f"✨ Hook: {hook}")
        
        print("📝 Generating content outline...")
        content = self.generate_content_outline(title, description, hook)
        
        # Create the markdown file
        filepath = self.create_markdown_file(content, title)
        
        return filepath

def main():
    parser = argparse.ArgumentParser(description='Generate viral video scripts from trending topics')
    parser.add_argument('--niche', default='general', help='Target niche')
    parser.add_argument('--topic-index', type=int, default=0, help='Topic index to use (0-4)')
    parser.add_argument('--list-topics', action='store_true', help='List available topics')
    
    args = parser.parse_args()
    
    try:
        generator = TrendToMarkdown(args.niche)
        
        if args.list_topics:
            topics = generator.get_trending_topics(args.niche)
            print(f"\n📰 Trending topics for {args.niche}:")
            for i, topic in enumerate(topics):
                print(f"{i}: {topic['title']} ({topic['source']})")
            return
        
        filepath = generator.generate_from_trend(args.topic_index)
        print(f"\n🎬 Ready to render: python scripts/render.py {filepath}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()