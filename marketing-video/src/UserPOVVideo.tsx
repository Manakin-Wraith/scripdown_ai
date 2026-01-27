import React from 'react';
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { UploadScene } from './scenes/pov/UploadScene';
import { AnalysisScene } from './scenes/pov/AnalysisScene';
import { SceneViewerScene } from './scenes/pov/SceneViewerScene';
import { CollaborationScene } from './scenes/pov/CollaborationScene';
import { ExportScene } from './scenes/pov/ExportScene';
import { POVCTAScene } from './scenes/pov/POVCTAScene';

export const UserPOVVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a' }}>
      {/* Scene 1: Upload (0-5s) */}
      <Sequence from={0} durationInFrames={150}>
        <UploadScene />
      </Sequence>

      {/* Scene 2: AI Analysis (5-10s) */}
      <Sequence from={150} durationInFrames={150}>
        <AnalysisScene />
      </Sequence>

      {/* Scene 3: Scene Viewer & Breakdown (10-17s) */}
      <Sequence from={300} durationInFrames={210}>
        <SceneViewerScene />
      </Sequence>

      {/* Scene 4: Collaboration (17-23s) */}
      <Sequence from={510} durationInFrames={180}>
        <CollaborationScene />
      </Sequence>

      {/* Scene 5: Export (23-27s) */}
      <Sequence from={690} durationInFrames={120}>
        <ExportScene />
      </Sequence>

      {/* Scene 6: CTA (27-30s) */}
      <Sequence from={810} durationInFrames={90}>
        <POVCTAScene />
      </Sequence>
    </AbsoluteFill>
  );
};
