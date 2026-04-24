import { useCurrentFrame, interpolate, spring } from 'remotion';
import { COLORS, WIDTH, HEIGHT } from './constants';

const SCENARIOS = [
  { name: 'Good', score: 100, color: COLORS.success },
  { name: 'Mixed', score: 92, color: COLORS.success },
  { name: 'Flaky', score: 58, color: COLORS.warn },
  { name: 'Hallucinating', score: 26, color: COLORS.danger },
];

const HISTO_BINS = [
  { label: '90-100', count: 3, color: COLORS.success },
  { label: '70-89', count: 2, color: COLORS.success },
  { label: '50-69', count: 4, color: COLORS.warn },
  { label: '30-49', count: 3, color: COLORS.warn },
  { label: '0-29', count: 2, color: COLORS.danger },
];

export const Scene4Overview = () => {
  const frame = useCurrentFrame();
  const fps = 30;

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const panelY = spring({ frame, fps, from: 40, to: 0, config: { damping: 12 } });

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
        Fleet-<span style={{ color: COLORS.accent }}>wide</span> Observability
      </div>

      <div
        style={{
          display: 'flex',
          flex: 1,
          gap: 40,
          transform: `translateY(${panelY}px)`,
        }}
      >
        {/* Left: Session Grid + Histogram */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Session Grid */}
          <div
            style={{
              background: COLORS.cardBg,
              borderRadius: 16,
              border: `1px solid ${COLORS.border}`,
              padding: 24,
            }}
          >
            <div style={{ fontSize: 16, color: COLORS.muted, marginBottom: 16 }}>Session Grid (1,351 scored)</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 8 }}>
              {Array.from({ length: 24 }).map((_, i) => {
                const is = i < SCENARIOS.length;
                const s = is ? SCENARIOS[i] : SCENARIOS[Math.floor(Math.random() * SCENARIOS.length)];
                const f = is ? 20 + i * 10 : 100 + i * 5;
                const opacity = interpolate(frame, [f, f + 15], [0, 1], { extrapolateRight: 'clamp' });
                const scale = spring({ frame: frame - f, fps, from: 0.5, to: 1, config: { damping: 10 } });
                return (
                  <div
                    key={i}
                    style={{
                      aspectRatio: '1',
                      borderRadius: 8,
                      background: s.color + '33',
                      border: `2px solid ${s.color}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 13,
                      fontWeight: 700,
                      color: s.color,
                      opacity,
                      transform: `scale(${scale})`,
                    }}
                  >
                    {is ? s.score : Math.round(20 + Math.random() * 70)}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Histogram */}
          <div
            style={{
              background: COLORS.cardBg,
              borderRadius: 16,
              border: `1px solid ${COLORS.border}`,
              padding: 24,
              flex: 1,
            }}
          >
            <div style={{ fontSize: 16, color: COLORS.muted, marginBottom: 16 }}>Score Distribution</div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 'calc(100% - 40px)' }}>
              {HISTO_BINS.map((bin, i) => {
                const f = 60 + i * 15;
                const h = interpolate(frame, [f, f + 40], [0, bin.count * 14], { extrapolateRight: 'clamp' });
                const opacity = interpolate(frame, [f, f + 20], [0, 1], { extrapolateRight: 'clamp' });
                return (
                  <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, opacity }}>
                    <div style={{ fontSize: 12, color: COLORS.text, fontWeight: 600 }}>{bin.count}</div>
                    <div style={{ width: '100%', background: COLORS.border, borderRadius: 4, height: 120, position: 'relative' }}>
                      <div
                        style={{
                          position: 'absolute',
                          bottom: 0,
                          width: '100%',
                          height: h,
                          background: bin.color,
                          borderRadius: 4,
                        }}
                      />
                    </div>
                    <div style={{ fontSize: 11, color: COLORS.muted }}>{bin.label}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Radar + Gauge */}
        <div style={{ width: 420, display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Composite Gauge */}
          <div
            style={{
              background: COLORS.cardBg,
              borderRadius: 16,
              border: `1px solid ${COLORS.border}`,
              padding: 24,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <div style={{ fontSize: 16, color: COLORS.muted, marginBottom: 12 }}>Fleet Average</div>
            <div
              style={{
                fontSize: 80,
                fontWeight: 900,
                color: COLORS.warn,
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {Math.round(interpolate(frame, [40, 100], [0, 63.4], { extrapolateRight: 'clamp' }))}
            </div>
            <div style={{ fontSize: 14, color: COLORS.muted, marginTop: 4 }}>/ 100</div>
          </div>

          {/* Radar (simplified as dimension list) */}
          <div
            style={{
              background: COLORS.cardBg,
              borderRadius: 16,
              border: `1px solid ${COLORS.border}`,
              padding: 24,
              flex: 1,
            }}
          >
            <div style={{ fontSize: 16, color: COLORS.muted, marginBottom: 16 }}>Dimension Averages</div>
            {[
              { label: 'Consistency', value: 78, color: COLORS.success },
              { label: 'Error Recovery', value: 45, color: COLORS.warn },
              { label: 'Tool Accuracy', value: 21, color: COLORS.danger },
              { label: 'Grounding', value: 93, color: COLORS.success },
            ].map((dim, i) => {
              const f = 80 + i * 12;
              const w = interpolate(frame, [f, f + 30], [0, dim.value], { extrapolateRight: 'clamp' });
              const opacity = interpolate(frame, [f, f + 15], [0, 1], { extrapolateRight: 'clamp' });
              return (
                <div key={i} style={{ marginBottom: 16, opacity }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 14, color: COLORS.text }}>{dim.label}</span>
                    <span style={{ fontSize: 14, color: dim.color, fontWeight: 600 }}>{dim.value}</span>
                  </div>
                  <div style={{ width: '100%', height: 6, background: COLORS.border, borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${w}%`, height: '100%', background: dim.color, borderRadius: 3 }} />
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
