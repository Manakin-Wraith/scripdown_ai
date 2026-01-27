# SlateOne POV Marketing Video

A user journey-focused marketing video showing real platform interaction from a filmmaker's perspective.

## 🎬 Video Overview

**Duration**: 30 seconds (900 frames @ 30fps)  
**Resolution**: 1920x1080 (Full HD)  
**Style**: Screen recording simulation with UI mockups  
**Composition ID**: `SlateOnePOV`

## 📖 User Journey Storyboard

### Scene 1: Upload (0-5s)
**POV**: User drags screenplay PDF into the platform

- Browser window mockup with SlateOne URL
- Drag-and-drop zone with hover states
- File appears with upload progress bar
- Progress: 0% → 100%

**Key Message**: "Simple, intuitive upload process"

---

### Scene 2: AI Analysis (5-10s)
**POV**: Watching AI process the script in real-time

- AI analysis progress indicator
- Scene detection happening live
- Scenes appearing one by one:
  - Scene 1: INT. COFFEE SHOP - DAY
  - Scene 2: EXT. CITY STREET - DAY
  - Scene 3: INT. APARTMENT - NIGHT
  - Scene 4: INT. OFFICE - DAY
  - Scene 5: EXT. PARK - SUNSET
- Powered by Google Gemini 2.0 badge

**Key Message**: "AI extracts every scene automatically"

---

### Scene 3: Scene Viewer & Breakdown (10-17s)
**POV**: Exploring detailed scene breakdown

- Sidebar with scene list (Scene 2 selected)
- Main panel showing comprehensive breakdown:
  - **Characters**: SARAH, MIKE
  - **Location**: City Street (Exterior)
  - **Time of Day**: Day
  - **Props**: Coffee Cup, Briefcase, Phone
- All metadata extracted automatically badge

**Key Message**: "Every detail, automatically extracted"

---

### Scene 4: Collaboration (17-23s)
**POV**: Team members discussing scenes in real-time

- Team avatars (Director, Producer, AD, DP)
- Live comment thread on Scene 2:
  - Director: "Let's add a tracking shot here..."
  - DP: "Perfect! I'll prep the Steadicam..."
- Real-time notification badge: "3 new updates"

**Key Message**: "Your entire team, in sync"

---

### Scene 5: Export (23-27s)
**POV**: Exporting breakdown reports

- Export format options grid:
  - PDF (Full breakdown report)
  - Excel (Spreadsheet format)
  - CSV (Raw data export)
  - JSON (API integration)
- Download progress bar for PDF
- Success checkmark

**Key Message**: "Share with your team, instantly"

---

### Scene 6: CTA (27-30s)
**POV**: Call to action

- "Ready to Transform Your Pre-Production?"
- Pulsing "Start Free Trial" button
- Benefits checklist:
  - ✓ 14-Day Free Trial
  - ✓ No Credit Card
  - ✓ Full Access
- Website: www.slateone.studio

---

## 🎨 Visual Design

### Browser Mockup
- Realistic browser chrome (traffic lights, URL bar)
- Dark theme UI matching SlateOne design
- Smooth transitions between states

### Color Palette
- **Background**: #0f172a (Dark Slate)
- **UI Elements**: #1e293b, #334155 (Slate variants)
- **Primary Accent**: #fbbf24, #f59e0b (Amber/Gold)
- **Success**: #10b981 (Green)
- **Text**: #f1f5f9, #94a3b8 (Light slate)

### Typography
- **Font**: Inter (system font stack)
- **Headings**: 42-56px, Bold
- **Body**: 14-24px, Regular/Medium

---

## 🚀 Usage

### Preview in Remotion Studio
```bash
npm run dev
```
Select **"SlateOnePOV"** from the composition dropdown.

### Render Video
```bash
npx remotion render src/index.ts SlateOnePOV pov-output.mp4
```

### Render for Social Media

