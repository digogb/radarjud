import axios from 'axios';

// Se VITE_API_URL estiver definido (mesmo vazio), usa ele. Caso contrário usa localhost:8000 (dev)
// Em produção (Docker), VITE_API_URL deve ser vazio para usar caminho relativo /api
const envUrl = import.meta.env.VITE_API_URL;
const API_URL = envUrl !== undefined ? envUrl : 'http://localhost:8000';

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

// ===== Monitoramento de Pessoas =====

export interface PessoaMonitorada {
    id: number;
    nome: string;
    cpf?: string;
    tribunal_filtro?: string;
    ativo: boolean;
    intervalo_horas: number;
    ultimo_check?: string;
    proximo_check?: string;
    total_publicacoes: number;
    total_alertas_nao_lidos: number;
    // Dados de origem (planilha)
    numero_processo?: string;
    comarca?: string;
    uf?: string;
    data_prazo?: string;
    data_expiracao?: string;
    origem_importacao?: string;
    criado_em: string;
    atualizado_em: string;
}

export interface ImportacaoStats {
    total: number;
    importados: number;
    pulados: number;
    erros: number;
    expirados_desativados?: number;
    dry_run?: boolean;
}

export interface PessoaMonitoradaCreate {
    nome: string;
    cpf?: string;
    tribunal_filtro?: string;
    intervalo_horas?: number;
}

export interface PublicacaoResumo {
    id: number;
    tribunal: string;
    numero_processo: string;
    data_disponibilizacao: string;
    orgao: string;
    tipo_comunicacao: string;
    texto_resumo: string;
    link?: string;
    criado_em: string;
}

export interface ProcessoGroup {
    numero_processo: string | null;
    tribunal: string | null;
    total: number;
    publicacoes: PublicacaoResumo[];
}

export interface AlertaItem {
    id: number;
    pessoa_id: number;
    pessoa_nome: string;
    tipo: string;
    titulo: string;
    descricao: string;
    lido: boolean;
    criado_em: string;
    lido_em?: string;
    publicacao?: PublicacaoResumo;
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

export const pessoaMonitoradaApi = {
    criar: async (data: PessoaMonitoradaCreate): Promise<PessoaMonitorada> => {
        const response = await api.post('/v1/pessoas-monitoradas', data);
        return response.data;
    },

    listar: async (ativo?: boolean): Promise<{ count: number; items: PessoaMonitorada[] }> => {
        const response = await api.get('/v1/pessoas-monitoradas', { params: { ativo } });
        return response.data;
    },

    obter: async (id: number): Promise<PessoaMonitorada> => {
        const response = await api.get(`/v1/pessoas-monitoradas/${id}`);
        return response.data;
    },

    atualizar: async (id: number, data: Partial<PessoaMonitoradaCreate> & { ativo?: boolean }): Promise<PessoaMonitorada> => {
        const response = await api.put(`/v1/pessoas-monitoradas/${id}`, data);
        return response.data;
    },

    remover: async (id: number): Promise<void> => {
        await api.delete(`/v1/pessoas-monitoradas/${id}`);
    },

    publicacoes: async (id: number): Promise<ProcessoGroup[]> => {
        const response = await api.get(`/v1/pessoas-monitoradas/${id}/publicacoes`);
        return response.data;
    },

    alertas: async (id: number, lido?: boolean): Promise<AlertaItem[]> => {
        const response = await api.get(`/v1/pessoas-monitoradas/${id}/alertas`, { params: { lido } });
        return response.data;
    },
};

export const alertaApi = {
    listar: async (params?: { pessoa_id?: number; lido?: boolean; limit?: number }): Promise<AlertaItem[]> => {
        const response = await api.get('/v1/alertas', { params });
        return response.data;
    },

    contarNaoLidos: async (pessoa_id?: number): Promise<number> => {
        const response = await api.get('/v1/alertas/nao-lidos/count', { params: { pessoa_id } });
        return response.data.count;
    },

    marcarLidos: async (ids?: number[], todos?: boolean): Promise<{ marcados: number }> => {
        const response = await api.post('/v1/alertas/marcar-lidos', { ids, todos: todos ?? false });
        return response.data;
    },
};

// ===== Busca Semântica =====

export interface ProcessoPublicacao {
    id?: number;
    texto_resumo?: string;
    texto_completo?: string;
    data_disponibilizacao?: string;
    orgao?: string;
    tipo_comunicacao?: string;
    link?: string;
    polo_ativo?: string;
    polo_passivo?: string;
}

export interface SemanticResult {
    pub_id?: number;
    processo_id?: number;
    score: number;
    tribunal?: string;
    numero_processo?: string;
    data_disponibilizacao?: string;
    polo_ativo?: string;
    polo_passivo?: string;
    orgao?: string;
    tipo_comunicacao?: string;
    texto_resumo?: string;
    texto_completo?: string;
    polos?: { ativo?: string[]; passivo?: string[] };
    link?: string;
    total_publicacoes?: number;
    pessoa_id?: number;
    publicacoes?: ProcessoPublicacao[];
}

export interface SemanticResponse {
    query: string;
    tipo: string;
    total: number;
    results: SemanticResult[];
}

export interface SemanticStatusCollection {
    points: number;
    vectors: number;
    status: string;
}

export interface SemanticStatus {
    status: string;
    collections?: Record<string, SemanticStatusCollection>;
    message?: string;
}

export const semanticApi = {
    search: async (params: {
        q: string;
        tribunal?: string;
        pessoa_id?: number;
        limit?: number;
        score_threshold?: number;
        tipo?: 'publicacoes' | 'processos';
    }): Promise<SemanticResponse> => {
        const response = await api.get('/v1/search/semantic', { params });
        return response.data;
    },

    status: async (): Promise<SemanticStatus> => {
        const response = await api.get('/v1/search/semantic/status');
        return response.data;
    },

    reindex: async (): Promise<{ status: string }> => {
        const response = await api.post('/v1/search/reindex');
        return response.data;
    },
};

// ===== Oportunidades de Crédito =====

export interface OportunidadeItem {
    id: number;
    pessoa_id: number;
    pessoa_nome: string;
    tribunal: string;
    numero_processo: string;
    data_disponibilizacao: string;
    orgao: string;
    tipo_comunicacao: string;
    texto_resumo: string;
    texto_completo?: string;
    link?: string;
    padrao_detectado: string;
    criado_em: string;
}

export const oportunidadesApi = {
    buscar: async (params?: { dias?: number; limit?: number }): Promise<{ total: number; items: OportunidadeItem[] }> => {
        const response = await api.get('/v1/oportunidades', { params });
        return response.data;
    },

    varrer: async (): Promise<{ status: string }> => {
        const response = await api.post('/v1/oportunidades/varrer');
        return response.data;
    },
};

export const importacaoApi = {
    importarPlanilha: async (
        arquivo: File,
        options?: { dryRun?: boolean; desativarExpirados?: boolean; intervaloHoras?: number }
    ): Promise<ImportacaoStats> => {
        const formData = new FormData();
        formData.append('arquivo', arquivo);
        const params: Record<string, string> = {};
        if (options?.dryRun) params['dry_run'] = 'true';
        if (options?.desativarExpirados) params['desativar_expirados'] = 'true';
        if (options?.intervaloHoras) params['intervalo_horas'] = String(options.intervaloHoras);
        const response = await api.post('/v1/importar-planilha', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            params,
        });
        return response.data;
    },
};

export default api;
