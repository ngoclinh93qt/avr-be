-- ════════════════════════════════════════════════════════════════════════════
-- FIX: Improved handle_new_user() trigger for signup 500 errors
-- Run this in Supabase SQL Editor
-- ════════════════════════════════════════════════════════════════════════════

-- 1. Drop existing trigger and function
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS handle_new_user();

-- 2. Recreate with better error handling
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert profile with safe defaults
    INSERT INTO profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', '')
    )
    ON CONFLICT (id) DO NOTHING; -- Skip if profile already exists
    
    RETURN NEW;
EXCEPTION WHEN others THEN
    -- Log error but don't fail signup - user account is created, profile can be created later
    RAISE WARNING 'Failed to create profile for user %: %', NEW.id, SQLERRM;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Recreate trigger
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- 4. Clean up: Check for orphaned/duplicate profiles
SELECT 'Duplicate profiles (keep newest):' as info, 
       id, email, COUNT(*) as count,
       MAX(created_at) as newest
FROM profiles
GROUP BY id, email
HAVING COUNT(*) > 1;

-- 5. Clean up orphaned auth users (optional - uncomment if needed)
-- DELETE FROM auth.users 
-- WHERE id NOT IN (SELECT id FROM profiles)
-- AND created_at < NOW() - INTERVAL '1 hour';

-- 6. Verify
SELECT COUNT(*) as profile_count FROM profiles;
SELECT COUNT(*) as auth_users_count FROM auth.users;
