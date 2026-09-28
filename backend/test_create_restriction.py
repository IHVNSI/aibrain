#!/usr/bin/env python3
"""Test SQL restrictions - hardcoded dangerous commands vs Security UI configurable."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.sql_guard import _dynamic_blocklist, contains_restricted

print("=" * 60)
print("SQL RESTRICTION TEST")
print("=" * 60)

blocklist = _dynamic_blocklist()
print(f"\nHardcoded forbidden commands: {len(blocklist)} items total")
print(f"Commands: {', '.join(sorted(blocklist))}")

# Test the actual restriction
print("\nTesting restriction detection:")
test_prompts = [
    # These should now be ALLOWED (not in hardcoded list)
    ("create a new customer account", True, "CREATE - Should be ALLOWED"),
    ("CREATE TABLE users", True, "CREATE - Should be ALLOWED"),
    ("INSERT INTO users VALUES", True, "INSERT - Should be ALLOWED"),
    ("UPDATE users SET name='John'", True, "UPDATE - Should be ALLOWED"),
    ("DELETE FROM users", True, "DELETE - Should be ALLOWED"),
    ("DROP TABLE users", True, "DROP - Should be ALLOWED"),
    ("ALTER TABLE users ADD COLUMN", True, "ALTER - Should be ALLOWED"),
    ("TRUNCATE TABLE users", True, "TRUNCATE - Should be ALLOWED"),
    
    # These should remain BLOCKED (hardcoded dangerous)
    ("GRANT SELECT ON users", False, "GRANT - Should be BLOCKED"),
    ("REVOKE ALL ON users", False, "REVOKE - Should be BLOCKED"),
    ("PRAGMA table_info(users)", False, "PRAGMA - Should be BLOCKED"),
    ("EXECUTE sp_something", False, "EXECUTE - Should be BLOCKED"),
]

for prompt, should_pass, desc in test_prompts:
    blocked, keyword = contains_restricted(prompt)
    status = "❌ BLOCKED" if blocked else "✅ ALLOWED"
    expected = "✅" if (not blocked and should_pass) or (blocked and not should_pass) else "❌"
    print(f"{expected} {status:12} | {prompt:40} | {desc}")
    if blocked:
        print(f"    Keyword: {keyword}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
