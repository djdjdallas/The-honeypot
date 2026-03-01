-- HoneyTrap Intelligence Database Schema

-- Groups being monitored
CREATE TABLE IF NOT EXISTS monitored_groups (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    group_identifier TEXT NOT NULL UNIQUE,
    group_name TEXT,
    platform TEXT NOT NULL DEFAULT 'telegram',
    added_at TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT TRUE,
    total_scams_detected INTEGER DEFAULT 0,
    notes TEXT
);

-- Engagement sessions with scammers
CREATE TABLE IF NOT EXISTS sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    scammer_id TEXT NOT NULL,
    persona_used TEXT NOT NULL,
    transcript TEXT,
    trigger_message TEXT,
    scam_type TEXT,
    confidence REAL,
    key_tactics TEXT[],
    turn_count INTEGER DEFAULT 0,
    wallets_found INTEGER DEFAULT 0,
    phishing_links TEXT[],
    phones_found TEXT[],
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_sessions_scam_type ON sessions(scam_type);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created ON sessions(created_at DESC);

-- Extracted wallet addresses
CREATE TABLE IF NOT EXISTS wallets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    address TEXT NOT NULL UNIQUE,
    chain TEXT NOT NULL,
    session_id UUID REFERENCES sessions(id),
    scammer_id TEXT,
    first_seen TIMESTAMPTZ DEFAULT now(),
    times_seen INTEGER DEFAULT 1,
    total_sessions INTEGER DEFAULT 1,
    flagged BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_wallets_chain ON wallets(chain);
CREATE INDEX idx_wallets_address ON wallets(address);
CREATE INDEX idx_wallets_scammer ON wallets(scammer_id);

-- Scam script patterns extracted from conversations
CREATE TABLE IF NOT EXISTS script_patterns (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    scam_type TEXT NOT NULL,
    tactics TEXT[],
    trigger_message TEXT,
    transcript_excerpt TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_patterns_scam_type ON script_patterns(scam_type);

-- Enable Row Level Security
ALTER TABLE monitored_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE script_patterns ENABLE ROW LEVEL SECURITY;

-- Allow read access for authenticated users (dashboard)
CREATE POLICY "Allow read access" ON monitored_groups FOR SELECT USING (true);
CREATE POLICY "Allow read access" ON sessions FOR SELECT USING (true);
CREATE POLICY "Allow read access" ON wallets FOR SELECT USING (true);
CREATE POLICY "Allow read access" ON script_patterns FOR SELECT USING (true);

-- Allow insert/update for service role (agent backend)
CREATE POLICY "Allow service insert" ON sessions FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow service insert" ON wallets FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow service upsert" ON wallets FOR UPDATE USING (true);
CREATE POLICY "Allow service insert" ON script_patterns FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow service insert" ON monitored_groups FOR INSERT WITH CHECK (true);
