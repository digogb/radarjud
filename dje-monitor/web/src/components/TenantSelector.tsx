/**
 * Seletor de Tenant — aparece quando o usuário não tem tenant configurado
 * ou quando VITE_ADMIN_MODE=true (permite trocar de tenant).
 */

import { useState } from 'react';
import { useTenant } from '../contexts/TenantContext';

interface TenantSelectorProps {
    /** Se true, mostra o formulário para configurar o tenant_id */
    forceShow?: boolean;
}

export function TenantSelector({ forceShow }: TenantSelectorProps) {
    const { tenantId, setTenant, clearTenant } = useTenant();
    const [input, setInput] = useState(tenantId || '');
    const isAdminMode = import.meta.env.VITE_ADMIN_MODE === 'true';

    if (!forceShow && !isAdminMode && tenantId) {
        return null;
    }

    const handleSave = () => {
        if (input.trim()) {
            setTenant(input.trim());
            window.location.reload();
        }
    };

    return (
        <div style={{
            padding: '12px 16px',
            background: '#1e293b',
            borderBottom: '1px solid #334155',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
        }}>
            <span style={{ color: '#94a3b8', fontSize: '13px' }}>Tenant ID:</span>
            <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="UUID do tenant"
                style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    border: '1px solid #475569',
                    background: '#0f172a',
                    color: '#e2e8f0',
                    fontSize: '12px',
                    width: '300px',
                    fontFamily: 'monospace',
                }}
                onKeyDown={e => e.key === 'Enter' && handleSave()}
            />
            <button
                onClick={handleSave}
                style={{
                    padding: '4px 12px',
                    background: '#3b82f6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px',
                }}
            >
                Aplicar
            </button>
            {tenantId && (
                <button
                    onClick={() => { clearTenant(); window.location.reload(); }}
                    style={{
                        padding: '4px 8px',
                        background: '#ef4444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px',
                    }}
                >
                    Limpar
                </button>
            )}
        </div>
    );
}

/**
 * Banner exibido quando não há tenant configurado.
 */
export function TenantRequiredBanner() {
    const { hasTenant } = useTenant();

    if (hasTenant) return null;

    return (
        <div style={{
            background: '#dc2626',
            color: 'white',
            padding: '12px 20px',
            textAlign: 'center',
            fontSize: '14px',
        }}>
            ⚠️ Tenant não configurado. Defina <code>VITE_TENANT_ID</code> no ambiente
            ou configure via localStorage (<code>dje_tenant_id</code>).
            {import.meta.env.VITE_ADMIN_MODE === 'true' && (
                <span> Use o seletor acima para configurar.</span>
            )}
        </div>
    );
}
