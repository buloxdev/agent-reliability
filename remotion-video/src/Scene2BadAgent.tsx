import { useCurrentFrame, interpolate, spring, Easing } from 'remotion';
import { COLORS, WIDTH, HEIGHT } from './constants';

const EVENTS = [
  { t: 0.5, icon: '💬', text: 'User asks about refunds', color: COLORS.text },
  { t: 2.5, icon: '🤖', text: 'Agent claims "definitely down 80%"', color: COLORS.danger },
  { t: 4.5, icon: '🔧', text: 'Tool returns: 14 refunds', color: COLORS.text },
  { t: 6.5, icon: '⚠️', text: 'Agent ignores tool data', color: COLORS.warn },
];

const DIMS = [
  { label: 'Consistency', start: 100, end: 55 },
  { label: 'Error Recovery', start: 100, end: 0 },
  { label: 'Tool Accuracy', start: 100, end: 35 },
  { label: 'Grounding', start: 100, end: 7 },
];

export const Scene2BadAgent = () => {
  const frame = useCurrentFrame();
  const fps = 30;

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const compositeScore = interpolate(frame, [30, 180], [100, 26], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        width: WIDTH,
        height: HEIGHT,
        background: COLORS.bg,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        padding: '60px 80px',
      }}
    >
      {/* Title */}
      <div
        style={{
          fontSize: 36,
          fontWeight: 700,
          color: COLORS.text,
          opacity: titleOpacity,
          marginBottom: 40,
        }}
      >
        The <span style={{ color: COLORS.danger }}>Hallucinating</span> Agent
      </div>

      <div style={{ display: 'flex', flex: 1, gap: 60 }}>
        {/* Left: Timeline */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
          {EVENTS.map((ev, i) => {
            const evFrame = ev.t * fps;
            const evOpacity = interpolate(frame, [evFrame, evFrame + 15], [0, 1], { extrapolateRight: 'clamp' });
            const evX = spring({ frame: frame - evFrame, fps, from: -40, to: 0, config: { damping: 14 } });
            return (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  opacity: evOpacity,
                  transform: `translateX(${evX}px)`,
                  background: COLORS.cardBg,
                  padding: '16px 24px',
                  borderRadius: 12,
                  border: `1px solid ${COLORS.border}`,
                }}
              >
                <span style={{ fontSize: 28 }}>{ev.icon}</span>
                <span style={{ fontSize: 22, color: ev.color }}>{ev.text}</span>
              </div>
            );
          })}
        </div>

        {/* Right: Score Panel */}
        <div
          style={{
            width: 440,
            background: COLORS.cardBg,
            borderRadius: 16,
            border: `1px solid ${COLORS.border}`,
            padding: 32,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <div style={{ fontSize: 18, color: COLORS.muted, marginBottom: 12 }}>Composite Score</div>
          <div
            style={{
              fontSize: 96,
              fontWeight: 900,
              color: compositeScore < 50 ? COLORS.danger : compositeScore < 70 ? COLORS.warn : COLORS.success,
              fontVariantNumeric: 'tabular-nums',
              lineHeight: 1,
            }}
          >
            {Math.round(compositeScore)}
          </div>

          {/* Dimension bars */}
          <div style={{ width: '100%', marginTop: 32, display: 'flex', flexDirection: 'column', gap: 16 }}>
            {DIMS.map((dim, i) => {
              const dimStartFrame = 60 + i * 30;
              const dimValue = interpolate(frame, [dimStartFrame, dimStartFrame + 60], [dim.start, dim.end], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
                easing: Easing.out(Easing.cubic),
              });
              const barOpacity = interpolate(frame, [dimStartFrame, dimStartFrame + 20], [0, 1], { extrapolateRight: 'clamp' });
              const barColor = dimValue < 30 ? COLORS.danger : dimValue < 60 ? COLORS.warn : COLORS.success;
              return (
                <div key={i} style={{ opacity: barOpacity }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 14, color: COLORS.text }}>{dim.label}</span>
                    <span style={{ fontSize: 14, color: barColor, fontWeight: 600 }}>{Math.round(dimValue)}</span>
                  </div>
                  <div style={{ width: '100%', height: 8, background: COLORS.border, borderRadius: 4, overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${dimValue}%`,
                        height: '100%',
                        background: barColor,
                        borderRadius: 4,
                        transition: 'width 0.1s linear',
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
