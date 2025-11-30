"""
SHADOW-MESH Cryptographic Utilities
Handles RSA key generation and Fernet symmetric encryption.
"""

import base64
import os
from typing import Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding


class CryptoUtils:
    """Handles all cryptographic operations for SHADOW-MESH."""
    
    RSA_KEY_SIZE = 2048
    RSA_PUBLIC_EXPONENT = 65537
    
    def __init__(self) -> None:
        """Initialize crypto utils and generate RSA key pair."""
        self._private_key, self._public_key = self._generate_rsa_keypair()
    
    def _generate_rsa_keypair(self) -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """Generate a new RSA key pair."""
        private_key = rsa.generate_private_key(
            public_exponent=self.RSA_PUBLIC_EXPONENT,
            key_size=self.RSA_KEY_SIZE,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        return private_key, public_key
    
    def get_public_key_pem(self) -> str:
        """Get the public key in PEM format as a base64 string."""
        pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(pem).decode('utf-8')
    
    @staticmethod
    def load_public_key_from_pem(pem_b64: str) -> rsa.RSAPublicKey:
        """Load a public key from a base64-encoded PEM string."""
        pem = base64.b64decode(pem_b64.encode('utf-8'))
        return serialization.load_pem_public_key(pem, backend=default_backend())
    
    @staticmethod
    def generate_fernet_key() -> bytes:
        """Generate a new Fernet symmetric key."""
        return Fernet.generate_key()
    
    @staticmethod
    def encrypt_message_with_fernet(message: str, key: bytes) -> bytes:
        """Encrypt a message using Fernet symmetric encryption."""
        fernet = Fernet(key)
        return fernet.encrypt(message.encode('utf-8'))
    
    @staticmethod
    def decrypt_message_with_fernet(encrypted_message: bytes, key: bytes) -> str:
        """Decrypt a message using Fernet symmetric encryption."""
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_message).decode('utf-8')
    
    @staticmethod
    def encrypt_key_with_rsa(symmetric_key: bytes, public_key: rsa.RSAPublicKey) -> bytes:
        """Encrypt a symmetric key using RSA public key."""
        return public_key.encrypt(
            symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def decrypt_key_with_rsa(self, encrypted_key: bytes) -> bytes:
        """Decrypt a symmetric key using our RSA private key."""
        return self._private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def encrypt_for_recipient(self, message: str, recipient_public_key_pem: str) -> Tuple[bytes, bytes]:
        """
        Encrypt a message for a recipient using hybrid encryption.
        
        Returns:
            Tuple of (encrypted_message, encrypted_symmetric_key)
        """
        # Generate a one-time symmetric key
        symmetric_key = self.generate_fernet_key()
        
        # Encrypt the message with the symmetric key
        encrypted_message = self.encrypt_message_with_fernet(message, symmetric_key)
        
        # Encrypt the symmetric key with recipient's public key
        recipient_public_key = self.load_public_key_from_pem(recipient_public_key_pem)
        encrypted_key = self.encrypt_key_with_rsa(symmetric_key, recipient_public_key)
        
        return encrypted_message, encrypted_key
    
    def decrypt_received_message(self, encrypted_message: bytes, encrypted_key: bytes) -> str:
        """
        Decrypt a received message using our private key.
        
        Args:
            encrypted_message: The Fernet-encrypted message
            encrypted_key: The RSA-encrypted symmetric key
            
        Returns:
            The decrypted message string
        """
        # Decrypt the symmetric key with our private key
        symmetric_key = self.decrypt_key_with_rsa(encrypted_key)
        
        # Decrypt the message with the symmetric key
        return self.decrypt_message_with_fernet(encrypted_message, symmetric_key)
