const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

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
};
