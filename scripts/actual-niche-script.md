# AI Video Renderer - Niche Script Documentation

## Overview

This document outlines the structure and implementation guidelines for niche-specific video automation scripts within the AI Video Renderer system. Each niche script should follow these patterns for consistency and maintainability.

## Script Structure

### 1. Niche Configuration

```javascript
const NICHE_CONFIG = {
  name: "Technology News",
  category: "Science & Technology",
  youtube_category_id: "28", // Science & Technology
  target_audience: "Tech enthusiasts, developers, early adopters",
  content_style: "informative, engaging, trending",
  video_length: {
    min: 60,  // seconds
    max: 300, // 5 minutes
    optimal: 180 // 3 minutes
  },
  posting_schedule: {
    frequency: "daily",
    time: "09:00", // UTC
    days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
  }
};
```

### 2. Content Generation Pipeline

#### Step 1: Topic Research
```javascript
const generateTopics = async () => {
  // Use AI services to generate trending topics
  const topics = await aiService.generateTopics({
    niche: NICHE_CONFIG.name,
    count: 10,
    trending: true,
    keywords: ["AI", "technology", "innovation", "startup"]
  });
  
  return topics.filter(topic => 
    topic.searchVolume > 1000 && 
    topic.competition < 0.7
  );
};
```

#### Step 2: Script Writing
```javascript
const generateScript = async (topic) => {
  const prompt = `
    Create an engaging ${NICHE_CONFIG.video_length.optimal}-second video script about: ${topic.title}
    
    Requirements:
    - Hook viewers in first 5 seconds
    - Include 3-5 key points
    - Add call-to-action
    - Target audience: ${NICHE_CONFIG.target_audience}
    - Style: ${NICHE_CONFIG.content_style}
    
    Format:
    [HOOK] - Opening statement
    [INTRO] - Brief introduction
    [POINT 1] - First main point
    [POINT 2] - Second main point
    [POINT 3] - Third main point
    [CTA] - Call to action
    [OUTRO] - Closing statement
  `;
  
  return await aiService.generateText(prompt);
};
```

#### Step 3: Visual Content
```javascript
const generateVisuals = async (script) => {
  const scenes = parseScriptScenes(script);
  const visuals = [];
  
  for (const scene of scenes) {
    // Generate or fetch relevant images/videos
    const visual = await mediaService.getVisual({
      query: scene.keywords,
      type: "image", // or "video"
      orientation: "horizontal",
      quality: "high"
    });
    
    visuals.push({
      scene: scene.id,
      media: visual,
      duration: scene.duration,
      transition: "fade"
    });
  }
  
  return visuals;
};
```

#### Step 4: Audio Generation
```javascript
const generateAudio = async (script) => {
  const cleanScript = removeScriptTags(script);
  
  const audioConfig = {
    text: cleanScript,
    voice_id: process.env.ELEVENLABS_VOICE_ID,
    model_id: "eleven_multilingual_v2",
    voice_settings: {
      stability: 0.5,
      similarity_boost: 0.8,
      style: 0.0,
      use_speaker_boost: true
    }
  };
  
  return await ttsService.generateSpeech(audioConfig);
};
```

### 3. Video Assembly

```javascript
const assembleVideo = async (script, visuals, audio) => {
  const videoConfig = {
    resolution: "1920x1080",
    fps: 30,
    format: "mp4",
    quality: "high",
    audio: {
      file: audio.url,
      volume: 0.8
    },
    scenes: visuals.map(visual => ({
      media: visual.media.url,
      duration: visual.duration,
      transition: visual.transition,
      effects: [
        {
          type: "text_overlay",
          text: getSceneText(script, visual.scene),
          position: "bottom",
          style: "modern"
        }
      ]
    }))
  };
  
  return await videoService.render(videoConfig);
};
```

### 4. Metadata Generation

```javascript
const generateMetadata = async (topic, script) => {
  const title = await aiService.generateTitle({
    topic: topic.title,
    style: "clickbait",
    maxLength: 60,
    includeEmojis: true
  });
  
  const description = await aiService.generateDescription({
    script: script,
    includeTimestamps: true,
    includeTags: true,
    includeLinks: true,
    maxLength: 5000
  });
  
  const tags = await aiService.generateTags({
    topic: topic.title,
    niche: NICHE_CONFIG.name,
    count: 15,
    trending: true
  });
  
  const thumbnail = await aiService.generateThumbnail({
    topic: topic.title,
    style: "youtube",
    includeText: true,
    colorScheme: "vibrant"
  });
  
  return {
    title,
    description,
    tags,
    thumbnail,
    category_id: NICHE_CONFIG.youtube_category_id,
    privacy: "public",
    made_for_kids: false,
    notify_subscribers: true
  };
};
```

## Implementation Examples

### Technology Niche
```javascript
const TECH_NICHE = {
  name: "Technology News",
  topics: [
    "AI breakthroughs",
    "Startup funding",
    "Tech product launches",
    "Cybersecurity threats",
    "Programming trends"
  ],
  keywords: ["AI", "tech", "startup", "innovation", "coding"],
  hashtags: ["#TechNews", "#AI", "#Innovation", "#Startup", "#Technology"]
};
```

