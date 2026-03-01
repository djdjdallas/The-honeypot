"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import DashboardLayout from "../../../components/DashboardLayout";
import { supabase } from "../../../lib/supabase";

const TACTIC_KEYWORDS = [
  "trust building",
  "fake profit",
  "urgency",
  "guaranteed",
  "screenshot",
  "withdrawal fee",
  "tax fee",
  "gas fee",
  "minimum investment",
  "recovery",
  "romance",
  "giveaway",
  "airdrop",
  "connect wallet",
  "validate wallet",
  "sync wallet",
  "trading signal",
  "passive income",
  "daily returns",
  "risk free",
  "100% safe",
  "send me",
  "dm me",
  "whatsapp",
  "liquidity pool",
  "mining pool",
];

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

const OUTCOME_LABELS = {
  wallet_extracted: "Wallet Extracted",
  phishing_extracted: "Phishing Link Extracted",
  max_turns: "Max Turns Reached",
  abandoned: "Scammer Went Silent",
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

function highlightTactics(text) {
  if (!text) return text;
  let result = text;
  const highlights = [];

  for (const keyword of TACTIC_KEYWORDS) {
    const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
    let match;
    while ((match = regex.exec(text)) !== null) {
      highlights.push({ start: match.index, end: match.index + match[0].length, text: match[0] });
    }
  }

  if (highlights.length === 0) return null;
  return highlights;
}

function formatDuration(start, end) {
  if (!start || !end) return "—";
  const ms = new Date(end) - new Date(start);
  const mins = Math.floor(ms / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  if (mins > 60) {
    const hrs = Math.floor(mins / 60);
    return `${hrs}h ${mins % 60}m`;
  }
  return `${mins}m ${secs}s`;
}

export default function SessionDetailPage() {
  const params = useParams();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSession();
  }, [params.id]);

  async function fetchSession() {
    const { data, error } = await supabase
      .from("sessions")
      .select("*")
      .eq("id", params.id)
      .single();

    if (!error && data) {
      setSession(data);
    }
    setLoading(false);
  }

  function parseTranscript(transcript) {
    if (!transcript) return [];
    return transcript.split("\n").filter(Boolean).map((line, i) => {
      const colonIdx = line.indexOf(": ");
      if (colonIdx === -1) return { speaker: "Unknown", text: line, isAgent: false };
      const speaker = line.substring(0, colonIdx);
      const text = line.substring(colonIdx + 2);
      const isAgent = speaker !== "Scammer";
      return { speaker: isAgent ? speaker : "Scammer", text, isAgent };
    });
  }

  function renderMessageText(text) {
    const highlights = highlightTactics(text);
    if (!highlights || highlights.length === 0) {
      return <span>{text}</span>;
    }

    // Sort highlights by position
    highlights.sort((a, b) => a.start - b.start);

    const parts = [];
    let lastEnd = 0;
    for (const h of highlights) {
      if (h.start > lastEnd) {
        parts.push(<span key={`t-${lastEnd}`}>{text.substring(lastEnd, h.start)}</span>);
      }
      parts.push(
        <span
          key={`h-${h.start}`}
          style={{
            background: "rgba(255, 165, 2, 0.2)",
            color: "var(--warning)",
            padding: "0.1rem 0.3rem",
            borderRadius: "3px",
            fontWeight: "bold",
          }}
          title="Detected scam tactic"
        >
          {h.text}
        </span>
      );
      lastEnd = h.end;
    }
    if (lastEnd < text.length) {
      parts.push(<span key={`t-${lastEnd}`}>{text.substring(lastEnd)}</span>);
    }
    return <>{parts}</>;
  }

  if (loading) {
    return (
      <DashboardLayout title="Session Detail">
        <p style={{ color: "var(--text-secondary)" }}>Loading session...</p>
      </DashboardLayout>
    );
  }

  if (!session) {
    return (
      <DashboardLayout title="Session Detail">
        <p style={{ color: "var(--text-secondary)" }}>Session not found.</p>
        <Link href="/live-feed" style={{ color: "var(--accent)", marginTop: "1rem", display: "inline-block" }}>
          Back to Live Feed
        </Link>
      </DashboardLayout>
    );
  }

  const messages = parseTranscript(session.transcript);

  return (
    <DashboardLayout title="Conversation Replay">
      {/* Back link */}
      <Link
        href="/live-feed"
        style={{
          color: "var(--accent)",
          fontSize: "0.85rem",
          display: "inline-block",
          marginBottom: "1.5rem",
        }}
      >
        &larr; Back to Live Feed
      </Link>

      <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
        {/* Main transcript area */}
        <div style={{ flex: "1 1 600px", minWidth: 0 }}>
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              padding: "1.5rem",
            }}
          >
            <h3 style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "1rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Transcript ({messages.length} messages)
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {messages.map((msg, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: msg.isAgent ? "flex-end" : "flex-start",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.7rem",
                      color: msg.isAgent ? "var(--accent)" : "var(--danger)",
                      marginBottom: "0.2rem",
                      fontWeight: "bold",
                    }}
                  >
                    {msg.isAgent ? `${msg.speaker} (Agent)` : "Scammer"}
                  </span>
                  <div
                    style={{
                      background: msg.isAgent ? "rgba(0, 212, 170, 0.1)" : "rgba(255, 71, 87, 0.1)",
                      border: `1px solid ${msg.isAgent ? "rgba(0, 212, 170, 0.2)" : "rgba(255, 71, 87, 0.2)"}`,
                      borderRadius: msg.isAgent ? "10px 10px 2px 10px" : "10px 10px 10px 2px",
                      padding: "0.75rem 1rem",
                      maxWidth: "85%",
                      fontSize: "0.9rem",
                      lineHeight: "1.5",
                    }}
                  >
                    {msg.isAgent ? msg.text : renderMessageText(msg.text)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar with metadata */}
        <div style={{ flex: "0 0 300px" }}>
          {/* Session Info */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              padding: "1.25rem",
              marginBottom: "1rem",
            }}
          >
            <h3 style={{ color: "var(--text-secondary)", fontSize: "0.8rem", marginBottom: "1rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Session Info
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.85rem" }}>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Scam Type: </span>
                <span style={{ color: "var(--danger)", fontWeight: "bold" }}>
                  {SCAM_TYPE_LABELS[session.scam_type] || session.scam_type || "Unclassified"}
                </span>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Confidence: </span>
                <span>{Math.round((session.confidence || 0) * 100)}%</span>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Persona: </span>
                <span style={{ color: "var(--accent)" }}>{session.persona_used}</span>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Turns: </span>
                <span>{session.turn_count}</span>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Duration: </span>
                <span>{formatDuration(session.started_at, session.ended_at)}</span>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Outcome: </span>
                <span style={{ color: OUTCOME_COLORS[session.outcome] || "var(--text-primary)" }}>
                  {OUTCOME_LABELS[session.outcome] || session.outcome || "Unknown"}
                </span>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Source: </span>
                <span>{session.source_group || "Unknown"}</span>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Scammer ID: </span>
                <span style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>{session.scammer_id}</span>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Started: </span>
                <span>{session.started_at ? new Date(session.started_at).toLocaleString() : "—"}</span>
              </div>
            </div>
          </div>

          {/* Tactics */}
          {session.key_tactics && session.key_tactics.length > 0 && (
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "10px",
                padding: "1.25rem",
                marginBottom: "1rem",
              }}
            >
              <h3 style={{ color: "var(--text-secondary)", fontSize: "0.8rem", marginBottom: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Detected Tactics
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                {session.key_tactics.map((tactic, i) => (
                  <span
                    key={i}
                    style={{
                      background: "rgba(255, 165, 2, 0.15)",
                      color: "var(--warning)",
                      padding: "0.3rem 0.6rem",
                      borderRadius: "4px",
                      fontSize: "0.8rem",
                    }}
                  >
                    {tactic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Intel */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              padding: "1.25rem",
            }}
          >
            <h3 style={{ color: "var(--text-secondary)", fontSize: "0.8rem", marginBottom: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Extracted Intel
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.85rem" }}>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Wallets: </span>
                <span style={{ color: session.wallets_found > 0 ? "var(--accent)" : "var(--text-secondary)" }}>
                  {session.wallets_found || 0}
                </span>
              </div>
              {session.phishing_links && session.phishing_links.length > 0 && (
                <div>
                  <span style={{ color: "var(--text-secondary)" }}>Phishing Links:</span>
                  {session.phishing_links.map((link, i) => (
                    <div
                      key={i}
                      style={{
                        fontFamily: "monospace",
                        fontSize: "0.75rem",
                        color: "var(--danger)",
                        wordBreak: "break-all",
                        marginTop: "0.3rem",
                        background: "rgba(255, 71, 87, 0.1)",
                        padding: "0.3rem 0.5rem",
                        borderRadius: "4px",
                      }}
                    >
                      {link}
                    </div>
                  ))}
                </div>
              )}
              {session.phones_found && session.phones_found.length > 0 && (
                <div>
                  <span style={{ color: "var(--text-secondary)" }}>Phones: </span>
                  {session.phones_found.map((phone, i) => (
                    <span key={i} style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
                      {phone}{i < session.phones_found.length - 1 ? ", " : ""}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
