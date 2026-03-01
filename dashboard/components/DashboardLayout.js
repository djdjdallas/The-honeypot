"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/live-feed", label: "Live Feed" },
  { href: "/wallets", label: "Wallets" },
  { href: "/script-patterns", label: "Script Patterns" },
  { href: "/scam-types", label: "Scam Types" },
];

export default function DashboardLayout({ children, title }) {
  const pathname = usePathname();

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside
        style={{
          width: "220px",
          background: "var(--bg-secondary)",
          borderRight: "1px solid var(--border)",
          padding: "1.5rem 0",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            padding: "0 1.25rem 1.5rem",
            borderBottom: "1px solid var(--border)",
            marginBottom: "1rem",
          }}
        >
          <Link href="/" style={{ color: "var(--accent)", fontSize: "1.2rem", fontWeight: "bold" }}>
            HoneyTrap
          </Link>
        </div>
        <nav>
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "block",
                padding: "0.6rem 1.25rem",
                color: pathname === item.href ? "var(--accent)" : "var(--text-secondary)",
                borderLeft: pathname === item.href ? "3px solid var(--accent)" : "3px solid transparent",
                fontSize: "0.9rem",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main style={{ flex: 1, padding: "2rem" }}>
        {title && (
          <h1 style={{ color: "var(--accent)", marginBottom: "1.5rem", fontSize: "1.6rem" }}>
            {title}
          </h1>
        )}
        {children}
      </main>
    </div>
  );
}
