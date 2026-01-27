# SlateOne Marketing Video - Production Guide

## 🎬 Quick Start

```bash
cd marketing-video
npm run dev
```

This opens the Remotion Studio where you can preview and edit the video in real-time.

## 📹 Video Overview

**Duration**: 30 seconds (900 frames @ 30fps)  
**Resolution**: 1920x1080 (Full HD)  
**Format**: MP4 (H.264)  
**Brand Colors**: Dark slate background with amber/gold accents
**Website**: www.slateone.studio

## 🎨 Scene Breakdown

### Scene 1: Intro (0-5 seconds)
**Purpose**: Brand introduction with impact

**Elements**:
- Animated clapperboard emoji (🎬) with spring animation
- "SlateOne" title with gold gradient
- Subtitle: "Automate Your Script Breakdown"
- Tagline: "Powered by AI • Built for Filmmakers"

**Animations**:
- Logo scales in with spring physics
- Title slides from left
- Subtitle and tagline fade in sequentially
- Animated background glow effect

### Scene 2-5: Feature Showcases (5-25 seconds)
**Purpose**: Highlight key platform capabilities

Each feature gets 5 seconds with consistent structure:

#### Feature 1: AI-Powered Breakdown (5-10s)
- Icon: 🤖
- Title: "AI-Powered Script Breakdown"
- Description: Google Gemini 2.0 integration
- Animations: Icon rotates on entrance, text slides up

#### Feature 2: Role-Specific Dashboards (10-15s)
- Icon: 👥
- Title: "Role-Specific Dashboards"
- Description: HOD-tailored views
- Animations: Consistent with Feature 1

#### Feature 3: Real-Time Collaboration (15-20s)
- Icon: 💬
- Title: "Real-Time Collaboration"
- Description: Team annotations and comments
- Animations: Consistent pattern

#### Feature 4: Professional Exports (20-25s)
- Icon: 📄
- Title: "Professional Exports"
- Description: PDF and Excel capabilities
- Animations: Consistent pattern

**Shared Feature Scene Elements**:
- Radial glow background
- Icon in bordered container with shadow
- Animated decorative line
- Progress dots at bottom
- Staggered text reveals

### Scene 6: Call-to-Action (25-30 seconds)
**Purpose**: Drive conversions

**Elements**:
- "Start Your Free Trial" headline with gold gradient
- Feature checklist with green checkmarks:
  - 14-Day Free Trial
  - No Credit Card Required
  - Full Feature Access
- Pulsing CTA button: "Get Started Now"
- Website URL: www.slateone.studio

**Animations**:
- CTA scales in with spring
- Checklist items stagger in
- Button pulses continuously
- URL fades in last

## 🎯 Rendering Commands

### Preview in Studio
```bash
npm run dev
```

### Render Full Video
```bash
npx remotion render src/Root.tsx SlateOneMarketing output.mp4
```

### Render with Custom Settings
```bash
# High quality (slower)
npx remotion render src/Root.tsx SlateOneMarketing output.mp4 --quality=100

# Fast preview (lower quality)
npx remotion render src/Root.tsx SlateOneMarketing output.mp4 --quality=50

# Specific frame range
npx remotion render src/Root.tsx SlateOneMarketing output.mp4 --frames=0-300
```

### Export as GIF
```bash
npx remotion render src/Root.tsx SlateOneMarketing output.gif
```

### Export Single Frame (Thumbnail)
```bash
# Frame 75 (middle of intro)
npx remotion still src/Root.tsx SlateOneMarketing thumbnail.png --frame=75
```

## 🎨 Customization Guide

### Adjust Timing
Edit `src/MarketingVideo.tsx`:

```tsx
// Change intro duration from 5s to 7s
<Sequence from={0} durationInFrames={210}> {/* was 150 */}
  <IntroScene title={titleText} subtitle={subtitleText} />
</Sequence>
```

### Modify Text Content
Edit scene props in `src/MarketingVideo.tsx`:

```tsx
<FeatureScene
  title="Your Custom Title"
  description="Your custom description"
  icon="🎯" // Change emoji
  delay={0}
/>
```

### Change Colors
Update inline styles in scene files:

```tsx
// Change gold to blue
background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
```

### Add New Features
1. Add new `<Sequence>` in `MarketingVideo.tsx`
2. Use `<FeatureScene>` component with new props
3. Adjust timing of subsequent scenes

## 🎵 Adding Audio

### Option 1: Background Music
```tsx
import { Audio } from 'remotion';

// In MarketingVideo.tsx
<Audio src="/path/to/music.mp3" volume={0.3} />
```

### Option 2: Sound Effects
```tsx
// In specific scenes
<Audio 
  src="/sounds/whoosh.mp3" 
  startFrom={30} 
  volume={0.5} 
/>
```

### Recommended Audio Specs
- Format: MP3 or WAV
- Length: 30 seconds
- Style: Upbeat, modern, tech-focused
- Volume: Keep at 30-50% to not overpower

## 📊 Performance Tips

### Faster Rendering
```bash
# Use more CPU cores
npx remotion render --concurrency=8

# Disable audio if not needed
npx remotion render --muted
```

### Optimize File Size
```bash
# Adjust codec settings
npx remotion render --codec=h264 --crf=23

# Lower resolution for social media
npx remotion render --height=720 --width=1280
```

## 📱 Social Media Exports

### Instagram/Facebook (Square)
```bash
npx remotion render src/Root.tsx ScripDownMarketing instagram.mp4 \
  --width=1080 --height=1080
```

### Instagram Stories (Vertical)
```bash
npx remotion render src/Root.tsx ScripDownMarketing story.mp4 \
  --width=1080 --height=1920
```

### Twitter/X (Landscape)
```bash
npx remotion render src/Root.tsx ScripDownMarketing twitter.mp4 \
  --width=1280 --height=720
```

## 🐛 Troubleshooting

### Video won't render
- Check all imports are correct
- Ensure dependencies are installed: `npm install`
- Clear cache: `rm -rf node_modules/.remotion`

### Animations look choppy
- Increase FPS: Change in `src/Root.tsx` composition
- Check CPU usage during render
- Use `--quality=100` flag

### Text is cut off
- Adjust padding in scene styles
- Check `maxWidth` properties
- Preview in Studio before rendering

## 📦 Deployment

### Upload to Website
1. Render final video: `npm run build`
2. Compress if needed (target <10MB)
3. Upload to hosting (Vimeo, YouTube, or CDN)
4. Embed on landing page

### Social Media
1. Render platform-specific versions
2. Add captions/subtitles if needed
3. Upload with optimized metadata
4. Schedule posts across platforms

## 🔄 Version Control

Current video structure is in Git. To make changes:

1. Create feature branch
2. Edit scenes in `src/scenes/`
3. Test in Remotion Studio
4. Commit changes
5. Render final version

## 📝 Notes

- All animations use spring physics for natural motion
- Color scheme matches ScripDown AI brand guidelines
- Font: Inter (system fallback included)
- Icons: Emoji for universal compatibility
- Total project size: ~50MB with dependencies

## 🚀 Next Steps

1. **Preview**: Run `npm run dev` and review in Studio
2. **Adjust**: Tweak timing, text, or animations as needed
3. **Add Audio**: Optional background music
4. **Render**: Export final MP4
5. **Deploy**: Upload to website and social media

## 📞 Support

For Remotion-specific issues:
- Docs: https://www.remotion.dev/docs
- Discord: https://remotion.dev/discord
- Examples: https://www.remotion.dev/docs/resources
