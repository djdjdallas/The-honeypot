export default function StatCard({ label, value, color }) {
  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "10px",
        padding: "1.25rem",
        minWidth: "160px",
      }}
    >
      <div style={{ color: "var(--text-secondary)", fontSize: "0.8rem", marginBottom: "0.4rem" }}>
        {label}
      </div>
      <div style={{ color: color || "var(--accent)", fontSize: "1.8rem", fontWeight: "bold" }}>
        {value}
      </div>
    </div>
  );
}
