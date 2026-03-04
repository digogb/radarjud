/**
 * Contexto de Tenant para o frontend DJE Monitor.
 *
 * Resolve o tenant via:
 * 1. localStorage (dje_tenant_id)
 * 2. VITE_TENANT_ID (build-time env var)
 * 3. query param ?tenant= (dev only)
 */

import React, { createContext, useContext, useState, useCallback } from 'react';

function getCurrentTenantId(): string | null {
    return localStorage.getItem('dje_tenant_id') ?? null;
}

function setCurrentTenantId(id: string): void {
    localStorage.setItem('dje_tenant_id', id);
}

interface TenantContextType {
    tenantId: string | null;
    setTenant: (id: string) => void;
    clearTenant: () => void;
    hasTenant: boolean;
}

const TenantContext = createContext<TenantContextType | null>(null);

export function TenantProvider({ children }: { children: React.ReactNode }) {
    const [tenantId, setTenantIdState] = useState<string | null>(() => getCurrentTenantId());

    const setTenant = useCallback((id: string) => {
        setCurrentTenantId(id);
        setTenantIdState(id);
    }, []);

    const clearTenant = useCallback(() => {
        localStorage.removeItem('dje_tenant_id');
        setTenantIdState(null);
    }, []);

    return (
        <TenantContext.Provider value={{
            tenantId,
            setTenant,
            clearTenant,
            hasTenant: !!tenantId,
        }}>
            {children}
        </TenantContext.Provider>
    );
}

export function useTenant(): TenantContextType {
    const ctx = useContext(TenantContext);
    if (!ctx) {
        throw new Error('useTenant deve ser usado dentro de <TenantProvider>');
    }
    return ctx;
}
