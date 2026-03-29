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
  primary: "#3b82f6",
  accent: "#06b6d4",
  success: "#10b981",
  text: "#f0f6fc",
  textSecondary: "#94a3b8",
};

const features = [
  { icon: "🤖", label: "IA Integrada" },
  { icon: "🏛️", label: "Cobertura Nacional" },
  { icon: "⚡", label: "Detecção em Tempo Real" },
  { icon: "🔒", label: "Multi-Tenant Seguro" },
  { icon: "📊", label: "Análise Semântica" },
  { icon: "📱", label: "Alertas Multicanal" },
];

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({
    fps,
    frame,
    config: { damping: 12, stiffness: 80 },
    durationInFrames: 30,
  });

  const taglineOpacity = interpolate(frame, [20, 45], [0, 1], { extrapolateRight: "clamp" });
  const taglineY = interpolate(frame, [20, 45], [20, 0], { extrapolateRight: "clamp" });

  const featuresOpacity = interpolate(frame, [45, 70], [0, 1], { extrapolateRight: "clamp" });

  const ctaSpring = spring({
    fps,
    frame: frame - 75,
    config: { damping: 14, stiffness: 100 },
    durationInFrames: 30,
  });

  const glowPulse = interpolate(
    Math.sin((frame / 30) * Math.PI * 2),
    [-1, 1],
    [0.4, 0.7]
  );

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at 50% 45%, #0f2044 0%, ${COLORS.bg} 65%)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Inter', 'Segoe UI', sans-serif",
        padding: "60px 80px",
      }}
    >
      {/* Background glow */}
      <div
        style={{
          position: "absolute",
          width: 700,
          height: 700,
          borderRadius: "50%",
          background: `radial-gradient(circle, rgba(59,130,246,${glowPulse}) 0%, transparent 70%)`,
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
        }}
      />

      {/* Grid */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `linear-gradient(rgba(59,130,246,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59,130,246,0.04) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />

      {/* Logo */}
      <div
        style={{
          transform: `scale(${titleSpring})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
          position: "relative",
          zIndex: 1,
          marginBottom: 20,
        }}
      >
        <div
          style={{
            width: 80,
            height: 80,
            borderRadius: 20,
            background: `linear-gradient(135deg, ${COLORS.primary}, ${COLORS.accent})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: `0 0 40px rgba(59,130,246,0.5)`,
          }}
        >
          <svg width="44" height="44" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="28" stroke="white" strokeWidth="2" strokeOpacity="0.3" />
            <circle cx="32" cy="32" r="18" stroke="white" strokeWidth="2" strokeOpacity="0.5" />
            <circle cx="32" cy="32" r="8" stroke="white" strokeWidth="2" strokeOpacity="0.8" />
            <circle cx="32" cy="32" r="3" fill="white" />
            <line x1="32" y1="32" x2="32" y2="4" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        </div>

        <div
          style={{
            fontSize: 60,
            fontWeight: 800,
            color: COLORS.text,
            letterSpacing: "-2px",
            lineHeight: 1,
          }}
        >
          Radar<span
            style={{
              background: `linear-gradient(135deg, ${COLORS.primary}, ${COLORS.accent})`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >Jud</span>
        </div>
      </div>

      {/* Tagline */}
      <div
        style={{
          fontSize: 28,
          fontWeight: 600,
          color: COLORS.textSecondary,
          textAlign: "center",
          opacity: taglineOpacity,
          transform: `translateY(${taglineY}px)`,
          marginBottom: 40,
          lineHeight: 1.4,
          position: "relative",
          zIndex: 1,
        }}
      >
        Detecte oportunidades de crédito
        <br />
        <span style={{ color: COLORS.text }}>antes da concorrência</span>
      </div>

      {/* Features grid */}
      <div
        style={{
          display: "flex",
          gap: 12,
          flexWrap: "wrap",
          justifyContent: "center",
          maxWidth: 700,
          opacity: featuresOpacity,
          marginBottom: 48,
          position: "relative",
          zIndex: 1,
        }}
      >
        {features.map((f, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 20px",
              borderRadius: 100,
              background: "rgba(59,130,246,0.1)",
              border: "1px solid rgba(59,130,246,0.25)",
              color: COLORS.text,
              fontSize: 14,
              fontWeight: 500,
            }}
          >
            <span>{f.icon}</span>
            {f.label}
          </div>
        ))}
      </div>

      {/* CTA */}
      {frame > 75 && (
        <div
          style={{
            display: "flex",
            gap: 16,
            opacity: ctaSpring,
            transform: `scale(${ctaSpring})`,
            position: "relative",
            zIndex: 1,
          }}
        >
          <div
            style={{
              padding: "16px 40px",
              background: `linear-gradient(135deg, ${COLORS.primary}, ${COLORS.accent})`,
              borderRadius: 14,
              color: "white",
              fontSize: 16,
              fontWeight: 700,
              boxShadow: `0 8px 30px rgba(59,130,246,0.4)`,
              letterSpacing: "0.3px",
            }}
          >
            Solicitar Demonstração
          </div>
          <div
            style={{
              padding: "16px 40px",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.15)",
              borderRadius: 14,
              color: COLORS.text,
              fontSize: 16,
              fontWeight: 600,
            }}
          >
            Ver Documentação
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
