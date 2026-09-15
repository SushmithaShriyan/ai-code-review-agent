import { useEffect, useState } from "react";
import StatsBar from "./components/StatsBar.jsx";
import ReviewList from "./components/ReviewList.jsx";
import { fetchReviews, fetchStats } from "./api.js";

export default function App() {
  const [reviews, setReviews] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [reviewData, statsData] = await Promise.all([
          fetchReviews(),
          fetchStats(),
        ]);
        setReviews(reviewData);
        setStats(statsData);
      } catch (e) {
        setError(e.message);
      }
    }
    load();
    const interval = setInterval(load, 10000); // poll every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app">
      <div className="header">
        <h1>ai-code-review-agent</h1>
        <span className="tag">dashboard</span>
      </div>

      {error && (
        <div className="empty-state">
          Couldn't reach the backend ({error}). Make sure the FastAPI server is
          running on the URL set in VITE_API_URL.
        </div>
      )}

      {!error && (
        <>
          <StatsBar stats={stats} />
          <div className="section-label">Recent reviews</div>
          <ReviewList reviews={reviews} />
        </>
      )}
    </div>
  );
}