**Instagram/Facebook (Square)**:
```bash
npx remotion render src/index.ts SlateOnePOV pov-instagram.mp4 --width=1080 --height=1080
```

**Instagram Stories (Vertical)**:
```bash
npx remotion render src/index.ts SlateOnePOV pov-story.mp4 --width=1080 --height=1920
```

**Twitter/X (Landscape)**:
```bash
npx remotion render src/index.ts SlateOnePOV pov-twitter.mp4 --width=1280 --height=720
```

---

## 🎯 Key Differences from Standard Version

| Aspect | Standard Version | POV Version |
|--------|-----------------|-------------|
| **Perspective** | Feature showcase | User journey |
| **Visuals** | Icons & text | UI mockups & interactions |
| **Storytelling** | "What it does" | "How you use it" |
| **Engagement** | Informative | Immersive |
| **Best For** | Landing pages | Social media, demos |

---

## 📝 Customization

### Adjust Scene Timings
Edit `src/UserPOVVideo.tsx`:

```tsx
// Change upload scene from 5s to 7s
<Sequence from={0} durationInFrames={210}> {/* was 150 */}
  <UploadScene />
</Sequence>
```

### Modify UI Elements
Each scene component is in `src/scenes/pov/`:
- `UploadScene.tsx` - Upload interface
- `AnalysisScene.tsx` - AI processing
- `SceneViewerScene.tsx` - Breakdown details
- `CollaborationScene.tsx` - Team comments
- `ExportScene.tsx` - Export options
- `POVCTAScene.tsx` - Call to action

### Change Script Content
Edit scene data in `AnalysisScene.tsx`:

```tsx
const sceneItems = [
  { number: '1', setting: 'YOUR SCENE HERE', time: 30 },
  // Add more scenes...
];
```

---

## 🎬 Production Tips

### 1. **Realistic Timing**
- Keep upload progress realistic (2-3 seconds)
- AI analysis should feel fast but not instant
- Allow time for viewers to read text

### 2. **Visual Hierarchy**
- Important elements should be larger
- Use color to draw attention (gold accents)
- Maintain consistent spacing

### 3. **Motion Design**
- Use spring animations for natural feel
- Stagger elements for visual interest
- Avoid jarring transitions

### 4. **Text Readability**
- Ensure sufficient contrast
- Use appropriate font sizes
- Limit text per frame

---

## 🎥 Rendering Best Practices

### High Quality (Production)
```bash
npx remotion render src/index.ts SlateOnePOV output.mp4 \
  --quality=100 \
  --codec=h264 \
  --audio-codec=aac
```

### Fast Preview (Testing)
```bash
npx remotion render src/index.ts SlateOnePOV preview.mp4 \
  --quality=50 \
  --frames=0-300
```

### GIF for Social
```bash
npx remotion render src/index.ts SlateOnePOV demo.gif \
  --quality=80
```

---

## 📊 Performance

- **Render Time**: ~2-4 minutes (depends on hardware)
- **File Size**: ~8-12 MB (H.264, quality 80)
- **Complexity**: Moderate (CSS animations, no video layers)

---

## 🔄 Version Comparison

Both versions are available in the same project:

1. **SlateOneMarketing** - Feature-focused version
2. **SlateOnePOV** - User journey version

Switch between them in Remotion Studio or specify in render commands.

---

## 📚 Related Files

- `src/UserPOVVideo.tsx` - Main composition
- `src/scenes/pov/*.tsx` - Individual scene components
- `PRODUCTION_GUIDE.md` - General rendering guide
- `STORYBOARD.md` - Standard version storyboard

---

## 💡 Use Cases

**POV Version is ideal for**:
- Social media ads (Instagram, TikTok, LinkedIn)
- Product demos and walkthroughs
- Onboarding videos
- Email campaigns
- Conference presentations

**Standard Version is ideal for**:
- Landing page hero videos
- Explainer content
- Feature announcements
- Investor presentations
- Website backgrounds
