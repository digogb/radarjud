import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const COLORS = {
  bg: "#0a0f1e",
  bgCard: "#111827",
  primary: "#3b82f6",
  accent: "#06b6d4",
  success: "#10b981",
  danger: "#ef4444",
  text: "#f0f6fc",
  textSecondary: "#94a3b8",
  border: "rgba(255,255,255,0.08)",
  sidebar: "#0d1424",
};

const NavItem: React.FC<{ icon: string; label: string; active?: boolean }> = ({ icon, label, active }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: "10px 16px",
      borderRadius: 10,
      background: active ? "rgba(59,130,246,0.15)" : "transparent",
      border: active ? "1px solid rgba(59,130,246,0.3)" : "1px solid transparent",
      color: active ? COLORS.primary : COLORS.textSecondary,
      fontSize: 14,
      fontWeight: active ? 600 : 400,
      marginBottom: 4,
    }}
  >
    <span style={{ fontSize: 16 }}>{icon}</span>
    {label}
  </div>
);

const positivePatterns = [
  { pattern: "expedição de precatório", enabled: true },
  { pattern: "alvará de levantamento", enabled: true },
  { pattern: "mandado de levantamento", enabled: true },
  { pattern: "RPV", enabled: true },
  { pattern: "acordo homologado", enabled: true },
  { pattern: "ordem de pagamento", enabled: true },
];

const negativePatterns = [
  { pattern: "anulação", enabled: true },
  { pattern: "cassação", enabled: true },
  { pattern: "suspensão", enabled: true },
  { pattern: "revogação", enabled: true },
  { pattern: "extinção sem julgamento", enabled: true },
];

const Toggle: React.FC<{ enabled: boolean }> = ({ enabled }) => (
  <div
    style={{
      width: 40,
      height: 22,
      borderRadius: 11,
      background: enabled ? COLORS.success : "rgba(255,255,255,0.1)",
      position: "relative",
      transition: "background 0.3s",
    }}
  >
    <div
      style={{
        position: "absolute",
        top: 3,
        left: enabled ? 21 : 3,
        width: 16,
        height: 16,
        borderRadius: "50%",
        background: "white",
        transition: "left 0.3s",
      }}
    />
  </div>
);

