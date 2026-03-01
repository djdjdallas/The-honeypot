"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import StatCard from "../../components/StatCard";
import { supabase } from "../../lib/supabase";

const SCAM_TYPE_LABELS = {
  pig_butchering: "Pig Butchering",
  fake_exchange: "Fake Exchange",
  pump_dump: "Pump & Dump",
  rug_pull: "Rug Pull",
  giveaway_scam: "Giveaway Scam",
  recovery_scam: "Recovery Scam",
  romance_crypto: "Romance Crypto",
  other: "Other",
};

const SCAM_TYPE_COLORS = {
  pig_butchering: "#ff6b6b",
  fake_exchange: "#ffa502",
  pump_dump: "#7bed9f",
  rug_pull: "#ff4757",
  giveaway_scam: "#1e90ff",
  recovery_scam: "#a55eea",
  romance_crypto: "#ff6348",
  other: "#747d8c",
};

export default function ScamTypesPage() {
  const [sessions, setSessions] = useState([]);
  const [typeCounts, setTypeCounts] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    const { data, error } = await supabase
      .from("sessions")
      .select("scam_type, confidence, key_tactics, turn_count, created_at")
      .not("scam_type", "is", null)
      .order("created_at", { ascending: false });

    if (!error && data) {
      setSessions(data);

      const counts = {};
      for (const s of data) {
        counts[s.scam_type] = (counts[s.scam_type] || 0) + 1;
      }
      setTypeCounts(counts);
    }
    setLoading(false);
  }

  const sortedTypes = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]);
  const totalSessions = sessions.length;

  return (
    <DashboardLayout title="Scam Type Analysis">
      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem", flexWrap: "wrap" }}>
        <StatCard label="Classified Sessions" value={totalSessions} />
        <StatCard label="Scam Types Seen" value={sortedTypes.length} color="var(--warning)" />
        <StatCard
          label="Top Type"
          value={
            sortedTypes.length > 0
              ? SCAM_TYPE_LABELS[sortedTypes[0][0]] || sortedTypes[0][0]
              : "—"
          }
          color="var(--danger)"
        />
      </div>

      {loading ? (
        <p style={{ color: "var(--text-secondary)" }}>Loading data...</p>
      ) : sortedTypes.length === 0 ? (
        <p style={{ color: "var(--text-secondary)" }}>No classified sessions yet.</p>
      ) : (
        <>
          {/* Bar chart */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              padding: "1.5rem",
              marginBottom: "2rem",
            }}
          >
            <h3 style={{ color: "var(--text-secondary)", marginBottom: "1rem", fontSize: "0.9rem" }}>
              Distribution
            </h3>
            {sortedTypes.map(([type, count]) => (
              <div key={type} style={{ marginBottom: "0.75rem" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "0.3rem",
                  }}
                >
                  <span style={{ fontSize: "0.85rem" }}>
                    {SCAM_TYPE_LABELS[type] || type}
                  </span>
                  <span style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                    {count} ({totalSessions > 0 ? Math.round((count / totalSessions) * 100) : 0}%)
                  </span>
                </div>
                <div
                  style={{
                    background: "var(--bg-secondary)",
                    borderRadius: "4px",
                    height: "8px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      background: SCAM_TYPE_COLORS[type] || "var(--accent)",
                      height: "100%",
                      width: `${totalSessions > 0 ? (count / totalSessions) * 100 : 0}%`,
                      borderRadius: "4px",
                      transition: "width 0.5s ease",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Recent classified sessions */}
          <h3 style={{ color: "var(--text-secondary)", marginBottom: "1rem", fontSize: "0.9rem" }}>
            Recent Classifications
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {sessions.slice(0, 20).map((s, i) => (
              <div
                key={i}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "0.75rem 1rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                }}
              >
                <span
                  style={{
                    color: SCAM_TYPE_COLORS[s.scam_type] || "var(--text-primary)",
                    fontWeight: "bold",
                    fontSize: "0.85rem",
                    minWidth: "140px",
                  }}
                >
                  {SCAM_TYPE_LABELS[s.scam_type] || s.scam_type}
                </span>
                <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                  {Math.round((s.confidence || 0) * 100)}% confidence
                </span>
                <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                  {s.turn_count} turns
                </span>
                {s.key_tactics?.slice(0, 2).map((t, j) => (
                  <span
                    key={j}
                    style={{
                      background: "var(--bg-secondary)",
                      color: "var(--text-secondary)",
                      padding: "0.15rem 0.4rem",
                      borderRadius: "3px",
                      fontSize: "0.7rem",
                    }}
                  >
                    {t}
                  </span>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </DashboardLayout>
  );
}
