/**
 * Store de access token em módulo singleton.
 *
 * Permite que o interceptor Axios (módulo-nível) acesse o access_token
 * que está armazenado em memória no React Context.
 *
 * Não é persistido em nenhum storage — apenas em memória JS.
 */

let _accessToken: string | null = null;

export function setAccessToken(token: string): void {
  _accessToken = token;
}

export function getAccessToken(): string | null {
  return _accessToken;
}

export function clearAccessToken(): void {
  _accessToken = null;
}
