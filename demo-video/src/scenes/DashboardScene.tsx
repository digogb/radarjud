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
  bgCardHover: "#1a2332",
  primary: "#3b82f6",
  accent: "#06b6d4",
  success: "#10b981",
  warning: "#f59e0b",
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
    {active && (
      <div
        style={{
          marginLeft: "auto",
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: COLORS.primary,
        }}
      />
    )}
  </div>
);

const StatCard: React.FC<{
  label: string;
  value: string;
  change: string;
  changePositive: boolean;
  color: string;
  icon: string;
  animValue: number;
}> = ({ label, value, change, changePositive, color, icon, animValue }) => (
  <div
    style={{
      background: COLORS.bgCard,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 16,
      padding: "24px",
      flex: 1,
      transform: `scale(${interpolate(animValue, [0, 1], [0.9, 1])})`,
      opacity: animValue,
    }}
  >
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: 16,
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 12,
          background: `${color}22`,
          border: `1px solid ${color}44`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 20,
        }}
      >
        {icon}
      </div>
      <div
        style={{
          fontSize: 12,
          color: changePositive ? COLORS.success : COLORS.danger,
          fontWeight: 600,
          background: changePositive ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
          padding: "3px 10px",
          borderRadius: 100,
        }}
      >
        {change}
      </div>
    </div>
    <div style={{ fontSize: 34, fontWeight: 800, color: COLORS.text, lineHeight: 1 }}>
      {value}
    </div>
    <div style={{ fontSize: 13, color: COLORS.textSecondary, marginTop: 6 }}>{label}</div>
  </div>
);

const ActivityItem: React.FC<{ name: string; court: string; time: string; type: string; opacity: number }> = ({
  name, court, time, type, opacity
}) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      padding: "12px 0",
      borderBottom: `1px solid ${COLORS.border}`,
      gap: 12,
      opacity,
    }}
  >
    <div
      style={{
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: type === "OPORTUNIDADE" ? COLORS.success : COLORS.primary,
        flexShrink: 0,
      }}
    />
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.text }}>{name}</div>
      <div style={{ fontSize: 12, color: COLORS.textSecondary }}>{court}</div>
    </div>
    <div
      style={{
        fontSize: 11,
        padding: "3px 10px",
        borderRadius: 100,
        background: type === "OPORTUNIDADE" ? "rgba(16,185,129,0.15)" : "rgba(59,130,246,0.15)",
        color: type === "OPORTUNIDADE" ? COLORS.success : COLORS.primary,
        fontWeight: 600,
        whiteSpace: "nowrap",
      }}
    >
      {type === "OPORTUNIDADE" ? "Oportunidade" : "Nova Publicação"}
    </div>
    <div style={{ fontSize: 11, color: COLORS.textSecondary, whiteSpace: "nowrap" }}>{time}</div>
  </div>
);

