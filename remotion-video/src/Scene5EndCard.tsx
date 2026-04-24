import { useCurrentFrame, interpolate, spring } from 'remotion';
import { COLORS, WIDTH, HEIGHT } from './constants';

export const Scene5EndCard = () => {
  const frame = useCurrentFrame();
  const fps = 30;

  const bgOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
  const titleScale = spring({ frame: frame - 15, fps, from: 0.8, to: 1, config: { damping: 12 } });
  const titleOpacity = interpolate(frame, [15, 35], [0, 1], { extrapolateRight: 'clamp' });
  const subtitleOpacity = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: 'clamp' });
  const linkOpacity = interpolate(frame, [50, 70], [0, 1], { extrapolateRight: 'clamp' });

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
      {/* Radial glow */}
      <div
        style={{
          position: 'absolute',
          width: 700,
          height: 400,
          background: `radial-gradient(ellipse, ${COLORS.accent}33, transparent 70%)`,
          opacity: bgOpacity,
        }}
      />

      <div
        style={{
          fontSize: 64,
          fontWeight: 800,
          color: COLORS.text,
          textAlign: 'center',
          opacity: titleOpacity,
          transform: `scale(${titleScale})`,
        }}
      >
        Agent Reliability
        <br />
        <span style={{ color: COLORS.accent }}>Scores</span>
      </div>

      <div
        style={{
          marginTop: 20,
          fontSize: 28,
          color: COLORS.muted,
          opacity: subtitleOpacity,
        }}
      >
        The credit score for AI agents.
      </div>

      <div
        style={{
          marginTop: 48,
          fontSize: 18,
          color: COLORS.accent,
          opacity: linkOpacity,
          fontFamily: 'monospace',
        }}
      >
        github.com / agent-reliability
      </div>
    </div>
  );
};
