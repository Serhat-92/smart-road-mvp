export default function MetricCard({ label, value, hint, accent = "blue" }) {
  return (
    <article className={`metric-card metric-${accent}`}>
      <span className="mono-label">{label}</span>
      <strong>{value}</strong>
      <p>{hint}</p>
    </article>
  );
}
