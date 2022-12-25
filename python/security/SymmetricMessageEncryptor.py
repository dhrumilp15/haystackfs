"""Generic encryption/decryption service for messages using symmetric encryption."""


class SymmetricMessageEncryptor:
    """Generic encryption/decryption service for messages using symmetric encryption."""

    def __init__(self, algorithm, config=None, key: str = None):
        """
        Initialize Message Encryption for symmetric ciphers.

        Args:
            algorithm: The algorithm with which to encrypt or decrypt
            key: The key with which to encrypt/decrypt messages
        """
        self.config = config
        self.key = key
        if 'KEY' in self.config:
            self.key = self.config.KEY
        self.cipher = algorithm(self.key)

    def encrypt(self, message: str) -> str:
        """
        Encrypt a message.

        Args:
            message - The message to encrypt

        Returns:
            The encrypted message.
        """
        return self.cipher.encrypt(message.encode()).decode()

    def decrypt(self, message: str) -> str:
        """
        Decrypt a message.

        Args:
            message - The message to decrypt

        Returns:
            The decrypted message.
        """
        return self.cipher.decrypt(message).decode()
