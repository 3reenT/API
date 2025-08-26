"""Utility module to generate a secure SECRET_KEY"""
import secrets

def generate_secret_key():
    """Generate and print a secure 64-character secret key."""
    key = secrets.token_hex(32)
    print("Generated SECRET_KEY:", key)


if __name__ == "__main__":
    generate_secret_key()
