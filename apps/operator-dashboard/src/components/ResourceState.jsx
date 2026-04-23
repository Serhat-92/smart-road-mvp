export function LoadingState({ label = "Loading panel" }) {
  return (
    <div className="state-card panel">
      <div className="loading-line" />
      <p>{label}</p>
    </div>
  );
}

export function ErrorState({ error }) {
  return (
    <div className="state-card panel error-state">
      <h3>Data feed unavailable</h3>
      <p>{error.message}</p>
    </div>
  );
}

export function EmptyState({ title, description }) {
  return (
    <div className="state-card panel">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
