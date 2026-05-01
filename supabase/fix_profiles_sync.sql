-- ════════════════════════════════════════════════════════════════════════════
-- FIX: Sync profiles from auth.users + set paid tier for admin
-- Run in Supabase SQL Editor
-- ════════════════════════════════════════════════════════════════════════════

-- Step 1: Add columns if missing (idempotent)
ALTER TABLE profiles 
    ADD COLUMN IF NOT EXISTS tier VARCHAR(10) DEFAULT 'free' CHECK (tier IN ('free', 'paid')),
    ADD COLUMN IF NOT EXISTS runs_today INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS paid_until TIMESTAMPTZ;

-- Step 2: Sync TẤT CẢ users từ auth.users vào profiles (an toàn để chạy lại)
-- Điều này giải quyết trường hợp profiles bị thiếu do trigger không chạy
INSERT INTO profiles (id, email, full_name)
SELECT 
    u.id,
    u.email,
    COALESCE(u.raw_user_meta_data->>'full_name', u.raw_user_meta_data->>'name', '')
FROM auth.users u
ON CONFLICT (id) DO UPDATE
SET 
    email = EXCLUDED.email,
    full_name = CASE 
        WHEN profiles.full_name IS NULL OR profiles.full_name = '' 
        THEN EXCLUDED.full_name 
        ELSE profiles.full_name 
    END;

-- Step 3: Grant paid tier cho admin@avr.com (dùng user UUID từ auth.users)
UPDATE profiles
SET 
    tier = 'paid',
    paid_until = NOW() + INTERVAL '1 year'
WHERE id IN (
    SELECT id FROM auth.users WHERE email = 'admin@avr.com'
);

-- Step 4: Kiểm tra kết quả
SELECT p.id, p.email, p.tier, p.paid_until, p.runs_today
FROM profiles p
JOIN auth.users u ON p.id = u.id;
