/**
 * Contexto de autenticação.
 *
 * - access_token: armazenado em memória (estado React) — não persiste entre abas
 * - refresh_token: armazenado em sessionStorage — persiste apenas na aba atual
 *
 * O access_token também é exposto via módulo `auth_token_store` para uso
 * no interceptor Axios (que não tem acesso ao React Context).
 */

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { authApi } from '../services/api';
import { setAccessToken as setAxiosToken, getAccessToken, clearAccessToken } from '../services/auth_token_store';

export interface UserInfo {
  id: string;
  name: string;
  email: string;
  role: string;
  tenant_id: string;
  tenant_name: string;
  must_change_password: boolean;
}

interface AuthState {
  accessToken: string | null;
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshTokens: () => Promise<void>;
}

const REFRESH_TOKEN_KEY = 'dje_refresh_token';

function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

function setRefreshToken(token: string): void {
  sessionStorage.setItem(REFRESH_TOKEN_KEY, token);
}

function clearRefreshToken(): void {
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    accessToken: null,
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Tentativa de restaurar sessão ao carregar (refresh_token em sessionStorage)
  useEffect(() => {
    const storedRefresh = getRefreshToken();
    if (storedRefresh) {
      authApi.refresh(storedRefresh)
        .then(({ access_token, refresh_token }) => {
          setRefreshToken(refresh_token);
          setAxiosToken(access_token);
          return authApi.me(access_token);
        })
        .then((user) => {
          setState(prev => ({
            ...prev,
            accessToken: getAccessToken(),
            user,
            isAuthenticated: true,
            isLoading: false,
          }));
        })
        .catch(() => {
          clearRefreshToken();
          clearAccessToken();
          setState(prev => ({ ...prev, isLoading: false }));
        });
    } else {
      setState(prev => ({ ...prev, isLoading: false }));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await authApi.login(email, password);
    setRefreshToken(result.refresh_token);
    setAxiosToken(result.access_token);
    setState({
      accessToken: result.access_token,
      user: result.user,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const logout = useCallback(async () => {
    const refresh = getRefreshToken();
    try {
      if (refresh) {
        await authApi.logout(refresh);
      }
    } catch {
      // Ignorar erros no logout
    } finally {
      clearRefreshToken();
      clearAccessToken();
      setState({
        accessToken: null,
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  }, []);

  const refreshTokens = useCallback(async () => {
    const refresh = getRefreshToken();
    if (!refresh) throw new Error('No refresh token');
    const result = await authApi.refresh(refresh);
    setRefreshToken(result.refresh_token);
    setAxiosToken(result.access_token);
    setState(prev => ({ ...prev, accessToken: result.access_token }));
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refreshTokens }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
