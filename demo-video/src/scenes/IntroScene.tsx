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
  text: "#f0f6fc",
  textSecondary: "#94a3b8",
};

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({
    fps,
    frame,
    config: { damping: 12, stiffness: 100 },
    durationInFrames: 30,
  });

  const taglineOpacity = interpolate(frame, [25, 50], [0, 1], {
    extrapolateRight: "clamp",
  });

  const taglineY = interpolate(frame, [25, 50], [20, 0], {
    extrapolateRight: "clamp",
  });

  const subtitleOpacity = interpolate(frame, [45, 70], [0, 1], {
    extrapolateRight: "clamp",
  });

  const glowOpacity = interpolate(frame, [0, 30, 90], [0, 0.6, 0.8], {
    extrapolateRight: "clamp",
  });

  const badgeOpacity = interpolate(frame, [60, 80], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at 50% 40%, #0f2044 0%, ${COLORS.bg} 70%)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Inter', 'Segoe UI', sans-serif",
      }}
    >
      {/* Glow effect */}
      <div
        style={{
          position: "absolute",
          width: 600,
          height: 600,
          borderRadius: "50%",
          background: `radial-gradient(circle, rgba(59,130,246,${glowOpacity}) 0%, transparent 70%)`,
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
        }}
      />

      {/* Grid lines */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `linear-gradient(rgba(59,130,246,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59,130,246,0.05) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />

      {/* Logo */}
      <div
        style={{
          transform: `scale(${logoScale})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
          position: "relative",
          zIndex: 1,
        }}
      >
        {/* Icon */}
        <div
          style={{
            width: 120,
            height: 120,
            borderRadius: 28,
            background: `linear-gradient(135deg, ${COLORS.primary}, ${COLORS.accent})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: `0 0 60px rgba(59,130,246,0.5), 0 20px 40px rgba(0,0,0,0.4)`,
          }}
        >
          {/* Radar icon */}
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="28" stroke="white" strokeWidth="2" strokeOpacity="0.3" />
            <circle cx="32" cy="32" r="18" stroke="white" strokeWidth="2" strokeOpacity="0.5" />
            <circle cx="32" cy="32" r="8" stroke="white" strokeWidth="2" strokeOpacity="0.8" />
            <circle cx="32" cy="32" r="3" fill="white" />
            <line x1="32" y1="32" x2="32" y2="4" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M32 32 L52 16" stroke="white" strokeWidth="2" strokeOpacity="0.6" strokeLinecap="round" />
          </svg>
        </div>

        {/* Title */}
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            color: COLORS.text,
            letterSpacing: "-2px",
            lineHeight: 1,
          }}
        >
          Radar
          <span
            style={{
              background: `linear-gradient(135deg, ${COLORS.primary}, ${COLORS.accent})`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Jud
          </span>
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 26,
            color: COLORS.textSecondary,
            fontWeight: 400,
            opacity: taglineOpacity,
            transform: `translateY(${taglineY}px)`,
            letterSpacing: "0.5px",
          }}
        >
          Monitoramento Inteligente do Diário da Justiça
        </div>

        {/* Subtitle */}
        <div
          style={{
            fontSize: 18,
            color: COLORS.accent,
            fontWeight: 500,
            opacity: subtitleOpacity,
            marginTop: 8,
          }}
        >
          Detecte oportunidades antes da concorrência
        </div>
      </div>

      {/* Feature badges */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          display: "flex",
          gap: 20,
          opacity: badgeOpacity,
        }}
      >
        {["IA Integrada", "Cobertura Nacional", "Tempo Real", "Multi-Tenant"].map((badge, i) => (
          <div
            key={i}
            style={{
              padding: "8px 20px",
              borderRadius: 100,
              background: "rgba(59,130,246,0.15)",
              border: "1px solid rgba(59,130,246,0.3)",
              color: COLORS.text,
              fontSize: 14,
              fontWeight: 500,
            }}
          >
            {badge}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
