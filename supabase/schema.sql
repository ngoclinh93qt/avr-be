-- ════════════════════════════════════════════════════════════════════════════
-- AVR Database Schema for Supabase
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql
-- ════════════════════════════════════════════════════════════════════════════

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ════════════════════════════════════════════════════════════════════════════
-- User Profiles (extends Supabase Auth)
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,
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

-- Trigger for new user
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- ════════════════════════════════════════════════════════════════════════════
-- Research Sessions
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Input
    abstract TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'auto',

    -- Processing state
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed

    -- Results
    keywords JSONB,
    assessment JSONB,
    analysis_result JSONB,

    -- Metadata
    total_papers_found INT DEFAULT 0,
    total_papers_ranked INT DEFAULT 0,
    avg_similarity FLOAT DEFAULT 0.0,
    processing_time_seconds FLOAT DEFAULT 0.0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for user queries
CREATE INDEX IF NOT EXISTS idx_research_sessions_user_id ON research_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_research_sessions_created_at ON research_sessions(created_at DESC);

-- ════════════════════════════════════════════════════════════════════════════
-- Research Papers (linked to sessions)
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS research_papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,

    -- Paper metadata
    pmid VARCHAR(50),
    title TEXT NOT NULL,
    authors JSONB DEFAULT '[]',
    abstract TEXT,
    year INT,
    journal TEXT,
    doi TEXT,

    -- Ranking
    similarity FLOAT DEFAULT 0.0,
    source VARCHAR(20) DEFAULT 'pubmed', -- pubmed, scholar

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for session queries
CREATE INDEX IF NOT EXISTS idx_research_papers_session_id ON research_papers(session_id);
CREATE INDEX IF NOT EXISTS idx_research_papers_similarity ON research_papers(similarity DESC);

-- ════════════════════════════════════════════════════════════════════════════
-- Row Level Security (RLS)
-- ════════════════════════════════════════════════════════════════════════════

-- Enable RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_papers ENABLE ROW LEVEL SECURITY;

-- Profiles: users can only see/edit their own profile
CREATE POLICY "Users can view own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

-- Research Sessions: users can only see their own sessions
CREATE POLICY "Users can view own sessions"
    ON research_sessions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sessions"
    ON research_sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions"
    ON research_sessions FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions"
    ON research_sessions FOR DELETE
    USING (auth.uid() = user_id);

-- Research Papers: users can see papers from their sessions
CREATE POLICY "Users can view papers from own sessions"
    ON research_papers FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM research_sessions WHERE user_id = auth.uid()
        )
    );

-- Service role bypass (for backend operations)
CREATE POLICY "Service role full access to sessions"
    ON research_sessions FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

CREATE POLICY "Service role full access to papers"
    ON research_papers FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ════════════════════════════════════════════════════════════════════════════
-- Updated_at trigger
-- ════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_research_sessions_updated_at
    BEFORE UPDATE ON research_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
