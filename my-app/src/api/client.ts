export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const BASE_URL = "/api";

// Shared refresh promise to prevent concurrent refresh requests
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = localStorage.getItem("refreshToken");
  if (!refreshToken) throw new Error("No refresh token");

  const response = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) throw new Error("Refresh failed");

  const data = await response.json();
  localStorage.setItem("token", data.access_token);
  return data.access_token;
}

function clearAuthAndRedirect() {
  localStorage.removeItem("token");
  localStorage.removeItem("refreshToken");
  localStorage.removeItem("role");
  localStorage.removeItem("userId");
  localStorage.removeItem("classId");
  localStorage.removeItem("className");
  localStorage.removeItem("currentClassId");
  window.location.href = "/login";
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  };

  if (!(options?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && !path.startsWith("/auth/")) {
    // Attempt token refresh — coalesce concurrent calls into one promise
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }

    let newToken: string;
    try {
      newToken = await refreshPromise;
    } catch {
      clearAuthAndRedirect();
      throw new Error("认证已过期");
    }

    // Retry original request with new token — business errors propagate normally
    const retryHeaders: Record<string, string> = {
      ...(options?.headers as Record<string, string>),
      Authorization: `Bearer ${newToken}`,
    };
    if (!(options?.body instanceof FormData)) {
      retryHeaders["Content-Type"] = "application/json";
    }

    const retryResponse = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers: retryHeaders,
    });

    if (!retryResponse.ok) {
      const error = await retryResponse.json().catch(() => ({ detail: "请求失败" }));
      throw new ApiError(error.detail || "请求失败", retryResponse.status);
    }

    if (retryResponse.status === 204) {
      return undefined as T;
    }

    return retryResponse.json();
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new ApiError(error.detail || "请求失败", response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
