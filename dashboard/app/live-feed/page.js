"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import StatCard from "../../components/StatCard";
import { supabase } from "../../lib/supabase";

export default function LiveFeedPage() {
  const [sessions, setSessions] = useState([]);
  const [stats, setStats] = useState({ total: 0, active: 0, walletsFound: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSessions();

    // Subscribe to real-time updates
    const channel = supabase
      .channel("sessions-changes")
      .on("postgres_changes", { event: "*", schema: "public", table: "sessions" }, () => {
        fetchSessions();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  async function fetchSessions() {
    const { data, error } = await supabase
      .from("sessions")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(50);

    if (!error && data) {
      setSessions(data);
      setStats({
        total: data.length,
        active: data.filter((s) => s.status === "active").length,
        walletsFound: data.reduce((sum, s) => sum + (s.wallets_found || 0), 0),
      });
    }
    setLoading(false);
  }

  return (
    <DashboardLayout title="Live Feed">
      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem", flexWrap: "wrap" }}>
        <StatCard label="Total Sessions" value={stats.total} />
        <StatCard label="Active" value={stats.active} color="var(--warning)" />
        <StatCard label="Wallets Found" value={stats.walletsFound} color="var(--danger)" />
      </div>

      {loading ? (
        <p style={{ color: "var(--text-secondary)" }}>Loading sessions...</p>
      ) : sessions.length === 0 ? (
        <p style={{ color: "var(--text-secondary)" }}>
          No sessions yet. Start the monitor to begin collecting intelligence.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {sessions.map((session) => (
            <div
              key={session.id}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "10px",
                padding: "1.25rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <span style={{ color: "var(--accent)", fontWeight: "bold" }}>
                  {session.persona_used}
                </span>
                <span
                  style={{
                    color: session.status === "active" ? "var(--warning)" : "var(--text-secondary)",
                    fontSize: "0.85rem",
                  }}
                >
                  {session.status} | {session.turn_count} turns
                </span>
              </div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>
                Scammer ID: {session.scammer_id}
              </div>
              {session.scam_type && (
                <span
                  style={{
                    background: "var(--bg-secondary)",
                    color: "var(--danger)",
                    padding: "0.2rem 0.6rem",
                    borderRadius: "4px",
                    fontSize: "0.8rem",
                    marginRight: "0.5rem",
                  }}
                >
                  {session.scam_type}
                </span>
              )}
              {session.wallets_found > 0 && (
                <span
                  style={{
                    background: "var(--bg-secondary)",
                    color: "var(--warning)",
                    padding: "0.2rem 0.6rem",
                    borderRadius: "4px",
                    fontSize: "0.8rem",
                  }}
                >
                  {session.wallets_found} wallet(s)
                </span>
              )}
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.5rem" }}>
                {session.trigger_message?.substring(0, 120)}
                {session.trigger_message?.length > 120 ? "..." : ""}
              </div>
            </div>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
