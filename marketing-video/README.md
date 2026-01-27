# SlateOne Marketing Video

A professional marketing video created with Remotion showcasing the SlateOne platform.

## Video Structure (30 seconds @ 30fps = 900 frames)

### 1. Intro Scene (0-5s)
- Animated logo entrance
- Title: "SlateOne"
- Subtitle: "Automate Your Script Breakdown"
- Tagline: "Powered by AI • Built for Filmmakers"

### 2. Feature Showcases (5-25s)
Each feature gets 5 seconds:

- **AI-Powered Breakdown** (5-10s)
  - Icon: 🤖
  - Highlights Google Gemini 2.0 integration

- **Role-Specific Dashboards** (10-15s)
  - Icon: 👥
  - Showcases HOD-tailored views

- **Real-Time Collaboration** (15-20s)
  - Icon: 💬
  - Team features and annotations

- **Professional Exports** (20-25s)
  - Icon: 📄
  - PDF and Excel export capabilities

### 3. Call-to-Action (25-30s)
- "Start Your Free Trial"
- Feature checklist (14-day trial, no credit card, full access)
- Animated CTA button
- Website URL: www.slateone.studio

## Brand Styling

Matches SlateOne's design system:
- **Background**: Dark slate (#0f172a, #1e293b)
- **Primary**: Amber/Gold gradient (#fbbf24, #f59e0b)
- **Text**: Light slate (#f1f5f9, #94a3b8)
- **Font**: Inter

## Setup & Usage

```bash
# Install dependencies
npm install

# Start Remotion Studio (preview & edit)
npm run dev

# Render video
npm run build
```

## Rendering Options

```bash
# Render as MP4
npx remotion render src/Root.tsx SlateOneMarketing output.mp4

# Render as GIF
npx remotion render src/Root.tsx SlateOneMarketing output.gif

# Render specific frame as image
npx remotion still src/Root.tsx SlateOneMarketing output.png --frame=150
```

## Customization

Edit `src/MarketingVideo.tsx` to:
- Adjust timing (change `durationInFrames`)
- Modify feature order
- Update text content
- Change animations

## File Structure

```
marketing-video/
├── src/
│   ├── Root.tsx              # Main composition registry
│   ├── MarketingVideo.tsx    # Video timeline & sequences
│   └── scenes/
│       ├── IntroScene.tsx    # Opening scene
│       ├── FeatureScene.tsx  # Reusable feature showcase
│       └── CTAScene.tsx      # Call-to-action finale
├── package.json
├── tsconfig.json
└── remotion.config.ts
```

## Animation Techniques Used

- **Spring animations**: Smooth, natural motion
- **Interpolation**: Controlled transitions
- **Stagger effects**: Sequential element reveals
- **Gradient backgrounds**: Dynamic visual interest
- **Scale & rotation**: Attention-grabbing entrances

## Export Recommendations

- **Resolution**: 1920x1080 (Full HD)
- **Frame Rate**: 30fps
- **Format**: MP4 (H.264)
- **Duration**: 30 seconds
- **File Size**: ~5-10MB (optimized for web)

## Next Steps

1. Preview in Remotion Studio
2. Adjust timing/animations as needed
3. Add background music (optional)
4. Render final video
5. Upload to social media/website
