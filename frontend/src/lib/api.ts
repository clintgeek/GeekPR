const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const BASEGEEK_LOGIN =
  process.env.NEXT_PUBLIC_BASEGEEK_LOGIN_URL || "https://basegeek.clintgeek.com/";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    // Send the basegeek session cookie (geek_token, Domain=.clintgeek.com)
    // on every API call so the backend can verify the session.
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (res.status === 401) {
    // Session missing or expired. Bounce to basegeek login; it'll send
    // the user back here after auth. The middleware catches the same
    // case server-side before the page even renders; this branch handles
    // session-expiry-mid-session.
    if (typeof window !== "undefined") {
      const here = encodeURIComponent(window.location.href);
      window.location.href = `${BASEGEEK_LOGIN}?redirect=${here}&app=geekpr`;
    }
    throw new Error("Unauthorized — redirecting to login");
  }

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export const api = {
  getReviews: (params?: { repo?: string; status?: string; skip?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.repo) query.set("repo", params.repo);
    if (params?.status) query.set("status", params.status);
    if (params?.skip) query.set("skip", String(params.skip));
    if (params?.limit) query.set("limit", String(params.limit));
    const queryStr = query.toString();
    return fetchAPI<any>(`/reviews/${queryStr ? "?" + queryStr : ""}`);
  },

  getReview: (id: number) => fetchAPI<any>(`/reviews/${id}`),

  getJobs: (params?: { repo?: string; status?: string }) => {
    const query = new URLSearchParams();
    if (params?.repo) query.set("repo", params.repo);
    if (params?.status) query.set("status", params.status);
    const queryStr = query.toString();
    return fetchAPI<any>(`/jobs/${queryStr ? "?" + queryStr : ""}`);
  },

  getRepoConfig: (owner: string, name: string) =>
    fetchAPI<any>(`/config/${owner}/${name}`),

  updateRepoConfig: (owner: string, name: string, config: any) =>
    fetchAPI<any>(`/config/${owner}/${name}`, {
      method: "PUT",
      body: JSON.stringify(config),
    }),

  getCurrentUser: () => fetchAPI<{ user: any; auth_mode: string }>(`/auth/me`),
};
