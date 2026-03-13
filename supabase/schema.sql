-- ════════════════════════════════════════════════════════════════════════════
-- AVR v2.2 Database Schema - Research Formation System
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql
-- ════════════════════════════════════════════════════════════════════════════

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ════════════════════════════════════════════════════════════════════════════
-- 1. User Profiles (extends Supabase Auth)
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,

    -- Subscription/Tier management
    tier VARCHAR(10) DEFAULT 'free' CHECK (tier IN ('free', 'paid')),
    runs_today INT DEFAULT 0,
    paid_until TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-create profile when user signs up
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- Reset runs_today daily (call via cron job or edge function)
CREATE OR REPLACE FUNCTION reset_daily_runs()
RETURNS void AS $$
BEGIN
    UPDATE profiles SET runs_today = 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ════════════════════════════════════════════════════════════════════════════
-- 2. Research Sessions (main research workflow container)
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Phase tracking
    phase VARCHAR(10) NOT NULL CHECK (phase IN ('phase1', 'phase2', 'phase3')),
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'abstract_ready', 'gate_run', 'outline_ready', 'abandoned')),

    -- Conversation state machine
    conversation_state VARCHAR(20) DEFAULT 'INITIAL'
        CHECK (conversation_state IN ('INITIAL', 'CLARIFYING', 'BLOCKED', 'COMPLETE')),
    clarifying_turns_count INT DEFAULT 0,
    extracted_attributes JSONB DEFAULT '{}',

    -- Phase 1 outputs: Conversational Engine
    blueprint JSONB,
    estimated_abstract TEXT,
    journal_suggestions JSONB DEFAULT '[]',

    -- Phase 2 outputs: Submission Gate
    submitted_abstract TEXT,
    violations JSONB DEFAULT '[]',
    integrity_score FLOAT,
    gate_result VARCHAR(20)
        CHECK (gate_result IS NULL OR gate_result IN ('PASS', 'REVISE', 'REJECT')),
    reviewer_simulation TEXT,

    -- Phase 3 outputs: Manuscript Outline
    target_journal_id VARCHAR(100),
    manuscript_outline TEXT,

    -- Tracking for multiple gate runs
    gate_run_count INT DEFAULT 0,
    score_history JSONB DEFAULT '[]',
    abstract_versions JSONB DEFAULT '[]',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_sessions_user_id
    ON research_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_research_sessions_user_updated
    ON research_sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_sessions_status
    ON research_sessions(status);
CREATE INDEX IF NOT EXISTS idx_research_sessions_phase
    ON research_sessions(phase);


-- ════════════════════════════════════════════════════════════════════════════
-- 3. Conversation Turns (chat history within a session)
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS conversation_turns (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,

    -- Message identity
    role VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,

    -- Extracted attributes from this turn (for user messages)
    extracted_attributes JSONB DEFAULT '{}',

    -- Metadata
    turn_number INT NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_id
    ON conversation_turns(session_id, id);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_turn
    ON conversation_turns(session_id, turn_number);


-- ════════════════════════════════════════════════════════════════════════════
-- 4. Violations (audit log for gate violations)
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,

    -- Violation details
    code VARCHAR(20) NOT NULL,
    tier INT NOT NULL CHECK (tier >= 0 AND tier <= 4),
    severity VARCHAR(10) NOT NULL CHECK (severity IN ('BLOCK', 'MAJOR', 'WARN')),

    -- Vietnamese messages for user
    message_vi TEXT NOT NULL,
    path_vi TEXT NOT NULL,

    -- Additional context
    context JSONB DEFAULT '{}',

    -- Which gate run this violation belongs to
    gate_run_number INT NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_violations_session_id
    ON violations(session_id);
CREATE INDEX IF NOT EXISTS idx_violations_session_run
    ON violations(session_id, gate_run_number);
CREATE INDEX IF NOT EXISTS idx_violations_tier
    ON violations(tier);


-- ════════════════════════════════════════════════════════════════════════════
-- Row Level Security (RLS)
-- ════════════════════════════════════════════════════════════════════════════

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE violations ENABLE ROW LEVEL SECURITY;

-- ── Profiles ──
DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
CREATE POLICY "Users can view own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

-- ── Research Sessions ──
DROP POLICY IF EXISTS "Users can view own sessions" ON research_sessions;
CREATE POLICY "Users can view own sessions"
    ON research_sessions FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own sessions" ON research_sessions;
CREATE POLICY "Users can insert own sessions"
    ON research_sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own sessions" ON research_sessions;
CREATE POLICY "Users can update own sessions"
    ON research_sessions FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own sessions" ON research_sessions;
CREATE POLICY "Users can delete own sessions"
    ON research_sessions FOR DELETE
    USING (auth.uid() = user_id);

-- ── Conversation Turns ──
DROP POLICY IF EXISTS "Users can view turns in own sessions" ON conversation_turns;
CREATE POLICY "Users can view turns in own sessions"
    ON conversation_turns FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM research_sessions WHERE user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can insert turns in own sessions" ON conversation_turns;
CREATE POLICY "Users can insert turns in own sessions"
    ON conversation_turns FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM research_sessions WHERE user_id = auth.uid()
        )
    );

-- ── Violations ──
DROP POLICY IF EXISTS "Users can view violations in own sessions" ON violations;
CREATE POLICY "Users can view violations in own sessions"
    ON violations FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM research_sessions WHERE user_id = auth.uid()
        )
    );

-- ── Service role bypass (backend operations via secret key) ──
DROP POLICY IF EXISTS "Service role full access to profiles" ON profiles;
CREATE POLICY "Service role full access to profiles"
    ON profiles FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

DROP POLICY IF EXISTS "Service role full access to research_sessions" ON research_sessions;
CREATE POLICY "Service role full access to research_sessions"
    ON research_sessions FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

DROP POLICY IF EXISTS "Service role full access to conversation_turns" ON conversation_turns;
CREATE POLICY "Service role full access to conversation_turns"
    ON conversation_turns FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

DROP POLICY IF EXISTS "Service role full access to violations" ON violations;
CREATE POLICY "Service role full access to violations"
    ON violations FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');


-- ════════════════════════════════════════════════════════════════════════════
-- Triggers
-- ════════════════════════════════════════════════════════════════════════════

-- ── updated_at trigger function (reusable) ──
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS update_research_sessions_updated_at ON research_sessions;
CREATE TRIGGER update_research_sessions_updated_at
    BEFORE UPDATE ON research_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ── Auto-increment turn_number on conversation turn insert ──
CREATE OR REPLACE FUNCTION set_turn_number()
RETURNS TRIGGER AS $$
BEGIN
    SELECT COALESCE(MAX(turn_number), 0) + 1
    INTO NEW.turn_number
    FROM conversation_turns
    WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS on_conversation_turn_insert ON conversation_turns;
CREATE TRIGGER on_conversation_turn_insert
    BEFORE INSERT ON conversation_turns
    FOR EACH ROW
    EXECUTE FUNCTION set_turn_number();

-- ── Update session updated_at when conversation turn is added ──
CREATE OR REPLACE FUNCTION update_session_on_turn()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE research_sessions
    SET updated_at = NOW()
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_turn_inserted ON conversation_turns;
CREATE TRIGGER on_turn_inserted
    AFTER INSERT ON conversation_turns
    FOR EACH ROW
    EXECUTE FUNCTION update_session_on_turn();
