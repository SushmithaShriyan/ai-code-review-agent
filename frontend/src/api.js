const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchReviews(limit = 20) {
  const res = await fetch(`${BASE_URL}/reviews?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch reviews");
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${BASE_URL}/reviews/stats`);
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}
