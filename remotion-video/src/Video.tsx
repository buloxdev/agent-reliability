import { Composition, Sequence } from 'remotion';
import { Scene1Hook } from './Scene1Hook';
import { Scene2BadAgent } from './Scene2BadAgent';
import { Scene3GoodAgent } from './Scene3GoodAgent';
import { Scene4Overview } from './Scene4Overview';
import { Scene5EndCard } from './Scene5EndCard';
import { FPS, WIDTH, HEIGHT } from './constants';

// Scene durations in frames (30fps)
const SCENE1_DURATION = 4 * FPS;   // 120
const SCENE2_DURATION = 10 * FPS;  // 300
const SCENE3_DURATION = 6 * FPS;   // 180
const SCENE4_DURATION = 6 * FPS;   // 180
const SCENE5_DURATION = 4 * FPS;   // 120

export const RemotionVideo = () => {
  return (
    <>
      <Composition
        id="AgentReliabilityVideo"
        component={AgentReliabilityVideo}
        durationInFrames={SCENE1_DURATION + SCENE2_DURATION + SCENE3_DURATION + SCENE4_DURATION + SCENE5_DURATION}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{}}
      />
    </>
  );
};

const AgentReliabilityVideo = () => {
  let offset = 0;

  return (
    <>
      <Sequence from={offset} durationInFrames={SCENE1_DURATION}>
        <Scene1Hook />
      </Sequence>
      {offset += SCENE1_DURATION}

      <Sequence from={offset} durationInFrames={SCENE2_DURATION}>
        <Scene2BadAgent />
      </Sequence>
      {offset += SCENE2_DURATION}

      <Sequence from={offset} durationInFrames={SCENE3_DURATION}>
        <Scene3GoodAgent />
      </Sequence>
      {offset += SCENE3_DURATION}

      <Sequence from={offset} durationInFrames={SCENE4_DURATION}>
        <Scene4Overview />
      </Sequence>
      {offset += SCENE4_DURATION}

      <Sequence from={offset} durationInFrames={SCENE5_DURATION}>
        <Scene5EndCard />
      </Sequence>
    </>
  );
};
