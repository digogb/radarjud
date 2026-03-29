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
  purple: "#8b5cf6",
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

const oportunidades = [
  {
    processo: "1234567-89.2023.8.26.0100",
    parte: "Construtora Horizonte Ltda",
    tribunal: "TJSP",
    tipo: "Expedição de Precatório",
    data: "27/03/2026",
    valor: "R$ 284.500,00",
    badge: COLORS.success,
  },
  {
    processo: "9876543-21.2022.8.19.0001",
    parte: "Importadora Global S/A",
    tribunal: "TJRJ",
    tipo: "Alvará de Levantamento",
    data: "26/03/2026",
    valor: "R$ 67.200,00",
    badge: COLORS.warning,
  },
  {
    processo: "1122334-55.2024.4.03.6100",
    parte: "Distribuidora Alfa Ltda",
    tribunal: "TRF-3",
    tipo: "Mandado de Levantamento",
    data: "25/03/2026",
    valor: "R$ 1.230.000,00",
    badge: COLORS.accent,
  },
];

export const OportunidadesScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const showDrawer = frame > 110;
  const drawerSpring = spring({
    fps,
    frame: frame - 110,
    config: { damping: 14, stiffness: 100 },
    durationInFrames: 30,
  });

  const drawerX = interpolate(drawerSpring, [0, 1], [500, 0]);

  const summaryOpacity = interpolate(frame, [140, 165], [0, 1], { extrapolateRight: "clamp" });

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
        <NavItem icon="💡" label="Oportunidades" active />
        <NavItem icon="⚙️" label="Parametrização" />
      </div>

      {/* Main */}
      <div style={{ flex: 1, padding: "32px 40px", overflow: "hidden" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
          <div>
            <div style={{ fontSize: 28, fontWeight: 800, color: COLORS.text }}>Oportunidades de Crédito</div>
            <div style={{ fontSize: 14, color: COLORS.textSecondary, marginTop: 4 }}>
              18 processos com sinais de recebimento detectados
            </div>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            {["7 dias", "30 dias", "60 dias", "90 dias"].map((d, i) => (
              <div
                key={i}
                style={{
                  padding: "8px 16px",
                  borderRadius: 8,
                  background: i === 1 ? COLORS.primary : "transparent",
                  border: `1px solid ${i === 1 ? COLORS.primary : COLORS.border}`,
                  color: i === 1 ? "white" : COLORS.textSecondary,
                  fontSize: 13,
                  fontWeight: i === 1 ? 600 : 400,
                  cursor: "pointer",
                }}
              >
                {d}
              </div>
            ))}
          </div>
        </div>

        {/* Opportunity cards */}
        {oportunidades.map((op, i) => {
          const cardOpacity = interpolate(frame, [i * 15, i * 15 + 25], [0, 1], { extrapolateRight: "clamp" });
          const cardY = interpolate(frame, [i * 15, i * 15 + 25], [20, 0], { extrapolateRight: "clamp" });

          return (
            <div
              key={i}
              style={{
                background: i === 0 ? "#1a2332" : COLORS.bgCard,
                border: `1px solid ${i === 0 ? COLORS.success + "44" : COLORS.border}`,
                borderRadius: 16,
                padding: "20px 24px",
                marginBottom: 12,
                opacity: cardOpacity,
                transform: `translateY(${cardY}px)`,
                display: "flex",
                alignItems: "center",
                gap: 20,
                boxShadow: i === 0 ? `0 0 20px rgba(16,185,129,0.1)` : "none",
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                  <div
                    style={{
                      padding: "4px 12px",
                      borderRadius: 100,
                      background: op.badge + "22",
                      border: `1px solid ${op.badge}44`,
                      color: op.badge,
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    {op.tipo}
                  </div>
                  <div
                    style={{
                      padding: "4px 12px",
                      borderRadius: 100,
                      background: "rgba(139,92,246,0.15)",
                      color: COLORS.purple,
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    {op.tribunal}
                  </div>
                  <div style={{ fontSize: 12, color: COLORS.textSecondary }}>{op.data}</div>
                </div>
                <div style={{ fontSize: 16, fontWeight: 700, color: COLORS.text, marginBottom: 4 }}>
                  {op.parte}
                </div>
                <div style={{ fontSize: 12, color: COLORS.textSecondary, fontFamily: "monospace" }}>
                  {op.processo}
                </div>
              </div>
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 800,
                  color: COLORS.success,
                }}
              >
                {op.valor}
              </div>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  background: "rgba(255,255,255,0.05)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: COLORS.textSecondary,
                  fontSize: 16,
                }}
              >
                →
              </div>
            </div>
          );
        })}
      </div>

      {/* Drawer */}
      {showDrawer && (
        <div
          style={{
            position: "absolute",
            right: 0,
            top: 0,
            bottom: 0,
            width: 480,
            background: "#0f1929",
            borderLeft: `1px solid ${COLORS.border}`,
            padding: "32px",
            transform: `translateX(${drawerX}px)`,
            overflow: "hidden",
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 800, color: COLORS.text, marginBottom: 4 }}>
            Construtora Horizonte Ltda
          </div>
          <div style={{ fontSize: 12, color: COLORS.textSecondary, fontFamily: "monospace", marginBottom: 24 }}>
            1234567-89.2023.8.26.0100 · TJSP
          </div>

          {/* AI Summary Card */}
          <div
            style={{
              background: "#1a2332",
              border: "1px solid rgba(16,185,129,0.3)",
              borderRadius: 16,
              padding: "20px",
              marginBottom: 20,
              opacity: summaryOpacity,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 14,
              }}
            >
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 8,
                  background: "linear-gradient(135deg, #10b981, #06b6d4)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 14,
                }}
              >
                ✨
              </div>
              <span style={{ fontSize: 14, fontWeight: 700, color: COLORS.text }}>Resumo por IA</span>
              <span style={{ fontSize: 11, color: COLORS.accent, marginLeft: "auto" }}>⚡ Cache</span>
            </div>

            <div
              style={{
                display: "flex",
                gap: 8,
                marginBottom: 14,
                flexWrap: "wrap",
              }}
            >
              <span style={{ padding: "3px 10px", borderRadius: 100, background: "rgba(16,185,129,0.15)", color: COLORS.success, fontSize: 12, fontWeight: 600 }}>
                Crédito Identificado
              </span>
              <span style={{ padding: "3px 10px", borderRadius: 100, background: "rgba(59,130,246,0.15)", color: COLORS.primary, fontSize: 12 }}>
                Polo Ativo
              </span>
              <span style={{ padding: "3px 10px", borderRadius: 100, background: "rgba(16,185,129,0.1)", color: COLORS.success, fontSize: 12 }}>
                R$ 284.500,00 identificado
              </span>
            </div>

            <div style={{ fontSize: 13, color: COLORS.textSecondary, lineHeight: 1.7 }}>
              Execução de título extrajudicial. Expedição de precatório referente ao contrato de empreitada n° 2023/0847.
              Prazo para liquidação: 90 dias conforme publicação. <strong style={{ color: COLORS.text }}>Oportunidade de recebimento imediato identificada.</strong>
            </div>
          </div>

          {/* Publications */}
          <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.text, marginBottom: 12 }}>
            Histórico de Publicações (47)
          </div>
          {[
            { date: "27/03/2026", text: "Expedição de precatório — valor: R$ 284.500,00. Prazo para pagamento: 90 dias.", highlight: true },
            { date: "15/02/2026", text: "Sentença de procedência. Condenação ao pagamento de R$ 284.500,00.", highlight: false },
            { date: "03/01/2026", text: "Designada audiência de instrução para 10/02/2026.", highlight: false },
          ].map((pub, i) => (
            <div
              key={i}
              style={{
                padding: "12px 16px",
                background: pub.highlight ? "rgba(16,185,129,0.08)" : "rgba(255,255,255,0.03)",
                border: `1px solid ${pub.highlight ? "rgba(16,185,129,0.3)" : COLORS.border}`,
                borderRadius: 10,
                marginBottom: 8,
              }}
            >
              <div style={{ fontSize: 11, color: COLORS.textSecondary, marginBottom: 4 }}>{pub.date}</div>
              <div style={{ fontSize: 12, color: COLORS.textSecondary, lineHeight: 1.5 }}>{pub.text}</div>
            </div>
          ))}
        </div>
      )}
    </AbsoluteFill>
  );
};
