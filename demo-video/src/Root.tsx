import React from "react";
import { Composition, Series } from "remotion";
import { IntroScene } from "./scenes/IntroScene";
import { ProblemScene } from "./scenes/ProblemScene";
import { DashboardScene } from "./scenes/DashboardScene";
import { MonitoradosScene } from "./scenes/MonitoradosScene";
import { AlertasScene } from "./scenes/AlertasScene";
import { OportunidadesScene } from "./scenes/OportunidadesScene";
import { BuscaSemanticaScene } from "./scenes/BuscaSemanticaScene";
import { ParametrizacaoScene } from "./scenes/ParametrizacaoScene";
import { OutroScene } from "./scenes/OutroScene";

// Scene durations at 30fps
const INTRO = 90;           // 3s
const PROBLEM = 150;        // 5s
const DASHBOARD = 180;      // 6s
const MONITORADOS = 210;    // 7s
const ALERTAS = 150;        // 5s
const OPORTUNIDADES = 210;  // 7s
const BUSCA = 180;          // 6s
const PARAMETRIZACAO = 150; // 5s
const OUTRO = 150;          // 5s

const TOTAL = INTRO + PROBLEM + DASHBOARD + MONITORADOS + ALERTAS + OPORTUNIDADES + BUSCA + PARAMETRIZACAO + OUTRO;

export const DemoVideo: React.FC = () => {
  return (
    <Series>
      <Series.Sequence durationInFrames={INTRO}>
        <IntroScene />
      </Series.Sequence>
      <Series.Sequence durationInFrames={PROBLEM}>
        <ProblemScene />
      </Series.Sequence>
      <Series.Sequence durationInFrames={DASHBOARD}>
        <DashboardScene />
      </Series.Sequence>
      <Series.Sequence durationInFrames={MONITORADOS}>
        <MonitoradosScene />
      </Series.Sequence>
      <Series.Sequence durationInFrames={ALERTAS}>
        <AlertasScene />
      </Series.Sequence>
      <Series.Sequence durationInFrames={OPORTUNIDADES}>
        <OportunidadesScene />
      </Series.Sequence>
      <Series.Sequence durationInFrames={BUSCA}>
        <BuscaSemanticaScene />
      </Series.Sequence>
      <Series.Sequence durationInFrames={PARAMETRIZACAO}>
        <ParametrizacaoScene />
      </Series.Sequence>
      <Series.Sequence durationInFrames={OUTRO}>
        <OutroScene />
      </Series.Sequence>
    </Series>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="DemoVideo"
        component={DemoVideo}
        durationInFrames={TOTAL}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{}}
      />
    </>
  );
};
