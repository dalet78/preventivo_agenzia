"""Generate a new password and salted scrypt hash for the private portal."""
from hashlib import scrypt
from secrets import token_bytes, token_urlsafe

password = token_urlsafe(24)
salt = token_bytes(16)
digest = scrypt(password.encode(), salt=salt, n=32768, r=8, p=1, maxmem=64*1024*1024)
print(f"Password: {password}")
print(f"PORTAL_PASSWORD_HASH={salt.hex()}:{digest.hex()}")
