import Link from "next/link";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>HoneyTrap</h1>
        <p className={styles.subtitle}>
          Autonomous Crypto Scam Intelligence Honeypot
        </p>
      </header>

      <nav className={styles.grid}>
        <Link href="/live-feed" className={styles.card}>
          <h2>Live Feed</h2>
          <p>Real-time scam engagement sessions and detected activity.</p>
        </Link>

        <Link href="/wallets" className={styles.card}>
          <h2>Wallets</h2>
          <p>Extracted cryptocurrency wallet addresses linked to scammers.</p>
        </Link>

        <Link href="/script-patterns" className={styles.card}>
          <h2>Script Patterns</h2>
          <p>Common scam scripts and tactics extracted from conversations.</p>
        </Link>

        <Link href="/scam-types" className={styles.card}>
          <h2>Scam Types</h2>
          <p>Classification breakdown and trend analysis of scam categories.</p>
        </Link>
      </nav>

      <footer className={styles.footer}>
        <p>Built for the Amazon Nova AI Hackathon</p>
      </footer>
    </div>
  );
}
