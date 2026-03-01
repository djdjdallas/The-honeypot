import { supabase } from "../../../lib/supabase";

export async function GET() {
  const [sessionsRes, walletsRes, patternsRes] = await Promise.all([
    supabase.from("sessions").select("id, scam_type, status, wallets_found", { count: "exact" }),
    supabase.from("wallets").select("id, chain", { count: "exact" }),
    supabase.from("script_patterns").select("id", { count: "exact" }),
  ]);

  const sessions = sessionsRes.data || [];
  const wallets = walletsRes.data || [];

  const scamTypeCounts = {};
  for (const s of sessions) {
    if (s.scam_type) {
      scamTypeCounts[s.scam_type] = (scamTypeCounts[s.scam_type] || 0) + 1;
    }
  }

  const chainCounts = {};
  for (const w of wallets) {
    chainCounts[w.chain] = (chainCounts[w.chain] || 0) + 1;
  }

  return Response.json({
    totalSessions: sessionsRes.count || 0,
    activeSessions: sessions.filter((s) => s.status === "active").length,
    totalWallets: walletsRes.count || 0,
    totalPatterns: patternsRes.count || 0,
    scamTypes: scamTypeCounts,
    chains: chainCounts,
  });
}
