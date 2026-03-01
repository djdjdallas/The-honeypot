import "./globals.css";

export const metadata = {
  title: "HoneyTrap Dashboard",
  description: "Crypto scam intelligence honeypot dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
