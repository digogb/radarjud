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

const QUERY = "execução fiscal com penhora de imóvel";

const results = [
  {
    processo: "0023456-78.2024.8.26.0050",
    parte: "Banco Nacional S/A vs. Construtora Planalto",
    tribunal: "TJSP",
    score: 0.94,
    snippet: "...determinada a penhora do imóvel cadastrado no CRECI sob nº 847-SP, avaliado em R$ 1.200.000, em execução fiscal movida pela Fazenda Estadual...",
  },
  {
    processo: "9901234-56.2023.4.02.5101",
    parte: "Fazenda Nacional vs. Metalúrgica Sul",
    tribunal: "TRF-2",
    score: 0.91,
    snippet: "...auto de penhora e avaliação do bem imóvel situado na Av. Brasil, nº 4500, para garantia da execução fiscal no valor de R$ 890.000...",
  },
  {
    processo: "5678901-23.2024.8.19.0200",
    parte: "INSS vs. Transportes Rápidos Ltda",
    tribunal: "TJRJ",
    score: 0.87,
    snippet: "...expedido mandado de penhora sobre imóvel comercial, bem de família não reconhecido, executado por débito fiscal previdenciário...",
  },
  {
    processo: "3344556-67.2022.8.13.0105",
    parte: "Fazenda Estadual vs. Supermercados Belo",
    tribunal: "TJMG",
    score: 0.83,
    snippet: "...imóvel penhorado para garantia de execução fiscal estadual, IPTU em atraso 2018-2023, avaliação judicial solicitada...",
  },
];

const ScoreBar: React.FC<{ score: number; animated: boolean }> = ({ score, animated }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
    <div
      style={{
        flex: 1,
        height: 4,
        background: "rgba(255,255,255,0.1)",
        borderRadius: 2,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: "100%",
          width: animated ? `${score * 100}%` : "0%",
          background: `linear-gradient(90deg, ${COLORS.primary}, ${COLORS.accent})`,
          borderRadius: 2,
          transition: "width 0.8s ease",
        }}
      />
    </div>
    <span
      style={{
        fontSize: 12,
        fontWeight: 700,
        color: score > 0.9 ? COLORS.success : COLORS.primary,
        minWidth: 36,
      }}
    >
      {(score * 100).toFixed(0)}%
    </span>
  </div>
);

export const BuscaSemanticaScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const typingProgress = interpolate(frame, [15, 55], [0, 1], { extrapolateRight: "clamp" });
  const queryText = QUERY.slice(0, Math.floor(typingProgress * QUERY.length));

  const showResults = frame > 65;
  const aiTagOpacity = interpolate(frame, [65, 80], [0, 1], { extrapolateRight: "clamp" });

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
        <NavItem icon="🔍" label="Busca" active />
        <NavItem icon="👥" label="Monitorados" />
        <NavItem icon="💡" label="Oportunidades" />
        <NavItem icon="⚙️" label="Parametrização" />
      </div>

      {/* Main */}
      <div style={{ flex: 1, padding: "32px 40px", overflow: "hidden" }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: COLORS.text, marginBottom: 4 }}>
            Busca Inteligente
          </div>
          <div style={{ fontSize: 14, color: COLORS.textSecondary }}>
            Pesquise por nome, número de processo ou descreva o que procura
          </div>
        </div>

        {/* Search mode toggle */}
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          <div
            style={{
              padding: "8px 20px",
              borderRadius: 10,
              background: "transparent",
              border: `1px solid ${COLORS.border}`,
              color: COLORS.textSecondary,
              fontSize: 13,
            }}
          >
            🔤 Busca Exata
          </div>
          <div
            style={{
              padding: "8px 20px",
              borderRadius: 10,
              background: "rgba(139,92,246,0.15)",
              border: `1px solid rgba(139,92,246,0.4)`,
              color: COLORS.purple,
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            ✨ Busca Semântica (IA)
          </div>
        </div>

        {/* Search box */}
        <div
          style={{
            background: COLORS.bgCard,
            border: `2px solid ${COLORS.purple}66`,
            borderRadius: 14,
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 16,
            boxShadow: `0 0 30px rgba(139,92,246,0.1)`,
          }}
        >
          <span style={{ fontSize: 20 }}>🔍</span>
          <div style={{ flex: 1, fontSize: 16, color: COLORS.text, display: "flex", alignItems: "center", gap: 2 }}>
            {queryText}
            <div style={{ width: 2, height: 20, background: COLORS.purple }} />
          </div>
          {frame > 55 && (
            <div
              style={{
                padding: "8px 20px",
                background: COLORS.purple,
                borderRadius: 8,
                color: "white",
                fontSize: 13,
                fontWeight: 600,
                opacity: interpolate(frame, [55, 65], [0, 1], { extrapolateRight: "clamp" }),
              }}
            >
              Buscar
            </div>
          )}
        </div>

        {/* AI description */}
        {frame > 60 && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 24,
              opacity: aiTagOpacity,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 14px",
                background: "rgba(139,92,246,0.1)",
                border: "1px solid rgba(139,92,246,0.3)",
                borderRadius: 100,
                color: COLORS.purple,
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              ✨ IA encontrou 4 publicações semanticamente relacionadas
            </div>
            <div style={{ fontSize: 12, color: COLORS.textSecondary }}>
              Usando embeddings em português jurídico (Nomic-embed)
            </div>
          </div>
        )}

        {/* Results */}
        {showResults && results.map((result, i) => {
          const rOpacity = interpolate(frame, [65 + i * 12, 80 + i * 12], [0, 1], { extrapolateRight: "clamp" });
          const rY = interpolate(frame, [65 + i * 12, 80 + i * 12], [15, 0], { extrapolateRight: "clamp" });

          return (
            <div
              key={i}
              style={{
                background: COLORS.bgCard,
                border: `1px solid ${COLORS.border}`,
                borderRadius: 14,
                padding: "18px 20px",
                marginBottom: 10,
                opacity: rOpacity,
                transform: `translateY(${rY}px)`,
              }}
            >
              <div style={{ display: "flex", gap: 12, marginBottom: 8, alignItems: "flex-start" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                    <span style={{ fontSize: 12, fontFamily: "monospace", color: COLORS.accent }}>
                      {result.processo}
                    </span>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: 100,
                        background: "rgba(139,92,246,0.15)",
                        color: COLORS.purple,
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      {result.tribunal}
                    </span>
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.text, marginBottom: 8 }}>
                    {result.parte}
                  </div>
                  <div style={{ fontSize: 13, color: COLORS.textSecondary, lineHeight: 1.5 }}>
                    {result.snippet}
                  </div>
                </div>
                <div style={{ minWidth: 120 }}>
                  <div style={{ fontSize: 11, color: COLORS.textSecondary, marginBottom: 4 }}>Relevância</div>
                  <ScoreBar score={result.score} animated={frame > 75 + i * 12} />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
