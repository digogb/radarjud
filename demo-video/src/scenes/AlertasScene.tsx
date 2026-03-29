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
  warning: "#f59e0b",
  text: "#f0f6fc",
  textSecondary: "#94a3b8",
  border: "rgba(255,255,255,0.08)",
};

const alerts = [
  {
    tipo: "OPORTUNIDADE_CREDITO",
    parte: "Construtora Horizonte Ltda",
    processo: "1234567-89.2023.8.26.0100",
    tribunal: "TJSP",
    resumo: "Expedição de precatório — R$ 284.500,00",
    tempo: "2 min atrás",
  },
  {
    tipo: "NOVA_PUBLICACAO",
    parte: "João Carlos Mendes Silva",
    processo: "9876543-21.2022.8.19.0001",
    tribunal: "TJRJ",
    resumo: "Designada nova data de audiência para 15/04/2026",
    tempo: "18 min atrás",
  },
  {
    tipo: "OPORTUNIDADE_CREDITO",
    parte: "Distribuidora Alfa Ltda",
    processo: "1122334-55.2024.4.03.6100",
    tribunal: "TRF-3",
    resumo: "Alvará de levantamento expedido — R$ 67.200,00",
    tempo: "45 min atrás",
  },
  {
    tipo: "NOVA_PUBLICACAO",
    parte: "Maria Aparecida Santos",
    processo: "5566778-99.2023.8.13.0200",
    tribunal: "TJMG",
    resumo: "Intimação para pagamento em 15 dias",
    tempo: "1h 20min atrás",
  },
];

export const AlertasScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleIn = spring({ fps, frame, config: { damping: 20, stiffness: 80 }, durationInFrames: 20 });

  // Telegram notification
  const showTelegram = frame > 95;
  const telegramSpring = spring({
    fps,
    frame: frame - 95,
    config: { damping: 12, stiffness: 150 },
    durationInFrames: 20,
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, #0d1117 0%, ${COLORS.bg} 100%)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        fontFamily: "'Inter', 'Segoe UI', sans-serif",
        padding: "60px 100px",
      }}
    >
      {/* Header */}
      <div
        style={{
          textAlign: "center",
          marginBottom: 48,
          opacity: titleIn,
          transform: `translateY(${interpolate(titleIn, [0, 1], [-20, 0])}px)`,
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "3px",
            color: COLORS.warning,
            textTransform: "uppercase",
            marginBottom: 12,
          }}
        >
          Alertas Inteligentes
        </div>
        <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text, letterSpacing: "-1px" }}>
          Notificado em tempo real
        </div>
        <div style={{ fontSize: 18, color: COLORS.textSecondary, marginTop: 10 }}>
          Telegram · E-mail · Interface Web
        </div>
      </div>

      {/* Alert cards */}
      <div style={{ width: "100%", maxWidth: 900 }}>
        {alerts.map((alert, i) => {
          const cardOpacity = interpolate(frame, [15 + i * 15, 35 + i * 15], [0, 1], { extrapolateRight: "clamp" });
          const cardX = interpolate(frame, [15 + i * 15, 35 + i * 15], [-30, 0], { extrapolateRight: "clamp" });
          const isOportunidade = alert.tipo === "OPORTUNIDADE_CREDITO";

          return (
            <div
              key={i}
              style={{
                background: COLORS.bgCard,
                border: `1px solid ${isOportunidade ? COLORS.success + "44" : COLORS.border}`,
                borderLeft: `4px solid ${isOportunidade ? COLORS.success : COLORS.primary}`,
                borderRadius: 14,
                padding: "16px 20px",
                marginBottom: 12,
                display: "flex",
                gap: 16,
                alignItems: "center",
                opacity: cardOpacity,
                transform: `translateX(${cardX}px)`,
                boxShadow: isOportunidade ? `0 4px 20px rgba(16,185,129,0.08)` : "none",
              }}
            >
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 12,
                  background: isOportunidade ? "rgba(16,185,129,0.15)" : "rgba(59,130,246,0.15)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 20,
                  flexShrink: 0,
                }}
              >
                {isOportunidade ? "💡" : "📋"}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: "3px 10px",
                      borderRadius: 100,
                      background: isOportunidade ? "rgba(16,185,129,0.15)" : "rgba(59,130,246,0.15)",
                      color: isOportunidade ? COLORS.success : COLORS.primary,
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                    }}
                  >
                    {isOportunidade ? "Oportunidade de Crédito" : "Nova Publicação"}
                  </span>
                  <span style={{ fontSize: 12, color: COLORS.textSecondary }}>{alert.tribunal}</span>
                </div>
                <div style={{ fontSize: 15, fontWeight: 600, color: COLORS.text, marginBottom: 2 }}>
                  {alert.parte}
                </div>
                <div style={{ fontSize: 13, color: COLORS.textSecondary }}>
                  {alert.resumo}
                </div>
              </div>

              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{ fontSize: 12, color: COLORS.textSecondary }}>{alert.tempo}</div>
                <div
                  style={{
                    marginTop: 6,
                    fontSize: 12,
                    color: COLORS.accent,
                    fontWeight: 500,
                  }}
                >
                  Ver processo →
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Telegram popup */}
      {showTelegram && (
        <div
          style={{
            position: "absolute",
            bottom: 50,
            right: 80,
            width: 360,
            background: "#212d40",
            borderRadius: 18,
            padding: "20px",
            boxShadow: "0 20px 60px rgba(0,0,0,0.6)",
            transform: `scale(${telegramSpring}) translateY(${interpolate(telegramSpring, [0, 1], [30, 0])}px)`,
            border: "1px solid rgba(255,255,255,0.1)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: "50%",
                background: "linear-gradient(135deg, #2196F3, #21CBF3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 20,
              }}
            >
              ✈️
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.text }}>RadarJud Bot</div>
              <div style={{ fontSize: 12, color: "#64b5f6" }}>Telegram</div>
            </div>
            <div style={{ marginLeft: "auto", fontSize: 12, color: COLORS.textSecondary }}>agora</div>
          </div>
          <div
            style={{
              background: "#2a3f57",
              borderRadius: 12,
              padding: "14px",
              fontSize: 13,
              color: COLORS.text,
              lineHeight: 1.6,
            }}
          >
            <strong style={{ color: COLORS.success }}>🚨 OPORTUNIDADE DE CRÉDITO</strong>
            <br />
            <strong>Construtora Horizonte Ltda</strong>
            <br />
            TJSP — Proc. 1234567-89.2023.8.26.0100
            <br />
            <span style={{ color: COLORS.warning }}>Expedição de precatório — R$ 284.500,00</span>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
