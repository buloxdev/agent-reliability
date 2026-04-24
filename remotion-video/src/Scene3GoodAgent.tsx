import { useCurrentFrame, interpolate, spring } from 'remotion';
import { COLORS, WIDTH, HEIGHT } from './constants';

const EVENTS = [
  { t: 0.5, icon: '💬', text: 'User asks about refunds' },
  { t: 2.0, icon: '🔧', text: 'Tool returns: 14 refunds' },
  { t: 3.5, icon: '🤖', text: 'Agent answers: "14 refunds found"' },
  { t: 5.0, icon: '✅', text: 'Answer grounded in tool data' },
];

const DIMS = [
  { label: 'Consistency', value: 100 },
  { label: 'Error Recovery', value: 100 },
  { label: 'Tool Accuracy', value: 100 },
  { label: 'Grounding', value: 100 },
];

export const Scene3GoodAgent = () => {
  const frame = useCurrentFrame();
  const fps = 30;

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const scoreScale = spring({ frame, fps, from: 0.5, to: 1, config: { damping: 10, stiffness: 80 } });
  const scoreOpacity = interpolate(frame, [15, 40], [0, 1], { extrapolateRight: 'clamp' });

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
      <div
        style={{
          fontSize: 36,
          fontWeight: 700,
          color: COLORS.text,
          opacity: titleOpacity,
          marginBottom: 40,
        }}
      >
        The <span style={{ color: COLORS.success }}>Reliable</span> Agent
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
                <span style={{ fontSize: 22, color: COLORS.text }}>{ev.text}</span>
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
            opacity: scoreOpacity,
            transform: `scale(${scoreScale})`,
          }}
        >
          <div style={{ fontSize: 18, color: COLORS.muted, marginBottom: 12 }}>Composite Score</div>
          <div
            style={{
              fontSize: 96,
              fontWeight: 900,
              color: COLORS.success,
              fontVariantNumeric: 'tabular-nums',
              lineHeight: 1,
            }}
          >
            100
          </div>

          <div style={{ width: '100%', marginTop: 32, display: 'flex', flexDirection: 'column', gap: 16 }}>
            {DIMS.map((dim, i) => {
              const dimFrame = 30 + i * 15;
              const dimOpacity = interpolate(frame, [dimFrame, dimFrame + 20], [0, 1], { extrapolateRight: 'clamp' });
              const dimWidth = interpolate(frame, [dimFrame, dimFrame + 40], [0, dim.value], { extrapolateRight: 'clamp' });
              return (
                <div key={i} style={{ opacity: dimOpacity }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 14, color: COLORS.text }}>{dim.label}</span>
                    <span style={{ fontSize: 14, color: COLORS.success, fontWeight: 600 }}>{dim.value}</span>
                  </div>
                  <div style={{ width: '100%', height: 8, background: COLORS.border, borderRadius: 4, overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${dimWidth}%`,
                        height: '100%',
                        background: COLORS.success,
                        borderRadius: 4,
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
