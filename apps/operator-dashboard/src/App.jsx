import { Navigate, Route, Routes } from "react-router-dom";

import { apiConfig } from "./api/operatorApi";
import DashboardShell from "./components/DashboardShell";
import ActiveEventsPage from "./pages/ActiveEventsPage";
import DeviceStatusPage from "./pages/DeviceStatusPage";
import EventHistoryPage from "./pages/EventHistoryPage";
import LiveStreamPage from "./pages/LiveStreamPage";

export default function App() {
  return (
    <DashboardShell apiConfig={apiConfig}>
      <Routes>
        <Route path="/" element={<Navigate to="/events/active" replace />} />
        <Route path="/events/active" element={<ActiveEventsPage />} />
        <Route path="/events/history" element={<EventHistoryPage />} />
        <Route path="/devices" element={<DeviceStatusPage />} />
        <Route path="/live" element={<LiveStreamPage />} />
        <Route path="*" element={<Navigate to="/events/active" replace />} />
      </Routes>
    </DashboardShell>
  );
}
