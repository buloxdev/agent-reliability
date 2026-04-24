import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { COLORS, WIDTH, HEIGHT } from './constants';

export const Scene1Hook = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
  const scale = spring({ frame, fps, from: 0.9, to: 1, config: { damping: 12 } });
  const glowOpacity = interpolate(frame, [0, 60], [0.3, 0.8], { extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        width: WIDTH,
        height: HEIGHT,
        background: COLORS.bg,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      {/* Glow behind text */}
      <div
        style={{
          position: 'absolute',
          width: 600,
          height: 200,
          background: `radial-gradient(ellipse, ${COLORS.accent}44, transparent 70%)`,
          opacity: glowOpacity,
        }}
      />
      <div
        style={{
          fontSize: 72,
          fontWeight: 800,
          color: COLORS.text,
          textAlign: 'center',
          lineHeight: 1.2,
          opacity,
          transform: `scale(${scale})`,
        }}
      >
        Can you{' '}
        <span style={{ color: COLORS.accent }}>trust</span>
        <br />
        your AI agent?
      </div>
      <div
        style={{
          marginTop: 24,
          fontSize: 28,
          color: COLORS.muted,
          opacity: interpolate(frame, [15, 40], [0, 1], { extrapolateRight: 'clamp' }),
        }}
      >
        Most agents are black boxes.
      </div>
    </div>
  );
};
