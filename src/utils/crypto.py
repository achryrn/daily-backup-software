from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import keyring

class CredentialManager:
    """Secure credential storage using OS keyring and encryption"""
    
    SERVICE_NAME = "BackupManagerPro"
    
    def __init__(self):
        self.key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_encryption_key(self):
        """Get or create encryption key stored in OS keyring"""
        key = keyring.get_password(self.SERVICE_NAME, "encryption_key")
        
        if key is None:
            # Generate new key
            key = Fernet.generate_key().decode()
            keyring.set_password(self.SERVICE_NAME, "encryption_key", key)
        
        return key.encode()
    
    def store_token(self, service_id: str, token_data: dict):
        """Store encrypted token data"""
        try:
            # Convert token data to JSON string
            import json
            token_json = json.dumps(token_data)
            
            # Encrypt the token
            encrypted_token = self.cipher.encrypt(token_json.encode())
            
            # Store in keyring as base64
            encoded_token = base64.b64encode(encrypted_token).decode()
            keyring.set_password(self.SERVICE_NAME, f"token_{service_id}", encoded_token)
            
            return True
        except Exception as e:
            print(f"Error storing token: {e}")
            return False
    
    def retrieve_token(self, service_id: str) -> dict:
        """Retrieve and decrypt token data"""
        try:
            # Get from keyring
            encoded_token = keyring.get_password(self.SERVICE_NAME, f"token_{service_id}")
            if encoded_token is None:
                return None
            
            # Decode and decrypt
            encrypted_token = base64.b64decode(encoded_token)
            decrypted_token = self.cipher.decrypt(encrypted_token)
            
            # Parse JSON
            import json
            token_data = json.loads(decrypted_token.decode())
            
            return token_data
        except Exception as e:
            print(f"Error retrieving token: {e}")
            return None
    
    def delete_token(self, service_id: str):
        """Delete stored token"""
        try:
            keyring.delete_password(self.SERVICE_NAME, f"token_{service_id}")
            return True
        except Exception as e:
            print(f"Error deleting token: {e}")
            return False
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt arbitrary data"""
        encrypted = self.cipher.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt arbitrary data"""
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted = self.cipher.decrypt(encrypted_bytes)
        return decrypted.decode()

class FileHasher:
    """Utility class for file integrity verification"""
    
    @staticmethod
    def calculate_file_hash(file_path: str, algorithm='sha256', chunk_size: int = 8192) -> str:
        """Calculate hash of a file"""
        if algorithm == 'sha256':
            hasher = hashes.SHA256()
        elif algorithm == 'md5':
            hasher = hashes.MD5()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        digest = hashes.Hash(hasher)
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    digest.update(chunk)
            
            return digest.finalize().hex()
        except (IOError, OSError) as e:
            raise Exception(f"Error calculating hash for {file_path}: {e}")
    
    @staticmethod
    def verify_file_integrity(source_path: str, target_path: str) -> bool:
        """Verify two files have the same content by comparing hashes"""
        try:
            source_hash = FileHasher.calculate_file_hash(source_path)
            target_hash = FileHasher.calculate_file_hash(target_path)
            return source_hash == target_hash
        except Exception:
            return False

# Global instances
credential_manager = CredentialManager()
file_hasher = FileHasher()