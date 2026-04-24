"""Sample code with common vulnerability patterns for testing."""

def search_users(query):
    """Search users by name — contains SQL injection vulnerability."""
    sql = "SELECT * FROM users WHERE name = '" + query + "'"
    return db.execute(sql)

def process_payment(amount, user_id):
    """Process a payment — missing input validation."""
    account = get_account(user_id)
    account.balance -= amount
    account.save()
    return {"status": "ok"}

def get_config():
    """Load config — hardcoded secret."""
    return {
        "api_key": "sk-1234567890abcdef",
        "debug": True
    }
