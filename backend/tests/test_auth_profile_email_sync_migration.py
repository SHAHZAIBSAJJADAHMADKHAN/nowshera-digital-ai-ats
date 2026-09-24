from pathlib import Path


def test_auth_email_sync_trigger_is_narrow_and_does_not_provision_profiles() -> None:
    sql = (Path(__file__).parents[2] / "supabase/migrations/20260925110000_sync_profile_email_from_auth.sql").read_text(encoding="utf-8").lower()

    assert "after update of email on auth.users" in sql
    assert "when (old.email is distinct from new.email)" in sql
    assert "where id = new.id" in sql
    assert "set email = lower(btrim(new.email))" in sql
    assert "insert into public.profiles" not in sql
    assert "role =" not in sql
    assert "is_active" not in sql
    assert "full_name" not in sql
    assert "phone" not in sql


def test_auth_email_sync_function_is_not_browser_callable() -> None:
    sql = (Path(__file__).parents[2] / "supabase/migrations/20260925110000_sync_profile_email_from_auth.sql").read_text(encoding="utf-8").lower()

    assert "security definer" in sql
    assert "set search_path = ''" in sql
    assert "revoke all on function public.sync_profile_email_from_auth() from public, anon, authenticated" in sql
