"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import { supabase } from "../../lib/supabase";

export default function ScriptPatternsPage() {
  const [patterns, setPatterns] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPatterns();
  }, []);

  async function fetchPatterns() {
    const { data, error } = await supabase
      .from("script_patterns")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(50);

    if (!error && data) {
      setPatterns(data);
    }
    setLoading(false);
  }

  return (
    <DashboardLayout title="Script Patterns">
      <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
        Common scam scripts and tactics extracted from engagement conversations.
      </p>

      {loading ? (
        <p style={{ color: "var(--text-secondary)" }}>Loading patterns...</p>
      ) : patterns.length === 0 ? (
        <p style={{ color: "var(--text-secondary)" }}>No script patterns extracted yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {patterns.map((pattern) => (
            <div
              key={pattern.id}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "10px",
                padding: "1.25rem",
                cursor: "pointer",
              }}
              onClick={() => setExpandedId(expandedId === pattern.id ? null : pattern.id)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span
                  style={{
                    color: "var(--danger)",
                    fontWeight: "bold",
                    textTransform: "uppercase",
                    fontSize: "0.85rem",
                  }}
                >
                  {pattern.scam_type?.replace(/_/g, " ")}
                </span>
                <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                  {pattern.created_at ? new Date(pattern.created_at).toLocaleDateString() : ""}
                </span>
              </div>

              {pattern.tactics && pattern.tactics.length > 0 && (
                <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
                  {pattern.tactics.map((tactic, i) => (
                    <span
                      key={i}
                      style={{
                        background: "var(--bg-secondary)",
                        color: "var(--warning)",
                        padding: "0.2rem 0.5rem",
                        borderRadius: "4px",
                        fontSize: "0.75rem",
                      }}
                    >
                      {tactic}
                    </span>
                  ))}
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
