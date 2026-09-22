import bcrypt

def hash_password(plain_password: str) -> str:
    """Turn a plain-text password into a secure hash for storage."""
    # bcrypt works with bytes, so we encode the string first
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
    # store it as a string in the database
    return hashed.decode('utf-8')

def check_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against a stored hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )