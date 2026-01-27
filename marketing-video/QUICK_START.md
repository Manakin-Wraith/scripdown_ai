# 🚀 Quick Start Guide

## Get Started in 3 Steps

### 1️⃣ Preview the Video
```bash
cd marketing-video
npm run dev
```

This opens **Remotion Studio** in your browser where you can:
- ✅ Preview the full 30-second video
- ✅ Scrub through timeline frame-by-frame
- ✅ Edit props and see changes live
- ✅ Test different timings

### 2️⃣ Customize (Optional)
Edit these files to personalize:

**Change Text**:
- `src/MarketingVideo.tsx` - Update feature titles/descriptions

**Adjust Timing**:
- `src/MarketingVideo.tsx` - Change `durationInFrames` values

**Modify Animations**:
- `src/scenes/IntroScene.tsx` - Intro animations
- `src/scenes/FeatureScene.tsx` - Feature showcases
- `src/scenes/CTAScene.tsx` - Call-to-action

### 3️⃣ Render Final Video
```bash
npx remotion render src/Root.tsx SlateOneMarketing output.mp4
```

**Output**: `output.mp4` in the `marketing-video` folder

---

## 📊 What You Get

✅ **30-second marketing video** showcasing SlateOne  
✅ **Professional animations** with spring physics  
✅ **Brand-matched design** (dark slate + amber/gold)  
✅ **6 scenes**:
   1. Intro (5s)
   2. AI-Powered Breakdown (5s)
   3. Role-Specific Dashboards (5s)
   4. Real-Time Collaboration (5s)
   5. Professional Exports (5s)
   6. Call-to-Action (5s)

---

## 🎨 Video Specs

| Property | Value |
|----------|-------|
| Duration | 30 seconds |
| Resolution | 1920x1080 (Full HD) |
| Frame Rate | 30 fps |
| Format | MP4 (H.264) |
| File Size | ~5-10 MB |

---

## 🎯 Common Tasks

### Export for Social Media

**Instagram/Facebook (Square)**:
```bash
npx remotion render src/Root.tsx SlateOneMarketing instagram.mp4 --width=1080 --height=1080
```

**Instagram Stories (Vertical)**:
```bash
npx remotion render src/Root.tsx SlateOneMarketing story.mp4 --width=1080 --height=1920
```

**Twitter/X (Landscape)**:
```bash
npx remotion render src/Root.tsx SlateOneMarketing twitter.mp4 --width=1280 --height=720
```

### Export as GIF
```bash
npx remotion render src/Root.tsx SlateOneMarketing output.gif
```

### Export Thumbnail
```bash
npx remotion still src/Root.tsx SlateOneMarketing thumbnail.png --frame=75
```

---

## 🎵 Add Background Music (Optional)

1. Add music file to `public/` folder
2. Edit `src/MarketingVideo.tsx`:

```tsx
import { Audio } from 'remotion';

// Add inside <AbsoluteFill>
<Audio src="/music.mp3" volume={0.3} />
```

---

## 📚 Full Documentation

- **README.md** - Project overview
- **PRODUCTION_GUIDE.md** - Detailed production instructions
- **STORYBOARD.md** - Visual scene breakdown

---

## 🆘 Troubleshooting

**Video won't preview?**
- Run `npm install` to ensure dependencies are installed

**Animations look choppy?**
- This is normal in preview mode
- Final render will be smooth

**Need help?**
- Remotion Docs: https://www.remotion.dev/docs
- Remotion Discord: https://remotion.dev/discord

---

## ✨ Next Steps

1. **Preview**: `npm run dev`
2. **Customize**: Edit text/timing as needed
3. **Render**: Export final MP4
4. **Deploy**: Upload to website/social media

**Estimated Time**: 15-30 minutes from preview to final render

---

## 🎬 Ready to Create?

```bash
cd marketing-video
npm run dev
```

**Happy creating! 🚀**
