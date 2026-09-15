function severityCounts(issues) {
  const counts = { high: 0, medium: 0, low: 0 };
  for (const issue of issues || []) {
    counts[issue.severity] = (counts[issue.severity] || 0) + 1;
  }
  return counts;
}

export default function ReviewList({ reviews }) {
  if (!reviews || reviews.length === 0) {
    return (
      <div className="empty-state">
        No reviews yet. Open a pull request on a connected repo, or send a
        test payload to <code>POST /webhook/github</code> to see one appear here.
      </div>
    );
  }

  return (
    <div>
      {reviews.map((r) => {
        const counts = severityCounts(r.issues);
        return (
          <div className="review-card" key={r._id}>
            <div className="review-card-top">
              <span className="pr-title">{r.pr_title || `PR #${r.pr_number}`}</span>
              <span className="repo">{r.repo} · #{r.pr_number}</span>
            </div>
            <p className="summary">{r.summary}</p>
            <div className="badge-row">
              {counts.high > 0 && <span className="badge high">{counts.high} high</span>}
              {counts.medium > 0 && <span className="badge medium">{counts.medium} medium</span>}
              {counts.low > 0 && <span className="badge low">{counts.low} low</span>}
              {counts.high + counts.medium + counts.low === 0 && (
                <span className="badge low">clean</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
