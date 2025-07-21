#!/usr/bin/env python3
"""
YouTube Compliance Monitor
Analyzes compliance logs and provides insights for content optimization
"""

import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any
import argparse

class ComplianceMonitor:
    """Monitor and analyze YouTube compliance metrics"""
    
    def __init__(self, log_file: str = 'logs/compliance.log'):
        self.log_file = log_file
        self.upload_log = 'logs/upload_history.log'
    
    def load_compliance_data(self, days: int = 30) -> List[Dict]:
        """Load compliance data from the last N days"""
        if not os.path.exists(self.log_file):
            return []
        
        cutoff_date = datetime.now() - timedelta(days=days)
        compliance_data = []
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line.strip())
                            log_date = datetime.fromisoformat(data['timestamp'])
                            if log_date >= cutoff_date:
                                compliance_data.append(data)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue
        except FileNotFoundError:
            pass
        
        return compliance_data
    
    def analyze_title_compliance(self, data: List[Dict]) -> Dict:
        """Analyze title compliance patterns"""
        total_titles = 0
        compliant_titles = 0
        common_issues = defaultdict(int)
        niche_scores = defaultdict(list)
        
        for entry in data:
            if 'title_validation' in entry:
                total_titles += 1
                title_val = entry['title_validation']
                
                if title_val.get('compliant', False):
                    compliant_titles += 1
                
                # Track issues
                for issue in title_val.get('issues', []):
                    common_issues[issue] += 1
                
                # Track niche performance
                niche = entry.get('niche', 'unknown')
                niche_scores[niche].append(title_val.get('score', 0))
        
        # Calculate niche averages
        niche_averages = {}
        for niche, scores in niche_scores.items():
            niche_averages[niche] = sum(scores) / len(scores) if scores else 0
        
        return {
            'total_titles': total_titles,
            'compliance_rate': compliant_titles / total_titles if total_titles > 0 else 0,
            'common_issues': dict(common_issues),
            'niche_performance': niche_averages
        }
    
    def analyze_content_compliance(self, data: List[Dict]) -> Dict:
        """Analyze content compliance patterns"""
        total_content = 0
        compliant_content = 0
        flagged_topics = defaultdict(int)
        niche_flags = defaultdict(int)
        
        for entry in data:
            if 'content_validation' in entry:
                total_content += 1
                content_val = entry['content_validation']
                
                if content_val.get('compliant', False):
                    compliant_content += 1
                
                # Track flagged topics
                for topic in content_val.get('flagged_topics', []):
                    flagged_topics[topic] += 1
                    niche_flags[entry.get('niche', 'unknown')] += 1
        
        return {
            'total_content': total_content,
            'compliance_rate': compliant_content / total_content if total_content > 0 else 0,
            'flagged_topics': dict(flagged_topics),
            'niche_flags': dict(niche_flags)
        }
    
    def analyze_thumbnail_safety(self, data: List[Dict]) -> Dict:
        """Analyze thumbnail safety patterns"""
        total_thumbnails = 0
        safe_thumbnails = 0
        safety_issues = defaultdict(int)
        
        for entry in data:
            if 'thumbnail_validation' in entry:
                total_thumbnails += 1
                thumb_val = entry['thumbnail_validation']
                
                if thumb_val.get('compliant', False):
                    safe_thumbnails += 1
                
                # Track safety issues
                for issue in thumb_val.get('issues', []):
                    safety_issues[issue] += 1
        
        return {
            'total_thumbnails': total_thumbnails,
            'safety_rate': safe_thumbnails / total_thumbnails if total_thumbnails > 0 else 0,
            'common_issues': dict(safety_issues)
        }
    
    def analyze_upload_patterns(self, days: int = 30) -> Dict:
        """Analyze upload timing and frequency patterns"""
        if not os.path.exists(self.upload_log):
            return {'total_uploads': 0, 'daily_average': 0, 'peak_hours': {}}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        uploads = []
        hourly_uploads = defaultdict(int)
        daily_uploads = defaultdict(int)
        
        try:
            with open(self.upload_log, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            upload_time = datetime.fromisoformat(line.strip())
                            if upload_time >= cutoff_date:
                                uploads.append(upload_time)
                                hourly_uploads[upload_time.hour] += 1
                                daily_uploads[upload_time.date()] += 1
                        except ValueError:
                            continue
        except FileNotFoundError:
            pass
        
        return {
            'total_uploads': len(uploads),
            'daily_average': len(uploads) / days if days > 0 else 0,
            'peak_hours': dict(sorted(hourly_uploads.items(), key=lambda x: x[1], reverse=True)[:5]),
            'daily_distribution': len(daily_uploads)
        }
    
    def generate_report(self, days: int = 30) -> str:
        """Generate comprehensive compliance report"""
        data = self.load_compliance_data(days)
        
        if not data:
            return f"No compliance data found for the last {days} days."
        
        title_analysis = self.analyze_title_compliance(data)
        content_analysis = self.analyze_content_compliance(data)
        thumbnail_analysis = self.analyze_thumbnail_safety(data)
        upload_analysis = self.analyze_upload_patterns(days)
        
        report = f"""
🔍 YOUTUBE COMPLIANCE REPORT ({days} days)
{'='*50}

📊 OVERVIEW
- Total Compliance Checks: {len(data)}
- Average Compliance Score: {sum(entry.get('final_score', 0) for entry in data) / len(data):.2f}
- Total Uploads: {upload_analysis['total_uploads']}
- Daily Upload Average: {upload_analysis['daily_average']:.1f}

📝 TITLE COMPLIANCE
- Total Titles Checked: {title_analysis['total_titles']}
- Compliance Rate: {title_analysis['compliance_rate']:.1%}
- Top Issues:
"""
        
        for issue, count in sorted(title_analysis['common_issues'].items(), key=lambda x: x[1], reverse=True)[:3]:
            report += f"  • {issue}: {count} times\n"
        
        report += f"""
- Niche Performance:
"""
        for niche, score in sorted(title_analysis['niche_performance'].items(), key=lambda x: x[1], reverse=True):
            report += f"  • {niche}: {score:.2f}\n"
        
        report += f"""

📄 CONTENT COMPLIANCE
- Total Content Checked: {content_analysis['total_content']}
- Compliance Rate: {content_analysis['compliance_rate']:.1%}
- Flagged Topics:
"""
        
        for topic, count in sorted(content_analysis['flagged_topics'].items(), key=lambda x: x[1], reverse=True):
            report += f"  • {topic}: {count} times\n"
        
        report += f"""

🖼️ THUMBNAIL SAFETY
- Total Thumbnails Checked: {thumbnail_analysis['total_thumbnails']}
- Safety Rate: {thumbnail_analysis['safety_rate']:.1%}
- Common Issues:
"""
        
        for issue, count in sorted(thumbnail_analysis['common_issues'].items(), key=lambda x: x[1], reverse=True):
            report += f"  • {issue}: {count} times\n"
        
        report += f"""

⏰ UPLOAD PATTERNS
- Peak Upload Hours:
"""
        
        for hour, count in list(upload_analysis['peak_hours'].items())[:3]:
            report += f"  • {hour:02d}:00 - {count} uploads\n"
        
        report += f"""

💡 RECOMMENDATIONS
"""
        
        # Generate recommendations based on analysis
        recommendations = []
        
        if title_analysis['compliance_rate'] < 0.8:
            recommendations.append("• Improve title compliance by avoiding spam keywords and excessive caps")
        
        if content_analysis['compliance_rate'] < 0.9:
            recommendations.append("• Review content for sensitive topics before processing")
        
        if thumbnail_analysis['safety_rate'] < 0.95:
            recommendations.append("• Enhance thumbnail safety checks and prompt filtering")
        
        if upload_analysis['daily_average'] > 2:
            recommendations.append("• Consider reducing upload frequency to avoid rate limiting")
        
        if not recommendations:
            recommendations.append("• Compliance metrics look good! Continue current practices.")
        
        for rec in recommendations:
            report += f"{rec}\n"
        
        return report
    
    def get_niche_insights(self, niche: str, days: int = 30) -> str:
        """Get compliance insights for a specific niche"""
        data = self.load_compliance_data(days)
        niche_data = [entry for entry in data if entry.get('niche') == niche]
        
        if not niche_data:
            return f"No compliance data found for niche '{niche}' in the last {days} days."
        
        title_scores = [entry['title_validation']['score'] for entry in niche_data if 'title_validation' in entry]
        content_scores = [entry['content_validation']['score'] for entry in niche_data if 'content_validation' in entry]
        
        avg_title_score = sum(title_scores) / len(title_scores) if title_scores else 0
        avg_content_score = sum(content_scores) / len(content_scores) if content_scores else 0
        
        return f"""
🎯 NICHE INSIGHTS: {niche.upper()}
{'='*30}

📊 Performance Metrics:
- Total Checks: {len(niche_data)}
- Average Title Score: {avg_title_score:.2f}
- Average Content Score: {avg_content_score:.2f}
- Overall Compliance: {(avg_title_score + avg_content_score) / 2:.2f}

📈 Trend: {'Improving' if avg_title_score > 0.8 else 'Needs Attention'}
"""

def main():
    parser = argparse.ArgumentParser(description='YouTube Compliance Monitor')
    parser.add_argument('--days', type=int, default=30, help='Number of days to analyze')
    parser.add_argument('--niche', type=str, help='Analyze specific niche')
    parser.add_argument('--report', action='store_true', help='Generate full report')
    
    args = parser.parse_args()
    
    monitor = ComplianceMonitor()
    
    if args.niche:
        print(monitor.get_niche_insights(args.niche, args.days))
    elif args.report:
        print(monitor.generate_report(args.days))
    else:
        # Quick summary
        data = monitor.load_compliance_data(args.days)
        if data:
            avg_score = sum(entry.get('final_score', 0) for entry in data) / len(data)
            print(f"📊 Quick Summary ({args.days} days):")
            print(f"   Total Checks: {len(data)}")
            print(f"   Average Compliance Score: {avg_score:.2f}")
            print(f"   Status: {'✅ Good' if avg_score > 0.8 else '⚠️ Needs Attention'}")
            print(f"\nRun with --report for detailed analysis")
        else:
            print(f"No compliance data found for the last {args.days} days.")

if __name__ == '__main__':
    main()