"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import DashboardLayout from "../../components/DashboardLayout";
import StatCard from "../../components/StatCard";
import { supabase } from "../../lib/supabase";

const OUTCOME_LABELS = {
  wallet_extracted: "Wallet Extracted",
  phishing_extracted: "Link Extracted",
  max_turns: "Max Turns",
  abandoned: "Abandoned",
  error: "Error",
  intel_sufficient: "Intel Sufficient",
  unknown: "Unknown",
};

const OUTCOME_COLORS = {
  wallet_extracted: "#00d4aa",
  phishing_extracted: "#ffa502",
  max_turns: "#8888aa",
  abandoned: "#747d8c",
  error: "#ff4757",
  intel_sufficient: "#00d4aa",
  unknown: "#8888aa",
};

function formatDuration(start, end) {
  if (!start || !end) return "—";
  const ms = new Date(end) - new Date(start);
  const mins = Math.floor(ms / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  if (mins > 60) {
    const hrs = Math.floor(mins / 60);
    return `${hrs}h ${mins % 60}m`;
  }
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

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
            <Link
              key={session.id}
              href={`/session/${session.id}`}
              style={{ textDecoration: "none", color: "inherit" }}
            >
              <div
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: "10px",
                  padding: "1.25rem",
                  cursor: "pointer",
                  transition: "border-color 0.2s",
                }}
                onMouseOver={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
                onMouseOut={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
              >
                {/* Row 1: Persona, status, turn count, duration */}
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem", alignItems: "center" }}>
                  <span style={{ color: "var(--accent)", fontWeight: "bold" }}>
                    {session.persona_used}
                  </span>
                  <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
                    <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                      {session.turn_count} turns
                    </span>
                    <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                      {formatDuration(session.started_at, session.ended_at)}
                    </span>
                    <span
                      style={{
                        color: session.status === "active" ? "var(--warning)" : "var(--text-secondary)",
                        fontSize: "0.8rem",
                      }}
                    >
                      {session.status}
                    </span>
                  </div>
                </div>

                {/* Row 2: Scammer ID + Source Group */}
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "0.5rem", display: "flex", gap: "1rem" }}>
                  <span>Scammer: {session.scammer_id}</span>
                  {session.source_group && session.source_group !== "Unknown" && (
                    <span>
                      Source: <span style={{ color: "var(--accent)" }}>{session.source_group}</span>
                    </span>
                  )}
                </div>

                {/* Row 3: Badges — scam type, outcome, wallets */}
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                  {session.scam_type && (
                    <span
                      style={{
                        background: "rgba(255, 71, 87, 0.15)",
                        color: "var(--danger)",
                        padding: "0.2rem 0.6rem",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                      }}
                    >
                      {session.scam_type.replace(/_/g, " ")}
                    </span>
                  )}
                  {session.outcome && session.outcome !== "unknown" && (
                    <span
                      style={{
                        background: `${OUTCOME_COLORS[session.outcome] || "#8888aa"}22`,
                        color: OUTCOME_COLORS[session.outcome] || "var(--text-secondary)",
                        padding: "0.2rem 0.6rem",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                      }}
                    >
                      {OUTCOME_LABELS[session.outcome] || session.outcome}
                    </span>
                  )}
                  {session.wallets_found > 0 && (
                    <span
                      style={{
                        background: "rgba(255, 165, 2, 0.15)",
                        color: "var(--warning)",
                        padding: "0.2rem 0.6rem",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                      }}
                    >
                      {session.wallets_found} wallet(s)
                    </span>
                  )}
                  {session.phishing_links && session.phishing_links.length > 0 && (
                    <span
                      style={{
                        background: "rgba(255, 71, 87, 0.15)",
                        color: "var(--danger)",
                        padding: "0.2rem 0.6rem",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                      }}
                    >
                      {session.phishing_links.length} link(s)
                    </span>
                  )}
                </div>

                {/* Row 4: Trigger message preview */}
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "0.5rem" }}>
                  {session.trigger_message?.substring(0, 120)}
                  {session.trigger_message?.length > 120 ? "..." : ""}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
