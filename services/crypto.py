import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Centralized encryption key (fixed 32-byte base64-encoded key)
ENCRYPTION_KEY = b'MzI2NDUzMjE0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc='  # Valid key
CIPHER = Fernet(ENCRYPTION_KEY)

logger.info("Initialized CIPHER for encryption/decryption")