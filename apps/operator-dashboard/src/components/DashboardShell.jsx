import { NavLink } from "react-router-dom";

const navigationItems = [
  { label: "Active Events", to: "/events/active" },
  { label: "Event History", to: "/events/history" },
  { label: "İstatistikler", to: "/statistics" },
  { label: "Device Status", to: "/devices" },
  { label: "Live Stream", to: "/live" },
];

export default function DashboardShell({ apiConfig, children }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="eyebrow">Operator Console</p>
          <h1>Road Sentinel</h1>
          <p className="muted-copy">
            Monitor active risk, field devices, and incoming streams from one
            calm surface.
          </p>
        </div>

        <nav className="nav-list" aria-label="Primary">
          {navigationItems.map((item) => (
            <NavLink
              key={item.to}
              className={({ isActive }) =>
                isActive ? "nav-item nav-item-active" : "nav-item"
              }
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footnote">
          <p className="mono-label">Gateway Feed</p>
          <strong>{apiConfig.useMockApi ? "Mock API" : "Live FastAPI"}</strong>
          <p className="muted-copy">{apiConfig.apiBaseUrl}</p>
        </div>
      </aside>

      <main className="content-area">
        <header className="top-bar">
          <div>
            <p className="eyebrow">Ops View</p>
            <h2>Traffic Supervision Dashboard</h2>
          </div>
          <div className="top-bar-status">
            <span className="status-dot" />
            <span>{apiConfig.useMockApi ? "Mock transport active" : "Polling gateway events"}</span>
          </div>
        </header>

        <section className="page-content">{children}</section>
      </main>
    </div>
  );
}