export const ParametrizacaoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const activeTab = frame > 80 ? "negative" : "positive";

  const tabTransition = interpolate(frame, [75, 90], [0, 1], { extrapolateRight: "clamp" });

  const showNewPattern = frame > 100;
  const newPatternSpring = spring({
    fps,
    frame: frame - 100,
    config: { damping: 14, stiffness: 120 },
    durationInFrames: 25,
  });

  const typingProgress = interpolate(frame, [115, 145], [0, 1], { extrapolateRight: "clamp" });
  const newText = "precatório complementar".slice(0, Math.floor(typingProgress * 23));

  const patterns = activeTab === "positive" ? positivePatterns : negativePatterns;

  return (
    <AbsoluteFill
      style={{
        background: COLORS.bg,
        fontFamily: "'Inter', 'Segoe UI', sans-serif",
        display: "flex",
      }}
    >
      {/* Sidebar */}
      <div
        style={{
          width: 220,
          background: COLORS.sidebar,
          borderRight: `1px solid ${COLORS.border}`,
          padding: "24px 16px",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 8px", marginBottom: 24 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "linear-gradient(135deg, #3b82f6, #06b6d4)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>📡</div>
          <span style={{ fontSize: 18, fontWeight: 800, color: COLORS.text }}>RadarJud</span>
        </div>
        <NavItem icon="📊" label="Dashboard" />
        <NavItem icon="🔍" label="Busca" />
        <NavItem icon="👥" label="Monitorados" />
        <NavItem icon="💡" label="Oportunidades" />
        <NavItem icon="⚙️" label="Parametrização" active />
      </div>

      {/* Main */}
      <div style={{ flex: 1, padding: "32px 40px", overflow: "hidden" }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: COLORS.text, marginBottom: 4 }}>
            Parametrização
          </div>
          <div style={{ fontSize: 14, color: COLORS.textSecondary }}>
            Configure os padrões de detecção de oportunidades de crédito
          </div>
        </div>

        {/* Tabs */}
        <div
          style={{
            display: "flex",
            gap: 0,
            background: COLORS.bgCard,
            borderRadius: 12,
            padding: 4,
            marginBottom: 24,
            border: `1px solid ${COLORS.border}`,
            width: "fit-content",
          }}
        >
          <div
            style={{
              padding: "10px 24px",
              borderRadius: 8,
              background: activeTab === "positive" ? COLORS.success + "22" : "transparent",
              border: activeTab === "positive" ? `1px solid ${COLORS.success}44` : "1px solid transparent",
              color: activeTab === "positive" ? COLORS.success : COLORS.textSecondary,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            ✓ Padrões Positivos ({positivePatterns.length})
          </div>
          <div
            style={{
              padding: "10px 24px",
              borderRadius: 8,
              background: activeTab === "negative" ? COLORS.danger + "22" : "transparent",
              border: activeTab === "negative" ? `1px solid ${COLORS.danger}44` : "1px solid transparent",
              color: activeTab === "negative" ? COLORS.danger : COLORS.textSecondary,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            ✕ Padrões Negativos ({negativePatterns.length})
          </div>
        </div>

        {/* Explanation */}
        <div
          style={{
            background: `${activeTab === "positive" ? COLORS.success : COLORS.danger}11`,
            border: `1px solid ${activeTab === "positive" ? COLORS.success : COLORS.danger}33`,
            borderRadius: 12,
            padding: "12px 16px",
            fontSize: 13,
            color: COLORS.textSecondary,
            marginBottom: 20,
            lineHeight: 1.6,
          }}
        >
          {activeTab === "positive"
            ? "Expressões que, quando encontradas em uma publicação, indicam possibilidade de recebimento de crédito."
            : "Expressões que, quando encontradas em publicações mais recentes do mesmo processo, invalidam uma oportunidade detectada."}
        </div>

        {/* Pattern list */}
        <div
          style={{
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 16,
            overflow: "hidden",
          }}
        >
          {patterns.map((p, i) => {
            const itemOpacity = interpolate(frame, [i * 8, i * 8 + 15], [0, 1], { extrapolateRight: "clamp" });
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "14px 20px",
                  borderBottom: i < patterns.length - 1 ? `1px solid ${COLORS.border}` : "none",
                  gap: 14,
                  opacity: itemOpacity,
                }}
              >
                <div
                  style={{
                    color: COLORS.textSecondary,
                    fontSize: 16,
                    cursor: "grab",
                  }}
                >
                  ⋮⋮
                </div>
                <div
                  style={{
                    flex: 1,
                    fontSize: 14,
                    color: COLORS.text,
                    fontFamily: "monospace",
                    background: "rgba(255,255,255,0.04)",
                    padding: "6px 12px",
                    borderRadius: 8,
                    border: `1px solid ${COLORS.border}`,
                  }}
                >
                  "{p.pattern}"
                </div>
                <Toggle enabled={p.enabled} />
                <div style={{ color: COLORS.textSecondary, fontSize: 14, cursor: "pointer" }}>✎</div>
                <div style={{ color: COLORS.textSecondary + "88", fontSize: 14, cursor: "pointer" }}>✕</div>
              </div>
            );
          })}
        </div>

        {/* Add new pattern */}
        {showNewPattern && (
          <div
            style={{
              marginTop: 16,
              display: "flex",
              gap: 12,
              alignItems: "center",
              opacity: newPatternSpring,
              transform: `translateY(${interpolate(newPatternSpring, [0, 1], [15, 0])}px)`,
            }}
          >
            <div
              style={{
                flex: 1,
                background: COLORS.bgCard,
                border: `2px solid ${COLORS.primary}`,
                borderRadius: 10,
                padding: "12px 16px",
                color: COLORS.text,
                fontSize: 14,
                fontFamily: "monospace",
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              "{newText}
              <div style={{ width: 1.5, height: 16, background: COLORS.primary }} />
              "
            </div>
            <div
              style={{
                padding: "12px 24px",
                background: COLORS.primary,
                borderRadius: 10,
                color: "white",
                fontSize: 14,
                fontWeight: 600,
                whiteSpace: "nowrap",
              }}
            >
              + Adicionar
            </div>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
