import { Composition } from 'remotion';
import { MarketingVideo } from './MarketingVideo';
import { UserPOVVideo } from './UserPOVVideo';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="SlateOneMarketing"
        component={MarketingVideo}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          titleText: 'SlateOne',
          subtitleText: 'Automate Your Script Breakdown',
        }}
      />
      <Composition
        id="SlateOnePOV"
        component={UserPOVVideo}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
