"use client";

import { useEffect, useState, useMemo } from "react";
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

export default function ScriptPatternsPage() {
  const [patterns, setPatterns] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState("all");

  useEffect(() => {
    fetchPatterns();

    const channel = supabase
      .channel("patterns-changes")
      .on("postgres_changes", { event: "*", schema: "public", table: "script_patterns" }, () => {
        fetchPatterns();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  async function fetchPatterns() {
    const { data, error } = await supabase
      .from("script_patterns")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(200);

    if (!error && data) {
      setPatterns(data);
    }
    setLoading(false);
  }

  // Group patterns by scam type and compute tactic frequencies
  const { groupedByType, tacticFrequencies, scamTypeCounts } = useMemo(() => {
    const grouped = {};
    const tacticFreqs = {};
    const typeCounts = {};

    for (const pattern of patterns) {
      const type = pattern.scam_type || "other";
      if (!grouped[type]) grouped[type] = [];
      grouped[type].push(pattern);
      typeCounts[type] = (typeCounts[type] || 0) + 1;

      if (pattern.tactics) {
        for (const tactic of pattern.tactics) {
          const key = `${type}::${tactic}`;
          tacticFreqs[key] = (tacticFreqs[key] || 0) + 1;
          // Global count too
          tacticFreqs[`__global__::${tactic}`] = (tacticFreqs[`__global__::${tactic}`] || 0) + 1;
        }
      }
    }

    return { groupedByType: grouped, tacticFrequencies: tacticFreqs, scamTypeCounts: typeCounts };
  }, [patterns]);

  // Get unique scam types for filter
  const scamTypes = Object.keys(scamTypeCounts).sort(
    (a, b) => (scamTypeCounts[b] || 0) - (scamTypeCounts[a] || 0)
  );

  // Filtered patterns
  const filteredPatterns = filterType === "all"
    ? patterns
    : patterns.filter((p) => p.scam_type === filterType);

  // Top tactics across all patterns
  const topTactics = useMemo(() => {
    const globalTactics = {};
    for (const [key, count] of Object.entries(tacticFrequencies)) {
      if (key.startsWith("__global__::")) {
        const tactic = key.replace("__global__::", "");
        globalTactics[tactic] = count;
      }
    }
    return Object.entries(globalTactics)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);
  }, [tacticFrequencies]);

  return (
    <DashboardLayout title="Script Patterns">
      {/* Stats row */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem", flexWrap: "wrap" }}>
        <StatCard label="Total Patterns" value={patterns.length} />
        <StatCard label="Scam Types" value={scamTypes.length} color="var(--warning)" />
        <StatCard
          label="Top Type"
          value={scamTypes.length > 0 ? (SCAM_TYPE_LABELS[scamTypes[0]] || scamTypes[0]) : "\u2014"}
          color="var(--danger)"
        />
      </div>

      {/* Top Tactics frequency */}
      {topTactics.length > 0 && (
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "10px",
            padding: "1.25rem",
            marginBottom: "1.5rem",
          }}
        >
          <h3 style={{ color: "var(--text-secondary)", fontSize: "0.8rem", marginBottom: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Most Common Tactics (across all sessions)
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {topTactics.map(([tactic, count]) => (
              <div key={tactic} style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.2rem" }}>
                    <span style={{ fontSize: "0.85rem" }}>{tactic}</span>
                    <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                      {count} session{count !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <div style={{ background: "var(--bg-secondary)", borderRadius: "4px", height: "6px", overflow: "hidden" }}>
                    <div
                      style={{
                        background: "var(--warning)",
                        height: "100%",
                        width: `${patterns.length > 0 ? (count / patterns.length) * 100 : 0}%`,
                        borderRadius: "4px",
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter by scam type */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <button
          onClick={() => setFilterType("all")}
          style={{
            background: filterType === "all" ? "var(--accent)" : "var(--bg-card)",
            color: filterType === "all" ? "var(--bg-primary)" : "var(--text-secondary)",
            border: "1px solid var(--border)",
            borderRadius: "6px",
            padding: "0.35rem 0.8rem",
            cursor: "pointer",
            fontSize: "0.8rem",
          }}
        >
          All ({patterns.length})
        </button>
        {scamTypes.map((type) => (
          <button
            key={type}
            onClick={() => setFilterType(type)}
            style={{
              background: filterType === type ? (SCAM_TYPE_COLORS[type] || "var(--accent)") : "var(--bg-card)",
              color: filterType === type ? "var(--bg-primary)" : (SCAM_TYPE_COLORS[type] || "var(--text-secondary)"),
              border: "1px solid var(--border)",
              borderRadius: "6px",
              padding: "0.35rem 0.8rem",
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            {SCAM_TYPE_LABELS[type] || type} ({scamTypeCounts[type]})
          </button>
        ))}
      </div>

      {loading ? (
        <p style={{ color: "var(--text-secondary)" }}>Loading patterns...</p>
      ) : filteredPatterns.length === 0 ? (
        <p style={{ color: "var(--text-secondary)" }}>No script patterns extracted yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {filteredPatterns.map((pattern) => (
            <div
              key={pattern.id}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderLeft: `3px solid ${SCAM_TYPE_COLORS[pattern.scam_type] || "var(--border)"}`,
                borderRadius: "10px",
                padding: "1.25rem",
                cursor: "pointer",
              }}
              onClick={() => setExpandedId(expandedId === pattern.id ? null : pattern.id)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span
                  style={{
                    color: SCAM_TYPE_COLORS[pattern.scam_type] || "var(--danger)",
                    fontWeight: "bold",
                    fontSize: "0.85rem",
                  }}
                >
                  {SCAM_TYPE_LABELS[pattern.scam_type] || pattern.scam_type?.replace(/_/g, " ")}
                </span>
                <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                  {pattern.created_at ? new Date(pattern.created_at).toLocaleDateString() : ""}
                </span>
              </div>

              {pattern.tactics && pattern.tactics.length > 0 && (
                <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
                  {pattern.tactics.map((tactic, i) => {
                    const freqKey = `__global__::${tactic}`;
                    const freq = tacticFrequencies[freqKey] || 0;
                    return (
                      <span
                        key={i}
                        style={{
                          background: "rgba(255, 165, 2, 0.15)",
                          color: "var(--warning)",
                          padding: "0.2rem 0.5rem",
                          borderRadius: "4px",
                          fontSize: "0.75rem",
                        }}
                        title={`Seen in ${freq} session(s)`}
                      >
                        {tactic} ({freq})
                      </span>
                    );
                  })}
                </div>
              )}

              <div
                style={{
                  color: "var(--text-secondary)",
                  fontSize: "0.85rem",
                  marginTop: "0.75rem",
                }}
              >
                {pattern.trigger_message?.substring(0, 150)}
                {pattern.trigger_message?.length > 150 ? "..." : ""}
              </div>

              {expandedId === pattern.id && pattern.transcript_excerpt && (
                <pre
                  style={{
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border)",
                    borderRadius: "6px",
                    padding: "1rem",
                    marginTop: "1rem",
                    fontSize: "0.8rem",
                    color: "var(--text-secondary)",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    maxHeight: "400px",
                    overflowY: "auto",
                  }}
                >
                  {pattern.transcript_excerpt}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
