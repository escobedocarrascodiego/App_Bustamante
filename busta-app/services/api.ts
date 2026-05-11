import { API_BASE_URL } from '@/constants/config';

export type TokenPair = { access: string; refresh: string };

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
  token?: string | null;
  auth?: boolean;
};

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, data: unknown, message?: string) {
    super(message ?? `Error ${status}`);
    this.status = status;
    this.data = data;
  }
}

type TokenProvider = {
  getAccess: () => string | null;
  getRefresh: () => string | null;
  setTokens: (tokens: TokenPair) => Promise<void> | void;
  onUnauthorized?: () => void;
};

let tokenProvider: TokenProvider | null = null;

export function configureApi(provider: TokenProvider) {
  tokenProvider = provider;
}

async function refreshAccess(): Promise<string | null> {
  if (!tokenProvider) return null;
  const refresh = tokenProvider.getRefresh();
  if (!refresh) return null;
  const res = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { access: string };
  await tokenProvider.setTokens({ access: data.access, refresh });
  return data.access;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, token, auth = true, headers, ...rest } = options;

  const buildHeaders = (accessToken?: string | null): HeadersInit => {
    const h: Record<string, string> = {
      Accept: 'application/json',
      ...(headers as Record<string, string> | undefined),
    };
    if (body !== undefined && !(body instanceof FormData)) {
      h['Content-Type'] = 'application/json';
    }
    const resolvedToken = token ?? (auth ? tokenProvider?.getAccess() : null);
    if (resolvedToken) h.Authorization = `Bearer ${resolvedToken}`;
    return h;
  };

  const doFetch = async (accessToken?: string | null) => {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      headers: buildHeaders(accessToken),
      body:
        body === undefined
          ? undefined
          : body instanceof FormData
            ? (body as unknown as BodyInit)
            : JSON.stringify(body),
    });
    return res;
  };

  let response = await doFetch();

  if (response.status === 401 && auth && tokenProvider?.getRefresh()) {
    const newAccess = await refreshAccess();
    if (newAccess) {
      response = await doFetch(newAccess);
    } else {
      tokenProvider?.onUnauthorized?.();
    }
  }

  if (response.status === 204) {
    return undefined as T;
  }

  let data: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, data);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PATCH', body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PUT', body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'DELETE' }),
};
