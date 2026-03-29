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
  danger: "#ef4444",
  warning: "#f59e0b",
  text: "#f0f6fc",
  textSecondary: "#94a3b8",
  border: "rgba(255,255,255,0.08)",
};

const problems = [
  {
    icon: "⏱️",
    title: "Verificação Manual Diária",
    desc: "Advogados perdem 40-80h/mês verificando portais de tribunais manualmente",
    color: "#ef4444",
  },
  {
    icon: "⚠️",
    title: "Risco de Perder Publicações Críticas",
    desc: "Uma publicação ignorada pode significar perda de prazo processual irreversível",
    color: "#f59e0b",
  },
  {
    icon: "💸",
    title: "Oportunidades de Crédito Perdidas",
    desc: "Alvarás, precatórios e levantamentos não detectados = crédito não recuperado",
    color: "#ef4444",
  },
  {
    icon: "📊",
    title: "Impossível Monitorar em Escala",
    desc: "Centenas de réus em múltiplos tribunais — inviável sem automação",
    color: "#f59e0b",
  },
];

export const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, 20], [-30, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, #0d1117 0%, ${COLORS.bg} 100%)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Inter', 'Segoe UI', sans-serif",
        padding: "60px 80px",
      }}
    >
      {/* Title */}
      <div
        style={{
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          marginBottom: 48,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: "3px",
            color: COLORS.danger,
            textTransform: "uppercase",
            marginBottom: 12,
          }}
        >
          O Problema
        </div>
        <div
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: COLORS.text,
            letterSpacing: "-1px",
            lineHeight: 1.1,
          }}
        >
          Monitorar o DJE manualmente
          <br />
          <span style={{ color: COLORS.danger }}>é inviável</span>
        </div>
      </div>

      {/* Problem cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 20,
          width: "100%",
          maxWidth: 1400,
        }}
      >
        {problems.map((problem, i) => {
          const cardSpring = spring({
            fps,
            frame: frame - 20 - i * 15,
            config: { damping: 14, stiffness: 80 },
            durationInFrames: 35,
          });

          const cardOpacity = interpolate(frame, [20 + i * 15, 40 + i * 15], [0, 1], {
            extrapolateRight: "clamp",
          });

          return (
            <div
              key={i}
              style={{
                background: COLORS.bgCard,
                border: `1px solid ${COLORS.border}`,
                borderLeft: `4px solid ${problem.color}`,
                borderRadius: 16,
                padding: "28px 32px",
                display: "flex",
                gap: 20,
                alignItems: "flex-start",
                opacity: cardOpacity,
                transform: `translateY(${interpolate(cardSpring, [0, 1], [30, 0])}px)`,
              }}
            >
              <div style={{ fontSize: 36, flexShrink: 0 }}>{problem.icon}</div>
              <div>
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 700,
                    color: COLORS.text,
                    marginBottom: 8,
                  }}
                >
                  {problem.title}
                </div>
                <div
                  style={{
                    fontSize: 15,
                    color: COLORS.textSecondary,
                    lineHeight: 1.5,
                  }}
                >
                  {problem.desc}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom statement */}
      {frame > 90 && (
        <div
          style={{
            marginTop: 40,
            fontSize: 22,
            color: COLORS.accent,
            fontWeight: 600,
            opacity: interpolate(frame, [90, 110], [0, 1], { extrapolateRight: "clamp" }),
            textAlign: "center",
          }}
        >
          O RadarJud resolve tudo isso — de forma automática e inteligente.
        </div>
      )}
    </AbsoluteFill>
  );
};
