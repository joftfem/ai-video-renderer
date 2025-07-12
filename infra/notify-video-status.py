#!/usr/bin/env python3
"""
Video Status Notification Script

Sends notifications about video upload status, analytics, and system health
to Discord and Telegram channels.

Features:
- Discord webhook notifications with rich embeds
- Telegram bot notifications with formatting
- Video analytics reporting
- System health status
- Error notifications with context
- Customizable notification templates

Usage:
    python3 notify-video-status.py "Video uploaded successfully" --type success
    python3 notify-video-status.py "Upload failed" --type error --details "API quota exceeded"

Environment Variables Required:
    DISCORD_WEBHOOK_URL
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Optional, List
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Missing required dependency: requests")
    print("Install with: pip3 install requests")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NotificationSender:
    """Handles sending notifications to Discord and Telegram."""
    
    def __init__(self):
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.gcp_project_id = os.getenv('GOOGLE_PROJECT_ID')
        self.bitly_access_token = os.getenv('BITLY_TOKEN')
        
        # Validate at least one notification method is configured
        if not self.discord_webhook and not (self.telegram_token and self.telegram_chat_id):
            logger.warning("No notification methods configured")
    
    def send_discord_notification(self, message: str, notification_type: str = 'info', 
                                details: Optional[str] = None, video_data: Optional[Dict] = None) -> bool:
        """Send notification to Discord using webhook."""
        if not self.discord_webhook:
            logger.debug("Discord webhook not configured")
            return False
        
        # Color mapping for different notification types
        colors = {
            'success': 0x00ff00,  # Green
            'error': 0xff0000,    # Red
            'warning': 0xffff00,  # Yellow
            'info': 0x0099ff,     # Blue
            'analytics': 0x9900ff # Purple
        }
        
        # Icon mapping
        icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'analytics': '📊'
        }
        
        embed = {
            'title': f"{icons.get(notification_type, 'ℹ️')} AI Video Renderer",
            'description': message,
            'color': colors.get(notification_type, colors['info']),
            'timestamp': datetime.utcnow().isoformat(),
            'footer': {
                'text': 'AI Video Renderer System'
            }
        }
        
        # Add details field if provided
        if details:
            embed['fields'] = [{
                'name': 'Details',
                'value': details[:1024],  # Discord field value limit
                'inline': False
            }]
        
        # Add video information if provided
        if video_data:
            fields = embed.get('fields', [])
            
            if 'title' in video_data:
                fields.append({
                    'name': '🎬 Video Title',
                    'value': video_data['title'][:1024],
                    'inline': False
                })
            
            if 'url' in video_data:
                fields.append({
                    'name': '🔗 Video URL',
                    'value': video_data['url'],
                    'inline': True
                })
            
            if 'views' in video_data:
                fields.append({
                    'name': '👀 Views',
                    'value': str(video_data['views']),
                    'inline': True
                })
            
            if 'duration' in video_data:
                fields.append({
                    'name': '⏱️ Duration',
                    'value': video_data['duration'],
                    'inline': True
                })
            
            embed['fields'] = fields
        
        payload = {
            'embeds': [embed],
            'username': 'AI Video Renderer',
            'avatar_url': 'https://cdn-icons-png.flaticon.com/512/1384/1384060.png'
        }
        
        try:
            response = requests.post(
                self.discord_webhook,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            logger.info("✅ Discord notification sent successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to send Discord notification: {e}")
            return False
    
    def send_telegram_notification(self, message: str, notification_type: str = 'info',
                                 details: Optional[str] = None, video_data: Optional[Dict] = None) -> bool:
        """Send notification to Telegram using bot API."""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.debug("Telegram credentials not configured")
            return False
        
        # Icon mapping
        icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'analytics': '📊'
        }
        
        # Build message text
        text_parts = [
            f"{icons.get(notification_type, 'ℹ️')} *AI Video Renderer*",
            f"\n{message}"
        ]
        
        if details:
            text_parts.append(f"\n\n*Details:*\n{details}")
        
        if video_data:
            text_parts.append("\n\n*Video Information:*")
            
            if 'title' in video_data:
                text_parts.append(f"🎬 *Title:* {video_data['title']}")
            
            if 'url' in video_data:
                text_parts.append(f"🔗 *URL:* {video_data['url']}")
            
            if 'views' in video_data:
                text_parts.append(f"👀 *Views:* {video_data['views']}")
            
            if 'duration' in video_data:
                text_parts.append(f"⏱️ *Duration:* {video_data['duration']}")
        
        text_parts.append(f"\n\n🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        full_message = "\n".join(text_parts)
        
        # Telegram message length limit is 4096 characters
        if len(full_message) > 4096:
            full_message = full_message[:4093] + "..."
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': full_message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info("✅ Telegram notification sent successfully")
                return True
            else:
                logger.error(f"❌ Telegram API error: {result.get('description')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to send Telegram notification: {e}")
            return False
    
    def send_notification(self, message: str, notification_type: str = 'info',
                         details: Optional[str] = None, video_data: Optional[Dict] = None) -> Dict[str, bool]:
        """Send notification to all configured platforms."""
        results = {}
        
        # Send to Discord
        if self.discord_webhook:
            results['discord'] = self.send_discord_notification(
                message, notification_type, details, video_data
            )
        
        # Send to Telegram
        if self.telegram_token and self.telegram_chat_id:
            results['telegram'] = self.send_telegram_notification(
                message, notification_type, details, video_data
            )
        
        return results
    
    def send_system_health_report(self) -> Dict[str, bool]:
        """Send a system health report."""
        try:
            # Gather system information
            import psutil
            import subprocess
            
            # Get system stats
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get Docker container status
            try:
                docker_result = subprocess.run(
                    ['docker-compose', 'ps', '--format', 'json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                docker_status = "Running" if docker_result.returncode == 0 else "Error"
            except:
                docker_status = "Unknown"
            
            health_data = {
                'cpu_usage': f"{cpu_percent}%",
                'memory_usage': f"{memory.percent}%",
                'disk_usage': f"{disk.percent}%",
                'docker_status': docker_status
            }
            
            # Determine overall health
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                health_type = 'warning'
                health_message = "⚠️ System resources running high"
            elif docker_status != "Running":
                health_type = 'error'
                health_message = "❌ Docker containers not running properly"
            else:
                health_type = 'success'
                health_message = "✅ System running normally"
            
            details = "\n".join([
                f"CPU Usage: {health_data['cpu_usage']}",
                f"Memory Usage: {health_data['memory_usage']}",
                f"Disk Usage: {health_data['disk_usage']}",
                f"Docker Status: {health_data['docker_status']}"
            ])
            
            return self.send_notification(
                health_message,
                health_type,
                details
            )
            
        except ImportError:
            logger.warning("psutil not available for system health monitoring")
            return self.send_notification(
                "System health check completed (limited info)",
                'info',
                "Install psutil for detailed system monitoring"
            )
        except Exception as e:
            logger.error(f"Error generating health report: {e}")
            return self.send_notification(
                "❌ Failed to generate system health report",
                'error',
                str(e)
            )

def parse_video_data(video_json: str) -> Optional[Dict]:
    """Parse video data from JSON string."""
    try:
        return json.loads(video_json)
    except json.JSONDecodeError:
        logger.warning("Invalid video data JSON provided")
        return None

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Send video status notifications')
    parser.add_argument('message', help='Notification message')
    parser.add_argument('--type', choices=['success', 'error', 'warning', 'info', 'analytics'],
                       default='info', help='Notification type')
    parser.add_argument('--details', help='Additional details')
    parser.add_argument('--video-data', help='Video data as JSON string')
    parser.add_argument('--health-report', action='store_true', help='Send system health report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        sender = NotificationSender()
        
        if args.health_report:
            results = sender.send_system_health_report()
        else:
            video_data = parse_video_data(args.video_data) if args.video_data else None
            results = sender.send_notification(
                args.message,
                args.type,
                args.details,
                video_data
            )
        
        # Report results
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        if success_count == total_count and total_count > 0:
            logger.info(f"✅ All notifications sent successfully ({success_count}/{total_count})")
            sys.exit(0)
        elif success_count > 0:
            logger.warning(f"⚠️ Partial success ({success_count}/{total_count})")
            sys.exit(0)
        else:
            logger.error("❌ All notifications failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()