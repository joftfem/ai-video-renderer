#!/usr/bin/env python3
"""
Content Variation Engine
Randomizes content templates, hooks, and structures to avoid YouTube pattern detection
"""

import random
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

class ContentVariationEngine:
    """Engine for creating varied content to avoid pattern detection"""
    
    def __init__(self, config_file: str = 'config/variation_templates.json'):
        self.config_file = config_file
        self.templates = self.load_templates()
        self.used_patterns = self.load_usage_history()
    
    def load_templates(self) -> Dict[str, Any]:
        """Load variation templates from config file"""
        default_templates = {
            "intro_hooks": [
                "Did you know that {topic}?",
                "Here's something interesting about {topic}.",
                "Let's explore {topic} together.",
                "Today we're diving into {topic}.",
                "You might be surprised to learn about {topic}.",
                "Let's talk about {topic}.",
                "Have you ever wondered about {topic}?",
                "Here's what you need to know about {topic}."
            ],
            "transition_phrases": [
                "Moving on to our next point...",
                "Now, let's consider...",
                "Another important aspect is...",
                "It's also worth noting that...",
                "Additionally, we should mention...",
                "Furthermore...",
                "On a related note...",
                "This brings us to..."
            ],
            "conclusion_styles": [
                "To wrap up, {summary}.",
                "In conclusion, {summary}.",
                "So there you have it - {summary}.",
                "That's the key takeaway: {summary}.",
                "Remember, {summary}.",
                "The bottom line is {summary}.",
                "What we've learned is {summary}."
            ],
            "voice_styles": [
                {"name": "professional", "speed": 1.0, "pitch": 0.0, "emphasis": "moderate"},
                {"name": "conversational", "speed": 1.1, "pitch": 0.1, "emphasis": "light"},
                {"name": "energetic", "speed": 1.2, "pitch": 0.2, "emphasis": "strong"},
                {"name": "calm", "speed": 0.9, "pitch": -0.1, "emphasis": "subtle"},
                {"name": "authoritative", "speed": 0.95, "pitch": -0.05, "emphasis": "moderate"}
            ],
            "structure_templates": [
                ["intro", "main_point_1", "main_point_2", "main_point_3", "conclusion"],
                ["hook", "context", "explanation", "examples", "summary"],
                ["question", "answer", "details", "implications", "takeaway"],
                ["intro", "problem", "solution", "benefits", "conclusion"],
                ["opening", "background", "key_points", "analysis", "wrap_up"]
            ],
            "title_variations": {
                "tech": [
                    "{topic}: What You Need to Know",
                    "Understanding {topic} in Simple Terms",
                    "The Complete Guide to {topic}",
                    "{topic} Explained Simply",
                    "Everything About {topic}"
                ],
                "finance": [
                    "{topic}: A Beginner's Guide",
                    "Understanding {topic} Basics",
                    "{topic} Made Simple",
                    "The Truth About {topic}",
                    "{topic}: Key Insights"
                ],
                "health": [
                    "{topic}: What Science Says",
                    "The Facts About {topic}",
                    "Understanding {topic} Better",
                    "{topic}: Evidence-Based Insights",
                    "What You Should Know About {topic}"
                ],
                "general": [
                    "{topic}: An Overview",
                    "Exploring {topic}",
                    "The Story of {topic}",
                    "{topic}: Key Points",
                    "Understanding {topic}"
                ]
            },
            "description_templates": [
                "In this video, we explore {topic} and discuss {key_points}. {call_to_action}",
                "Learn about {topic} as we cover {key_points}. {call_to_action}",
                "Today's topic is {topic}. We'll examine {key_points}. {call_to_action}",
                "Join us as we dive into {topic} and explore {key_points}. {call_to_action}",
                "This video covers {topic}, including {key_points}. {call_to_action}"
            ],
            "call_to_actions": [
                "Let us know your thoughts in the comments below!",
                "What's your experience with this topic? Share in the comments!",
                "Thanks for watching! Don't forget to subscribe for more content.",
                "If you found this helpful, please give it a thumbs up!",
                "Subscribe for more educational content like this!"
            ]
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_templates = json.load(f)
                    # Merge with defaults
                    for key, value in default_templates.items():
                        if key not in loaded_templates:
                            loaded_templates[key] = value
                    return loaded_templates
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        
        # Save default templates
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(default_templates, f, indent=2)
        
        return default_templates
    
    def load_usage_history(self) -> Dict[str, List[str]]:
        """Load history of used patterns to avoid repetition"""
        history_file = 'logs/variation_history.json'
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        return {"used_intros": [], "used_structures": [], "used_voices": []}
    
    def save_usage_history(self):
        """Save usage history to prevent repetition"""
        history_file = 'logs/variation_history.json'
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        # Keep only last 50 entries to prevent file bloat
        for key in self.used_patterns:
            if len(self.used_patterns[key]) > 50:
                self.used_patterns[key] = self.used_patterns[key][-50:]
        
        with open(history_file, 'w') as f:
            json.dump(self.used_patterns, f, indent=2)
    
    def get_varied_intro(self, topic: str, niche: str = "general") -> str:
        """Get a varied intro hook that hasn't been used recently"""
        available_intros = [intro for intro in self.templates["intro_hooks"] 
                           if intro not in self.used_patterns.get("used_intros", [])[-10:]]
        
        if not available_intros:
            available_intros = self.templates["intro_hooks"]
        
        selected_intro = random.choice(available_intros).format(topic=topic)
        
        # Track usage
        if "used_intros" not in self.used_patterns:
            self.used_patterns["used_intros"] = []
        self.used_patterns["used_intros"].append(selected_intro)
        
        return selected_intro
    
    def get_varied_structure(self) -> List[str]:
        """Get a content structure that hasn't been used recently"""
        available_structures = [str(struct) for struct in self.templates["structure_templates"] 
                               if str(struct) not in self.used_patterns.get("used_structures", [])[-5:]]
        
        if not available_structures:
            available_structures = [str(struct) for struct in self.templates["structure_templates"]]
        
        selected_structure = random.choice(available_structures)
        structure_list = eval(selected_structure)  # Convert string back to list
        
        # Track usage
        if "used_structures" not in self.used_patterns:
            self.used_patterns["used_structures"] = []
        self.used_patterns["used_structures"].append(selected_structure)
        
        return structure_list
    
    def get_varied_voice_style(self) -> Dict[str, Any]:
        """Get a voice style that hasn't been used recently"""
        available_voices = [voice for voice in self.templates["voice_styles"] 
                           if voice["name"] not in self.used_patterns.get("used_voices", [])[-3:]]
        
        if not available_voices:
            available_voices = self.templates["voice_styles"]
        
        selected_voice = random.choice(available_voices)
        
        # Track usage
        if "used_voices" not in self.used_patterns:
            self.used_patterns["used_voices"] = []
        self.used_patterns["used_voices"].append(selected_voice["name"])
        
        return selected_voice
    
    def get_varied_title(self, topic: str, niche: str = "general") -> str:
        """Generate a varied title for the given topic and niche"""
        niche_templates = self.templates["title_variations"].get(niche, 
                                                                self.templates["title_variations"]["general"])
        
        template = random.choice(niche_templates)
        return template.format(topic=topic)
    
    def get_varied_description(self, topic: str, key_points: str) -> str:
        """Generate a varied description"""
        template = random.choice(self.templates["description_templates"])
        call_to_action = random.choice(self.templates["call_to_actions"])
        
        return template.format(
            topic=topic,
            key_points=key_points,
            call_to_action=call_to_action
        )
    
    def get_transition_phrase(self) -> str:
        """Get a random transition phrase"""
        return random.choice(self.templates["transition_phrases"])
    
    def get_conclusion_style(self, summary: str) -> str:
        """Get a varied conclusion"""
        template = random.choice(self.templates["conclusion_styles"])
        return template.format(summary=summary)
    
    def randomize_timing(self, base_delay: int = 43200) -> int:  # 12 hours default
        """Randomize upload timing to avoid patterns"""
        # Add random variation of ±25% to base delay
        variation = int(base_delay * 0.25)
        return base_delay + random.randint(-variation, variation)
    
    def vary_content_structure(self, content: str, niche: str = "general") -> Dict[str, Any]:
        """Apply comprehensive variation to content structure"""
        # Extract topic from content (simple extraction)
        lines = content.split('\n')
        topic = "this topic"  # Default fallback
        
        # Try to extract topic from first meaningful line
        for line in lines[:5]:
            if line.strip() and len(line.strip()) > 10:
                # Simple topic extraction - take first few words
                words = line.strip().split()[:3]
                if words:
                    topic = ' '.join(words).rstrip('.,!?:')
                break
        
        # Generate varied elements
        intro = self.get_varied_intro(topic, niche)
        structure = self.get_varied_structure()
        voice_style = self.get_varied_voice_style()
        title = self.get_varied_title(topic, niche)
        description = self.get_varied_description(topic, "key insights and important information")
        upload_delay = self.randomize_timing()
        
        # Save usage history
        self.save_usage_history()
        
        return {
            "intro_hook": intro,
            "content_structure": structure,
            "voice_style": voice_style,
            "title": title,
            "description": description,
            "upload_delay_seconds": upload_delay,
            "transition_phrases": [self.get_transition_phrase() for _ in range(3)],
            "conclusion": self.get_conclusion_style("these are the key points to remember"),
            "variation_timestamp": datetime.now().isoformat()
        }
    
    def apply_content_variations(self, markdown_content: str, niche: str = "general") -> str:
        """Apply variations directly to markdown content"""
        variations = self.vary_content_structure(markdown_content, niche)
        
        # Apply intro variation
        lines = markdown_content.split('\n')
        if lines:
            # Replace or enhance the first content line
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#'):
                    lines[i] = f"{variations['intro_hook']} {line.strip()}"
                    break
        
        # Add transition phrases at logical breaks
        enhanced_lines = []
        transition_count = 0
        
        for i, line in enumerate(lines):
            enhanced_lines.append(line)
            
            # Add transitions after paragraphs (empty lines)
            if (line.strip() == '' and i < len(lines) - 1 and 
                lines[i + 1].strip() != '' and not lines[i + 1].startswith('#') and
                transition_count < len(variations['transition_phrases'])):
                
                enhanced_lines.append(variations['transition_phrases'][transition_count])
                transition_count += 1
        
        # Add conclusion
        if enhanced_lines and enhanced_lines[-1].strip():
            enhanced_lines.append('')
            enhanced_lines.append(variations['conclusion'])
        
        return '\n'.join(enhanced_lines)
    
    def get_upload_strategy(self) -> Dict[str, Any]:
        """Get randomized upload strategy to avoid patterns"""
        strategies = [
            {"privacy": "private", "delay_hours": 12, "description": "Private with 12h delay"},
            {"privacy": "private", "delay_hours": 8, "description": "Private with 8h delay"},
            {"privacy": "private", "delay_hours": 16, "description": "Private with 16h delay"},
            {"privacy": "unlisted", "delay_hours": 4, "description": "Unlisted with 4h delay"},
            {"privacy": "unlisted", "delay_hours": 6, "description": "Unlisted with 6h delay"}
        ]
        
        base_strategy = random.choice(strategies)
        
        # Add random variation to delay
        delay_variation = random.randint(-2, 2)  # ±2 hours
        base_strategy["delay_hours"] = max(1, base_strategy["delay_hours"] + delay_variation)
        
        return base_strategy

def main():
    """Test the content variation engine"""
    engine = ContentVariationEngine()
    
    # Test content
    test_content = """
# Understanding Artificial Intelligence

Artificial Intelligence is transforming our world.

Machine learning algorithms can process vast amounts of data.

Deep learning networks mimic human brain functions.

AI applications are found in healthcare, finance, and transportation.

The future of AI holds great promise and challenges.
"""
    
    print("🔄 CONTENT VARIATION ENGINE TEST")
    print("=" * 40)
    
    # Generate variations
    variations = engine.vary_content_structure(test_content, "tech")
    
    print(f"📝 Original Title: Understanding Artificial Intelligence")
    print(f"🎯 Varied Title: {variations['title']}")
    print(f"🎤 Voice Style: {variations['voice_style']['name']}")
    print(f"📋 Structure: {' → '.join(variations['content_structure'])}")
    print(f"⏰ Upload Delay: {variations['upload_delay_seconds'] // 3600} hours")
    print(f"📄 Description: {variations['description'][:100]}...")
    
    # Apply variations to content
    varied_content = engine.apply_content_variations(test_content, "tech")
    print(f"\n📝 VARIED CONTENT:")
    print("-" * 30)
    print(varied_content[:300] + "...")
    
    # Test upload strategy
    strategy = engine.get_upload_strategy()
    print(f"\n📤 UPLOAD STRATEGY:")
    print(f"   Privacy: {strategy['privacy']}")
    print(f"   Delay: {strategy['delay_hours']} hours")
    print(f"   Description: {strategy['description']}")

if __name__ == '__main__':
    main()