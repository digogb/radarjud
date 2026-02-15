import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

const api = axios.create({
    baseURL: `${API_URL}/api`,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Types - Novo formato organizado por instâncias
export interface MovimentacaoFormatada {
    data: string;
    movimentacao: string;
    detalhes?: string;
    codigoNacional?: number;
}

export interface InstanciaProcesso {
    grau: string;
    descricaoGrau: string;
    orgao: string;
    classe?: string;
    statusAtual?: string;
    ultimasMovimentacoes: MovimentacaoFormatada[];
}

export interface ProcessoFormatado {
    numeroProcesso: string;
    tribunal: string;
    assunto?: string;
    sistema?: string;
    formato?: string;
    dataAjuizamento?: string;
    dataUltimaAtualizacao?: string;
    valorCausa?: number;
    partes?: Parte[];
    instancias: InstanciaProcesso[];
}

// Tipo compatível com legado (para endpoints que ainda retornam formato antigo)
export interface Processo {
    id?: string;
    numeroUnificado?: string;
    numeroProcesso?: string; // novo formato
    tribunal: string;
    instancia?: string | number;
    instancias?: InstanciaProcesso[]; // novo formato
    classeNome?: string;
    orgaoJulgadorNome?: string;
    dataDistribuicao?: string;
    dataAjuizamento?: string; // novo formato
    dataUltimaAtualizacao?: string;
    valorCausa?: number;
    monitorado?: boolean;
    sistema?: string;
    formato?: string;
    assunto?: string; // novo formato
    partes: Parte[];
    movimentacoes?: Movimentacao[];
}

export interface Parte {
    id?: string;
    nome: string;
    documento?: string;
    polo: string;
    tipoParte?: string;
    tipo?: string; // novo formato
    tipoPessoa?: string;
    advogados?: { nome: string; oab?: string; inscricao?: string }[];
}

export interface Movimentacao {
    id?: string;
    data?: string; // novo formato
    dataHora?: string;
    codigoNacional?: number;
    descricao?: string;
    movimentacao?: string; // novo formato
    complemento?: string;
    detalhes?: string; // novo formato
}

export interface Assunto {
    id: string;
    codigoNacional: number;
    descricao: string;
    principal: boolean;
}

export interface AlteracaoDetectada {
    id: string;
    processoId: string;
    tipo: string;
    dadosAnteriores: Record<string, unknown>;
    dadosNovos: Record<string, unknown>;
    detectadoEm: string;
    visualizado: boolean;
    processo?: Processo;
}

export interface DashboardResumo {
    totalProcessos: number;
    processosMonitorados: number;
    alteracoesNaoVistas: number;
    ultimaSync: string | null;
}

// API functions
export const processoApi = {
    buscar: async (params: { numero?: string; cpf?: string; nome?: string; tribunal?: string }) => {
        // Adaptar para API DJEN
        // DJEN API endpoint: /api/v1/search?nome=...
        if (params.nome) {
            const response = await api.get('/v1/search', {
                params: {
                    nome: params.nome,
                    tribunal: params.tribunal
                }
            });
            // Adaptar resposta da API ({ count, results }) para array esperado pelo frontend
            return { data: response.data.results || [] };
        }
        // Fallback ou erro para outros tipos de busca não implementados ainda
        throw new Error("Apenas busca por nome está implementada no momento.");
    },

    listar: async (params?: { monitorado?: boolean; page?: number; limit?: number }) => {
        const response = await api.get('/processos', { params });
        return response.data;
    },

    obterPorId: async (id: string): Promise<Processo> => {
        const response = await api.get(`/processos/${id}`);
        return response.data;
    },

    obterMovimentacoes: async (id: string): Promise<Movimentacao[]> => {
        const response = await api.get(`/processos/${id}/movimentacoes`);
        return response.data;
    },

    monitorar: async (id: string): Promise<Processo> => {
        const response = await api.post(`/processos/${id}/monitorar`);
        return response.data;
    },

    desmonitorar: async (id: string): Promise<Processo> => {
        const response = await api.delete(`/processos/${id}/monitorar`);
        return response.data;
    },
};

export const dashboardApi = {
    getResumo: async (): Promise<DashboardResumo> => {
        const response = await api.get('/dashboard/resumo');
        return response.data;
    },

    getAlteracoes: async (limit?: number): Promise<AlteracaoDetectada[]> => {
        const response = await api.get('/dashboard/alteracoes', { params: { limit } });
        return response.data;
    },

    marcarVistas: async (ids?: string[]) => {
        const response = await api.post('/dashboard/alteracoes/marcar-vistas', { ids });
        return response.data;
    },

    getEstatisticasTribunais: async () => {
        const response = await api.get('/dashboard/estatisticas/tribunais');
        return response.data;
    },
};

export const syncApi = {
    forcar: async () => {
        const response = await api.post('/sync/forcar');
        return response.data;
    },

    getStatus: async () => {
        const response = await api.get('/sync/status');
        return response.data;
    },
};

export default api;