export const DashboardScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pageIn = spring({ fps, frame, config: { damping: 20, stiffness: 80 }, durationInFrames: 25 });

  const stat1 = spring({ fps, frame: frame - 20, config: { damping: 14, stiffness: 80 }, durationInFrames: 30 });
  const stat2 = spring({ fps, frame: frame - 30, config: { damping: 14, stiffness: 80 }, durationInFrames: 30 });
  const stat3 = spring({ fps, frame: frame - 40, config: { damping: 14, stiffness: 80 }, durationInFrames: 30 });
  const stat4 = spring({ fps, frame: frame - 50, config: { damping: 14, stiffness: 80 }, durationInFrames: 30 });

  const activityOpacity1 = interpolate(frame, [60, 75], [0, 1], { extrapolateRight: "clamp" });
  const activityOpacity2 = interpolate(frame, [70, 85], [0, 1], { extrapolateRight: "clamp" });
  const activityOpacity3 = interpolate(frame, [80, 95], [0, 1], { extrapolateRight: "clamp" });
  const activityOpacity4 = interpolate(frame, [90, 105], [0, 1], { extrapolateRight: "clamp" });
  const activityOpacity5 = interpolate(frame, [100, 115], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        background: COLORS.bg,
        fontFamily: "'Inter', 'Segoe UI', sans-serif",
        display: "flex",
        opacity: interpolate(pageIn, [0, 1], [0.5, 1]),
      }}
    >
      {/* Sidebar */}
      <div
        style={{
          width: 220,
          background: COLORS.sidebar,
          borderRight: `1px solid ${COLORS.border}`,
          padding: "24px 16px",
          display: "flex",
          flexDirection: "column",
          gap: 4,
          flexShrink: 0,
        }}
      >
        {/* Logo */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "12px 8px",
            marginBottom: 24,
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: `linear-gradient(135deg, #3b82f6, #06b6d4)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18,
            }}
          >
            📡
          </div>
          <span style={{ fontSize: 18, fontWeight: 800, color: COLORS.text }}>RadarJud</span>
        </div>

        <NavItem icon="📊" label="Dashboard" active />
        <NavItem icon="🔍" label="Busca" />
        <NavItem icon="👥" label="Monitorados" />
        <NavItem icon="💡" label="Oportunidades" />
        <NavItem icon="⚙️" label="Parametrização" />
      </div>

      {/* Main content */}
      <div style={{ flex: 1, padding: "32px 40px", overflow: "hidden" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
          <div>
            <div style={{ fontSize: 28, fontWeight: 800, color: COLORS.text }}>Dashboard</div>
            <div style={{ fontSize: 14, color: COLORS.textSecondary, marginTop: 4 }}>
              Última sincronização: há 12 minutos
            </div>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "rgba(16,185,129,0.15)",
              border: "1px solid rgba(16,185,129,0.3)",
              padding: "8px 16px",
              borderRadius: 10,
              color: COLORS.success,
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: COLORS.success,
                boxShadow: `0 0 6px ${COLORS.success}`,
              }}
            />
            Sistema Ativo
          </div>
        </div>

        {/* Stat cards */}
        <div style={{ display: "flex", gap: 16, marginBottom: 32 }}>
          <StatCard
            label="Total de Publicações"
            value="3.847"
            change="+127 hoje"
            changePositive
            color={COLORS.primary}
            icon="📄"
            animValue={stat1}
          />
          <StatCard
            label="Alertas Não Lidos"
            value="23"
            change="+8 novas"
            changePositive={false}
            color={COLORS.warning}
            icon="🔔"
            animValue={stat2}
          />
          <StatCard
            label="Partes Monitoradas"
            value="412"
            change="+5 esta semana"
            changePositive
            color={COLORS.success}
            icon="👥"
            animValue={stat3}
          />
          <StatCard
            label="Oportunidades Detectadas"
            value="18"
            change="+3 hoje"
            changePositive
            color={COLORS.accent}
            icon="💡"
            animValue={stat4}
          />
        </div>

        {/* Activity section */}
        <div
          style={{
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 16,
            padding: "24px",
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 700, color: COLORS.text, marginBottom: 16 }}>
            Atividade Recente
          </div>
          <ActivityItem
            name="Construtora Horizonte Ltda"
            court="TJSP — 3ª Vara Cível"
            time="há 8 min"
            type="OPORTUNIDADE"
            opacity={activityOpacity1}
          />
          <ActivityItem
            name="João Carlos Mendes Silva"
            court="TJRJ — 15ª Vara de Execução"
            time="há 23 min"
            type="PUBLICACAO"
            opacity={activityOpacity2}
          />
          <ActivityItem
            name="Importadora Global S/A"
            court="TRF-3 — 2ª Vara Federal"
            time="há 41 min"
            type="OPORTUNIDADE"
            opacity={activityOpacity3}
          />
          <ActivityItem
            name="Maria Aparecida Santos"
            court="TJMG — 7ª Vara Cível"
            time="há 1h 12min"
            type="PUBLICACAO"
            opacity={activityOpacity4}
          />
          <ActivityItem
            name="Distribuidora Alfa Ltda"
            court="TJCE — 4ª Vara Empresarial"
            time="há 2h 05min"
            type="PUBLICACAO"
            opacity={activityOpacity5}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
