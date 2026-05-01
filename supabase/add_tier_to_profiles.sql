-- ════════════════════════════════════════════════════════════════════════════
-- UPDATE: Add Subscription/Tier Management columns to existing profiles table
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql
-- ════════════════════════════════════════════════════════════════════════════

-- 1. Add columns (using IF NOT EXISTS is safe if some columns were already there)
ALTER TABLE profiles 
    ADD COLUMN IF NOT EXISTS tier VARCHAR(10) DEFAULT 'free' CHECK (tier IN ('free', 'paid')),
    ADD COLUMN IF NOT EXISTS runs_today INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS paid_until TIMESTAMPTZ;

-- 2. Dành cho admin: Update 1 tài khoản email cụ thể lên gói paid
-- Thay thế 'YOUR_ADMIN_EMAIL@example.com' bằng email tài khoản thực tế của bạn
UPDATE profiles
SET tier = 'paid', 
    paid_until = NOW() + INTERVAL '1 year'
WHERE email = 'admin@avr.com';

-- Hoặc Update toàn bộ users lên gói paid (Dành cho bản Open Beta)
-- UPDATE profiles SET tier = 'paid', paid_until = NOW() + INTERVAL '1 year';
