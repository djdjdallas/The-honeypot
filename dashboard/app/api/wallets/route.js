import { supabase } from "../../../lib/supabase";

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const chain = searchParams.get("chain");
  const limit = parseInt(searchParams.get("limit") || "100", 10);

  let query = supabase
    .from("wallets")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(limit);

  if (chain) {
    query = query.eq("chain", chain);
  }

  const { data, error } = await query;

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json(data);
}
