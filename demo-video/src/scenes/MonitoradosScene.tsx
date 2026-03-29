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
  sidebar: "#0d1424",
};

const pessoas = [
  { nome: "Construtora Horizonte Ltda", doc: "12.345.678/0001-99", pubs: 47, alertas: 3, prox: "2h 14min", status: "ativo" },
  { nome: "João Carlos Mendes Silva", doc: "123.456.789-00", pubs: 12, alertas: 1, prox: "5h 50min", status: "ativo" },
  { nome: "Importadora Global S/A", doc: "98.765.432/0001-11", pubs: 89, alertas: 0, prox: "1h 03min", status: "ativo" },
  { nome: "Distribuidora Alfa Ltda", doc: "55.123.456/0001-77", pubs: 34, alertas: 7, prox: "3h 22min", status: "ativo" },
  { nome: "Maria Aparecida Santos", doc: "987.654.321-00", pubs: 8, alertas: 0, prox: "11h 05min", status: "ativo" },
];

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

export const MonitoradosScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const showModal = frame > 100;
  const modalSpring = spring({
    fps,
    frame: frame - 100,
    config: { damping: 14, stiffness: 120 },
    durationInFrames: 25,
  });

  const typingProgress = interpolate(frame, [115, 155], [0, 1], { extrapolateRight: "clamp" });
  const nameText = "Banco Nacional S/A".slice(0, Math.floor(typingProgress * 18));

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
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "linear-gradient(135deg, #3b82f6, #06b6d4)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>
            📡
          </div>
          <span style={{ fontSize: 18, fontWeight: 800, color: COLORS.text }}>RadarJud</span>
        </div>
        <NavItem icon="📊" label="Dashboard" />
        <NavItem icon="🔍" label="Busca" />
        <NavItem icon="👥" label="Monitorados" active />
        <NavItem icon="💡" label="Oportunidades" />
        <NavItem icon="⚙️" label="Parametrização" />
      </div>

      {/* Main */}
      <div style={{ flex: 1, padding: "32px 40px", overflow: "hidden" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
          <div>
            <div style={{ fontSize: 28, fontWeight: 800, color: COLORS.text }}>Monitorados</div>
            <div style={{ fontSize: 14, color: COLORS.textSecondary, marginTop: 4 }}>
              412 partes em monitoramento ativo
            </div>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <div
              style={{
                padding: "10px 20px",
                borderRadius: 10,
                border: `1px solid ${COLORS.border}`,
                color: COLORS.textSecondary,
                fontSize: 13,
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              📥 Importar Excel
            </div>
            <div
              style={{
                padding: "10px 20px",
                borderRadius: 10,
                background: COLORS.primary,
                color: "white",
                fontSize: 13,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: 8,
                boxShadow: `0 4px 16px rgba(59,130,246,0.4)`,
              }}
            >
              + Adicionar Parte
            </div>
          </div>
        </div>

        {/* Table */}
        <div
          style={{
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 16,
            overflow: "hidden",
          }}
        >
          {/* Table header */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1fr 1fr 1fr 80px",
              padding: "14px 24px",
              borderBottom: `1px solid ${COLORS.border}`,
              fontSize: 12,
              fontWeight: 600,
              color: COLORS.textSecondary,
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            <div>Nome / Documento</div>
            <div>Publicações</div>
            <div>Alertas</div>
            <div>Próx. Verificação</div>
            <div>Status</div>
          </div>

          {/* Rows */}
          {pessoas.map((p, i) => {
            const rowOpacity = interpolate(frame, [i * 12, i * 12 + 20], [0, 1], { extrapolateRight: "clamp" });
            const rowX = interpolate(frame, [i * 12, i * 12 + 20], [20, 0], { extrapolateRight: "clamp" });
            return (
              <div
                key={i}
                style={{
                  display: "grid",
                  gridTemplateColumns: "2fr 1fr 1fr 1fr 80px",
                  padding: "16px 24px",
                  borderBottom: i < pessoas.length - 1 ? `1px solid ${COLORS.border}` : "none",
                  opacity: rowOpacity,
                  transform: `translateX(${rowX}px)`,
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.text }}>{p.nome}</div>
                  <div style={{ fontSize: 12, color: COLORS.textSecondary, marginTop: 2 }}>{p.doc}</div>
                </div>
                <div style={{ fontSize: 14, color: COLORS.text, fontWeight: 600 }}>{p.pubs}</div>
                <div>
                  {p.alertas > 0 ? (
                    <span
                      style={{
                        background: "rgba(245,158,11,0.15)",
                        color: COLORS.warning,
                        padding: "3px 10px",
                        borderRadius: 100,
                        fontSize: 13,
                        fontWeight: 600,
                      }}
                    >
                      {p.alertas} novos
                    </span>
                  ) : (
                    <span style={{ color: COLORS.textSecondary, fontSize: 13 }}>—</span>
                  )}
                </div>
                <div style={{ fontSize: 13, color: COLORS.textSecondary }}>{p.prox}</div>
                <div>
                  <div
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: "50%",
                      background: COLORS.success,
                      boxShadow: `0 0 8px ${COLORS.success}`,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Add Modal */}
      {showModal && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backdropFilter: "blur(4px)",
          }}
        >
          <div
            style={{
              background: "#1a2332",
              border: `1px solid ${COLORS.border}`,
              borderRadius: 20,
              padding: "40px",
              width: 520,
              transform: `scale(${modalSpring})`,
              opacity: modalSpring,
              boxShadow: "0 40px 80px rgba(0,0,0,0.5)",
            }}
          >
            <div style={{ fontSize: 22, fontWeight: 800, color: COLORS.text, marginBottom: 8 }}>
              Adicionar Parte
            </div>
            <div style={{ fontSize: 14, color: COLORS.textSecondary, marginBottom: 28 }}>
              Cadastre o nome ou CNPJ/CPF para iniciar o monitoramento
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 13, color: COLORS.textSecondary, display: "block", marginBottom: 8, fontWeight: 500 }}>
                Nome da Parte *
              </label>
              <div
                style={{
                  background: COLORS.bgCard,
                  border: `1px solid ${COLORS.primary}`,
                  borderRadius: 10,
                  padding: "12px 16px",
                  color: COLORS.text,
                  fontSize: 15,
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                {nameText}
                <div
                  style={{
                    width: 2,
                    height: 18,
                    background: COLORS.primary,
                    animation: "blink 1s infinite",
                  }}
                />
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 13, color: COLORS.textSecondary, display: "block", marginBottom: 8, fontWeight: 500 }}>
                CNPJ / CPF (opcional)
              </label>
              <div
                style={{
                  background: COLORS.bgCard,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 10,
                  padding: "12px 16px",
                  color: COLORS.textSecondary,
                  fontSize: 15,
                }}
              >
                Deixe em branco para buscar apenas pelo nome
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 28 }}>
              <div>
                <label style={{ fontSize: 13, color: COLORS.textSecondary, display: "block", marginBottom: 8, fontWeight: 500 }}>
                  Frequência
                </label>
                <div
                  style={{
                    background: COLORS.bgCard,
                    border: `1px solid ${COLORS.border}`,
                    borderRadius: 10,
                    padding: "12px 16px",
                    color: COLORS.text,
                    fontSize: 14,
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  A cada 12 horas <span>▾</span>
                </div>
              </div>
              <div>
                <label style={{ fontSize: 13, color: COLORS.textSecondary, display: "block", marginBottom: 8, fontWeight: 500 }}>
                  Validade
                </label>
                <div
                  style={{
                    background: COLORS.bgCard,
                    border: `1px solid ${COLORS.border}`,
                    borderRadius: 10,
                    padding: "12px 16px",
                    color: COLORS.text,
                    fontSize: 14,
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  31/12/2026 <span>📅</span>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 12 }}>
              <div
                style={{
                  flex: 1,
                  padding: "12px",
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 10,
                  color: COLORS.textSecondary,
                  fontSize: 14,
                  fontWeight: 500,
                  textAlign: "center",
                }}
              >
                Cancelar
              </div>
              <div
                style={{
                  flex: 1,
                  padding: "12px",
                  background: COLORS.primary,
                  borderRadius: 10,
                  color: "white",
                  fontSize: 14,
                  fontWeight: 600,
                  textAlign: "center",
                  boxShadow: `0 4px 16px rgba(59,130,246,0.4)`,
                }}
              >
                Adicionar e Monitorar
              </div>
            </div>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