### Finance Niche
```javascript
const FINANCE_NICHE = {
  name: "Personal Finance",
  topics: [
    "Investment strategies",
    "Cryptocurrency updates",
    "Budgeting tips",
    "Market analysis",
    "Financial planning"
  ],
  keywords: ["finance", "investment", "money", "crypto", "stocks"],
  hashtags: ["#Finance", "#Investment", "#Money", "#Crypto", "#Stocks"]
};
```

### Health & Wellness Niche
```javascript
const HEALTH_NICHE = {
  name: "Health & Wellness",
  topics: [
    "Fitness routines",
    "Nutrition tips",
    "Mental health",
    "Wellness trends",
    "Medical breakthroughs"
  ],
  keywords: ["health", "fitness", "nutrition", "wellness", "medical"],
  hashtags: ["#Health", "#Fitness", "#Wellness", "#Nutrition", "#MentalHealth"]
};
```

## Integration with n8n Workflows

### Workflow Trigger
```javascript
// In n8n workflow
const executeNicheScript = async (niche) => {
  const script = require(`./scripts/${niche}-script.js`);
  
  try {
    // Generate content
    const topic = await script.generateTopic();
    const videoScript = await script.generateScript(topic);
    const visuals = await script.generateVisuals(videoScript);
    const audio = await script.generateAudio(videoScript);
    
    // Assemble video
    const video = await script.assembleVideo(videoScript, visuals, audio);
    const metadata = await script.generateMetadata(topic, videoScript);
    
    // Upload to YouTube
    const uploadResult = await youtubeService.upload(video, metadata);
    
    // Send notifications
    await notificationService.send({
      type: "video_uploaded",
      niche: niche,
      video_id: uploadResult.id,
      title: metadata.title
    });
    
    return uploadResult;
  } catch (error) {
    await notificationService.send({
      type: "error",
      niche: niche,
      error: error.message
    });
    throw error;
  }
};
```

## Best Practices

### 1. Content Quality
- Always fact-check AI-generated content
- Ensure content is original and not plagiarized
- Maintain consistent brand voice across niches
- Include proper citations for factual claims

### 2. SEO Optimization
- Research trending keywords before content creation
- Optimize titles for click-through rates
- Use relevant tags and descriptions
- Include timestamps in descriptions

### 3. Compliance
- Respect YouTube's community guidelines
- Avoid copyrighted material
- Disclose AI-generated content when required
- Follow advertising and sponsorship guidelines

### 4. Performance Monitoring
- Track video performance metrics
- A/B test different content styles
- Monitor audience retention rates
- Adjust strategies based on analytics

## Error Handling

```javascript
const handleScriptError = async (error, context) => {
  console.error(`Niche script error in ${context.niche}:`, error);
  
  // Log to monitoring system
  await monitoringService.logError({
    type: "niche_script_error",
    niche: context.niche,
    error: error.message,
    stack: error.stack,
    timestamp: new Date().toISOString()
  });
  
  // Send alert
  await notificationService.sendAlert({
    level: "error",
    message: `Niche script failed for ${context.niche}: ${error.message}`,
    context: context
  });
  
  // Attempt recovery
  if (error.type === "rate_limit") {
    await delay(error.retryAfter * 1000);
    return "retry";
  }
  
  return "abort";
};
```

## Configuration Management

```javascript
// Load niche configuration from environment or config file
const loadNicheConfig = (nicheName) => {
  const configPath = `./config/niches/${nicheName}.json`;
  
  if (fs.existsSync(configPath)) {
    return JSON.parse(fs.readFileSync(configPath, 'utf8'));
  }
  
  // Fallback to default configuration
  return {
    name: nicheName,
    category: "Entertainment",
    youtube_category_id: "24",
    target_audience: "General audience",
    content_style: "informative",
    video_length: { min: 60, max: 300, optimal: 180 },
    posting_schedule: {
      frequency: "daily",
      time: "12:00",
      days: ["monday", "wednesday", "friday"]
    }
  };
};
```

## Testing

```javascript
// Test script functionality
const testNicheScript = async (nicheName) => {
  const script = require(`./scripts/${nicheName}-script.js`);
  
  console.log(`Testing ${nicheName} niche script...`);
  
  try {
    // Test topic generation
    const topics = await script.generateTopics();
    console.log(`✓ Generated ${topics.length} topics`);
    
    // Test script generation
    const videoScript = await script.generateScript(topics[0]);
    console.log(`✓ Generated script (${videoScript.length} characters)`);
    
    // Test metadata generation
    const metadata = await script.generateMetadata(topics[0], videoScript);
    console.log(`✓ Generated metadata`);
    
    console.log(`✅ ${nicheName} script test passed`);
    return true;
  } catch (error) {
    console.error(`❌ ${nicheName} script test failed:`, error.message);
    return false;
  }
};
```

---

**Note**: This is a template document. Replace this content with your actual niche-specific scripts and configurations. Each niche should have its own implementation following these patterns for consistency and maintainability.