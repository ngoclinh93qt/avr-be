-- Migration: Add token tracking to profiles
-- Run this in Supabase SQL Editor

ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS tokens_used_total  BIGINT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS tokens_used_month  BIGINT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS token_limit_month  BIGINT NOT NULL DEFAULT 50000,
  ADD COLUMN IF NOT EXISTS token_reset_at     TIMESTAMPTZ NOT NULL DEFAULT (date_trunc('month', now() AT TIME ZONE 'UTC') + interval '1 month');

-- Atomic increment function to avoid race conditions
CREATE OR REPLACE FUNCTION increment_user_tokens(p_user_id UUID, p_amount BIGINT)
RETURNS TABLE(tokens_used_month BIGINT, token_limit_month BIGINT, token_reset_at TIMESTAMPTZ) AS $$
BEGIN
  -- Reset monthly counter if past reset date
  UPDATE profiles
  SET tokens_used_month = 0,
      token_reset_at = date_trunc('month', now() AT TIME ZONE 'UTC') + interval '1 month'
  WHERE id = p_user_id AND token_reset_at <= now();

  -- Atomic increment
  UPDATE profiles
  SET tokens_used_month = tokens_used_month + p_amount,
      tokens_used_total = tokens_used_total + p_amount
  WHERE id = p_user_id;

  RETURN QUERY
  SELECT p.tokens_used_month, p.token_limit_month, p.token_reset_at
  FROM profiles p WHERE p.id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Monthly reset function (for cron job)
CREATE OR REPLACE FUNCTION reset_monthly_tokens()
RETURNS void AS $$
  UPDATE profiles
  SET tokens_used_month = 0,
      token_reset_at = date_trunc('month', now() AT TIME ZONE 'UTC') + interval '1 month'
  WHERE token_reset_at <= now();
$$ LANGUAGE sql SECURITY DEFINER;

-- Grant execute to service role
GRANT EXECUTE ON FUNCTION increment_user_tokens(UUID, BIGINT) TO service_role;
GRANT EXECUTE ON FUNCTION reset_monthly_tokens() TO service_role;
