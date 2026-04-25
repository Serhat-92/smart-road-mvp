import { getEventStats } from "../api/operatorApi";
import MetricCard from "../components/MetricCard";
import { ErrorState, LoadingState } from "../components/ResourceState";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { formatTimestamp } from "../lib/formatters";

export default function StatisticsPage() {
  const { data: stats, error, isLoading, lastUpdatedAt, isRefreshing } = useAsyncResource(
    () => getEventStats(),
    [],
    { refreshIntervalMs: 30000 },
  );

  if (isLoading && !stats) {
    return <LoadingState label="İstatistikler yükleniyor..." />;
  }

  if (error && !stats) {
    return <ErrorState error={error} />;
  }

  if (!stats) return null;

  return (
    <div className="page-stack">
      <section className="section-heading">
        <div>
          <p className="eyebrow">Overview</p>
          <h3>Sistem İstatistikleri</h3>
          <p className="muted-copy">
            Genel durum ve cihaz performans istatistikleri.
            {lastUpdatedAt && ` · Son güncelleme: ${formatTimestamp(lastUpdatedAt)}`}
            {isRefreshing && " · yenileniyor..."}
          </p>
        </div>
      </section>

      <h4 style={{ margin: "1rem 0 0.5rem", fontSize: "1.1rem", fontWeight: "600", color: "var(--color-ink)" }}>Durum Özeti</h4>
      <section className="hero-grid">
        <MetricCard
          label="Toplam İhlal"
          value={stats.total_events}
          hint="Tüm zamanların kayıtlı ihlal sayısı."
          accent="neutral"
        />
        <MetricCard
          label="Bekleyen İnceleme"
          value={stats.pending_count}
          hint="İncelenmeyi bekleyen olaylar."
          accent="amber"
        />
        <MetricCard
          label="İncelenen"
          value={stats.reviewed_count}
          hint="Onaylanan ihlaller."
          accent="green"
        />
        <MetricCard
          label="Geçersiz"
          value={stats.dismissed_count}
          hint="Reddedilen ihlaller."
          accent="red"
        />
      </section>

      <h4 style={{ margin: "1rem 0 0.5rem", fontSize: "1.1rem", fontWeight: "600", color: "var(--color-ink)" }}>Hız Metrikleri</h4>
      <section className="hero-grid">
        <MetricCard
          label="Ort. Radar Hızı"
          value={stats.avg_radar_speed != null ? `${Math.round(stats.avg_radar_speed)} km/h` : "N/A"}
          hint="Radar donanımından ölçülen ortalama hız."
          accent="blue"
        />
        <MetricCard
          label="Ort. Tahmin Hızı"
          value={stats.avg_estimated_speed != null ? `${Math.round(stats.avg_estimated_speed)} km/h` : "N/A"}
          hint="Kamera perspektifinden tahmin edilen hız."
          accent="indigo"
        />
        <MetricCard
          label="Son 1 Saatte İhlal"
          value={stats.events_last_hour}
          hint="Son 60 dakika içerisindeki tespitler."
          accent="purple"
        />
      </section>

      <h4 style={{ margin: "1rem 0 0.5rem", fontSize: "1.1rem", fontWeight: "600", color: "var(--color-ink)" }}>En Aktif 3 Kamera</h4>
      <section style={{ background: "white", padding: "1.5rem", borderRadius: "12px", border: "1px solid var(--color-surface-border)" }}>
        {stats.top_cameras && stats.top_cameras.length > 0 ? (
          <table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid var(--color-surface-border)" }}>
                <th style={{ padding: "0.5rem", fontWeight: 600 }}>Kamera ID</th>
                <th style={{ padding: "0.5rem", fontWeight: 600 }}>İhlal Sayısı</th>
              </tr>
            </thead>
            <tbody>
              {stats.top_cameras.map((cam, idx) => (
                <tr key={cam.camera_id} style={{ borderBottom: "1px solid var(--color-surface-border)" }}>
                  <td style={{ padding: "0.75rem 0.5rem", fontFamily: "var(--font-mono)", fontSize: "0.9rem" }}>
                    {idx === 0 ? "🥇 " : idx === 1 ? "🥈 " : "🥉 "}{cam.camera_id}
                  </td>
                  <td style={{ padding: "0.75rem 0.5rem" }}>
                    <span style={{ background: "var(--color-primary-soft)", color: "var(--color-primary)", padding: "0.15rem 0.5rem", borderRadius: "999px", fontWeight: "500", fontSize: "0.85rem" }}>
                      {cam.count} olay
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted-copy">Henüz yeterli veri yok.</p>
        )}
      </section>
    </div>
  );
}
