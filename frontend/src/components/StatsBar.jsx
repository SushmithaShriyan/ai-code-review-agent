export default function StatsBar({ stats }) {
  if (!stats) return null;

  const items = [
    { label: "reviews run", value: stats.total_reviews },
    { label: "issues found", value: stats.total_issues },
    { label: "high severity", value: stats.issues_by_severity?.high ?? 0 },
    { label: "avg latency (ms)", value: stats.avg_latency_ms },
  ];

  return (
    <div className="stats-row">
      {items.map((item) => (
        <div className="stat-card" key={item.label}>
          <div className="value">{item.value}</div>
          <div className="label">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
