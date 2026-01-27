import React from 'react';
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { IntroScene } from './scenes/IntroScene';
import { FeatureScene } from './scenes/FeatureScene';
import { CTAScene } from './scenes/CTAScene';

interface MarketingVideoProps {
  titleText: string;
  subtitleText: string;
}

export const MarketingVideo: React.FC<MarketingVideoProps> = ({
  titleText,
  subtitleText,
}) => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a' }}>
      {/* Intro Scene: 0-150 frames (5 seconds) */}
      <Sequence from={0} durationInFrames={150}>
        <IntroScene title={titleText} subtitle={subtitleText} />
      </Sequence>

      {/* Feature 1: AI-Powered Breakdown - 150-300 frames */}
      <Sequence from={150} durationInFrames={150}>
        <FeatureScene
          title="AI-Powered Script Breakdown"
          description="Upload your script and let Google Gemini 2.0 automatically extract scenes, characters, props, and more"
          icon="🤖"
          delay={0}
        />
      </Sequence>

      {/* Feature 2: Role-Specific Dashboards - 300-450 frames */}
      <Sequence from={300} durationInFrames={150}>
        <FeatureScene
          title="Role-Specific Dashboards"
          description="Tailored views for Directors, Producers, Production Designers, and every HOD"
          icon="👥"
          delay={0}
        />
      </Sequence>

      {/* Feature 3: Real-Time Collaboration - 450-600 frames */}
      <Sequence from={450} durationInFrames={150}>
        <FeatureScene
          title="Real-Time Collaboration"
          description="Team annotations, comments, and shared breakdown sheets for seamless pre-production"
          icon="💬"
          delay={0}
        />
      </Sequence>

      {/* Feature 4: Export & Reports - 600-750 frames */}
      <Sequence from={600} durationInFrames={150}>
        <FeatureScene
          title="Professional Exports"
          description="Generate breakdown sheets, reports, and stripboards in PDF and Excel formats"
          icon="📄"
          delay={0}
        />
      </Sequence>

      {/* CTA Scene: 750-900 frames (5 seconds) */}
      <Sequence from={750} durationInFrames={150}>
        <CTAScene />
      </Sequence>
    </AbsoluteFill>
  );
};
