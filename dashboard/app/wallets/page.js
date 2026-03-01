"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import StatCard from "../../components/StatCard";
import { supabase } from "../../lib/supabase";

const CHAIN_COLORS = {
  ETH: "#627eea",
  BTC: "#f7931a",
  SOL: "#9945ff",
  TRX: "#eb0029",
};

export default function WalletsPage() {
  const [wallets, setWallets] = useState([]);
  const [chainFilter, setChainFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWallets();
  }, [chainFilter]);

  async function fetchWallets() {
    let query = supabase.from("wallets").select("*").order("created_at", { ascending: false });

    if (chainFilter !== "all") {
      query = query.eq("chain", chainFilter);
    }

    const { data, error } = await query.limit(100);
    if (!error && data) {
      setWallets(data);
    }
    setLoading(false);
  }

  const chains = ["all", "ETH", "BTC", "SOL", "TRX"];

  return (
    <DashboardLayout title="Extracted Wallets">
      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem", flexWrap: "wrap" }}>
        <StatCard label="Total Wallets" value={wallets.length} />
        <StatCard
          label="ETH"
          value={wallets.filter((w) => w.chain === "ETH").length}
          color={CHAIN_COLORS.ETH}
        />
        <StatCard
          label="BTC"
          value={wallets.filter((w) => w.chain === "BTC").length}
          color={CHAIN_COLORS.BTC}
        />
        <StatCard
          label="SOL"
          value={wallets.filter((w) => w.chain === "SOL").length}
          color={CHAIN_COLORS.SOL}
        />
        <StatCard
          label="TRX"
          value={wallets.filter((w) => w.chain === "TRX").length}
          color={CHAIN_COLORS.TRX}
        />
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
        {chains.map((chain) => (
          <button
            key={chain}
            onClick={() => setChainFilter(chain)}
            style={{
              background: chainFilter === chain ? "var(--accent)" : "var(--bg-card)",
              color: chainFilter === chain ? "var(--bg-primary)" : "var(--text-secondary)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              padding: "0.4rem 1rem",
              cursor: "pointer",
              fontSize: "0.85rem",
            }}
          >
            {chain.toUpperCase()}
          </button>
        ))}
      </div>

      {loading ? (
        <p style={{ color: "var(--text-secondary)" }}>Loading wallets...</p>
      ) : wallets.length === 0 ? (
        <p style={{ color: "var(--text-secondary)" }}>No wallets extracted yet.</p>
      ) : (
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            background: "var(--bg-card)",
            borderRadius: "10px",
            overflow: "hidden",
          }}
        >
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              <th style={thStyle}>Address</th>
              <th style={thStyle}>Chain</th>
              <th style={thStyle}>Scammer</th>
              <th style={thStyle}>First Seen</th>
              <th style={thStyle}>Sessions</th>
            </tr>
          </thead>
          <tbody>
            {wallets.map((wallet) => (
              <tr key={wallet.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={tdStyle}>
                  <code style={{ color: CHAIN_COLORS[wallet.chain] || "var(--accent)" }}>
                    {wallet.address.substring(0, 8)}...{wallet.address.slice(-6)}
                  </code>
                </td>
                <td style={tdStyle}>
                  <span
                    style={{
                      color: CHAIN_COLORS[wallet.chain] || "var(--text-primary)",
                      fontWeight: "bold",
                    }}
                  >
                    {wallet.chain}
                  </span>
                </td>
                <td style={tdStyle}>{wallet.scammer_id || "—"}</td>
                <td style={tdStyle}>
                  {wallet.first_seen ? new Date(wallet.first_seen).toLocaleDateString() : "—"}
                </td>
                <td style={tdStyle}>{wallet.total_sessions || 1}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </DashboardLayout>
  );
}

const thStyle = {
  textAlign: "left",
  padding: "0.75rem 1rem",
  color: "var(--text-secondary)",
  fontSize: "0.8rem",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const tdStyle = {
  padding: "0.75rem 1rem",
  fontSize: "0.9rem",
};
