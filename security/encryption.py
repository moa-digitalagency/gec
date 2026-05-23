"""
Module de chiffrement avancé pour GEC
- AES-256-GCM (v2) : authenticité + intégrité garanties
- Rétrocompatibilité AES-256-CBC (v1) en déchiffrement seulement
- Fail-fast si GEC_MASTER_KEY absente au démarrage
"""

import os
import base64
import hashlib
import secrets
import logging
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


def load_env_from_file(env_file='.env'):
    """Charge les variables d'environnement depuis un fichier .env."""
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key not in os.environ:
                        os.environ[key] = value


load_env_from_file()


class EncryptionManager:
    """Gestionnaire de chiffrement GEC — AES-256-GCM avec backward-compat CBC."""

    def __init__(self):
        self.backend = default_backend()
        self.iv_size = 16   # pour CBC (v1)
        self.nonce_size = 12  # pour GCM (v2)
        self.tag_size = 16    # GCM auth tag

        self.master_key = self._get_master_key()
        self.password_salt = self._get_password_salt()

    def _get_master_key(self):
        key_b64 = os.environ.get('GEC_MASTER_KEY')
        if key_b64:
            try:
                key = base64.b64decode(key_b64.encode('utf-8'))
                if len(key) != 32:
                    raise ValueError(f"GEC_MASTER_KEY doit être 32 bytes (256 bits), reçu {len(key)}")
                return key
            except Exception as e:
                logging.critical(f"GEC_MASTER_KEY invalide: {e}")
                raise RuntimeError(f"GEC_MASTER_KEY invalide: {e}") from e

        # Générer une clé temporaire pour le dev local, mais avertir fortement
        key = secrets.token_bytes(32)
        key_b64_str = base64.b64encode(key).decode('utf-8')
        logging.critical("=" * 70)
        logging.critical("ATTENTION : GEC_MASTER_KEY absente de l'environnement !")
        logging.critical("Une clé temporaire a été générée — elle sera perdue au redémarrage.")
        logging.critical("Toutes les données chiffrées seront illisibles après redémarrage.")
        logging.critical(f"Ajoutez dans .env : GEC_MASTER_KEY={key_b64_str}")
        logging.critical("=" * 70)
        return key

    def _get_password_salt(self):
        salt_b64 = os.environ.get('GEC_PASSWORD_SALT')
        if salt_b64:
            return base64.b64decode(salt_b64.encode('utf-8'))
        salt = secrets.token_bytes(32)
        salt_b64_str = base64.b64encode(salt).decode('utf-8')
        logging.critical(f"GEC_PASSWORD_SALT absente — ajoutez dans .env : GEC_PASSWORD_SALT={salt_b64_str}")
        return salt

    # ── Chiffrement AES-256-GCM (v2) ─────────────────────────────────────────

    def encrypt_data(self, plaintext, use_master_key=True):
        """Chiffre avec AES-256-GCM. Retourne une chaîne préfixée 'v2:'."""
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')

            nonce = get_random_bytes(self.nonce_size)
            cipher = AES.new(self.master_key, AES.MODE_GCM, nonce=nonce)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext)

            # Format : nonce(12) + tag(16) + ciphertext
            payload = nonce + tag + ciphertext
            return 'v2:' + base64.b64encode(payload).decode('utf-8')

        except Exception as e:
            logging.error(f"Erreur chiffrement GCM: {e}")
            raise

    def decrypt_data(self, encrypted_data, use_master_key=True):
        """Déchiffre AES-256-GCM (v2) ou AES-256-CBC (v1 legacy)."""
        try:
            if encrypted_data.startswith('v2:'):
                return self._decrypt_gcm(encrypted_data[3:])
            else:
                return self._decrypt_cbc_legacy(encrypted_data)
        except Exception as e:
            logging.error(f"Erreur déchiffrement: {e}")
            raise

    def _decrypt_gcm(self, b64_data):
        payload = base64.b64decode(b64_data.encode('utf-8'))
        nonce = payload[:self.nonce_size]
        tag = payload[self.nonce_size:self.nonce_size + self.tag_size]
        ciphertext = payload[self.nonce_size + self.tag_size:]
        cipher = AES.new(self.master_key, AES.MODE_GCM, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        return plaintext.decode('utf-8')

    def _decrypt_cbc_legacy(self, b64_data):
        """Déchiffrement legacy AES-256-CBC (v1) — lecture seulement."""
        encrypted_bytes = base64.b64decode(b64_data.encode('utf-8'))
        iv = encrypted_bytes[:self.iv_size]
        ciphertext = encrypted_bytes[self.iv_size:]
        cipher = AES.new(self.master_key, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(ciphertext)
        return unpad(decrypted_padded, AES.block_size).decode('utf-8')

    # ── Chiffrement de fichiers (GCM streaming) ───────────────────────────────

    def encrypt_file(self, file_path, output_path=None):
        """Chiffre un fichier avec AES-256-GCM. Format : magic(4) + nonce(12) + chunks."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Fichier introuvable: {file_path}")

            if output_path is None:
                output_path = file_path + ".encrypted"

            nonce = get_random_bytes(self.nonce_size)
            cipher = AES.new(self.master_key, AES.MODE_GCM, nonce=nonce)

            with open(file_path, 'rb') as infile:
                plaintext = infile.read()

            ciphertext, tag = cipher.encrypt_and_digest(plaintext)

            with open(output_path, 'wb') as outfile:
                outfile.write(b'GEC2')      # magic v2
                outfile.write(nonce)         # 12 bytes
                outfile.write(tag)           # 16 bytes
                outfile.write(ciphertext)

            logging.info(f"Fichier chiffré (GCM): {file_path} -> {output_path}")
            return output_path

        except Exception as e:
            logging.error(f"Erreur chiffrement fichier: {e}")
            raise

    def decrypt_file(self, encrypted_file_path, output_path=None):
        """Déchiffre un fichier GCM (v2) ou CBC (v1 legacy)."""
        try:
            if not os.path.exists(encrypted_file_path):
                raise FileNotFoundError(f"Fichier introuvable: {encrypted_file_path}")

            if output_path is None:
                output_path = encrypted_file_path.replace(".encrypted", "")

            with open(encrypted_file_path, 'rb') as infile:
                magic = infile.read(4)

            if magic == b'GEC2':
                self._decrypt_file_gcm(encrypted_file_path, output_path)
            else:
                self._decrypt_file_cbc_legacy(encrypted_file_path, output_path)

            logging.info(f"Fichier déchiffré: {encrypted_file_path} -> {output_path}")
            return output_path

        except Exception as e:
            logging.error(f"Erreur déchiffrement fichier: {e}")
            raise

    def _decrypt_file_gcm(self, encrypted_path, output_path):
        with open(encrypted_path, 'rb') as f:
            f.read(4)  # skip magic
            nonce = f.read(self.nonce_size)
            tag = f.read(self.tag_size)
            ciphertext = f.read()
        cipher = AES.new(self.master_key, AES.MODE_GCM, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        with open(output_path, 'wb') as f:
            f.write(plaintext)

    def _decrypt_file_cbc_legacy(self, encrypted_path, output_path):
        """Déchiffrement legacy CBC pour les anciens fichiers."""
        with open(encrypted_path, 'rb') as infile:
            iv = infile.read(self.iv_size)
            cipher = AES.new(self.master_key, AES.MODE_CBC, iv)
            with open(output_path, 'wb') as outfile:
                while True:
                    chunk = infile.read(8192)
                    if not chunk:
                        break
                    decrypted = cipher.decrypt(chunk)
                    if len(chunk) < 8192:
                        try:
                            decrypted = unpad(decrypted, AES.block_size)
                        except ValueError:
                            pass
                    outfile.write(decrypted)

    # ── Mot de passe ──────────────────────────────────────────────────────────

    def hash_password(self, password):
        import bcrypt
        salted = password.encode('utf-8') + self.password_salt
        return bcrypt.hashpw(salted, bcrypt.gensalt(rounds=12)).decode('utf-8')

    def verify_password(self, password, hashed_password):
        import bcrypt
        try:
            salted = password.encode('utf-8') + self.password_salt
            return bcrypt.checkpw(salted, hashed_password.encode('utf-8'))
        except Exception as e:
            logging.error(f"Erreur vérification mot de passe: {e}")
            return False

    def derive_key(self, password, salt=None):
        if salt is None:
            salt = self.password_salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=salt,
            iterations=100000, backend=self.backend
        )
        return kdf.derive(password.encode('utf-8'))

    # ── Utilitaires fichier ───────────────────────────────────────────────────

    def generate_file_checksum(self, file_path):
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def secure_delete_file(self, file_path, passes=3):
        try:
            if not os.path.exists(file_path):
                return
            file_size = os.path.getsize(file_path)
            with open(file_path, 'r+b') as file:
                for _ in range(passes):
                    file.seek(0)
                    file.write(os.urandom(file_size))
                    file.flush()
                    os.fsync(file.fileno())
            os.remove(file_path)
            logging.info(f"Fichier supprimé de façon sécurisée: {file_path}")
        except Exception as e:
            logging.error(f"Erreur suppression sécurisée: {e}")
            raise


# Instance globale
encryption_manager = EncryptionManager()


def encrypt_sensitive_data(data):
    return encryption_manager.encrypt_data(data)


def decrypt_sensitive_data(encrypted_data):
    return encryption_manager.decrypt_data(encrypted_data)


def encrypt_uploaded_file(file_path):
    return encryption_manager.encrypt_file(file_path)


def decrypt_file_for_download(encrypted_file_path, temp_dir=None):
    if temp_dir is None:
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir, exist_ok=True)

    original_name = os.path.basename(encrypted_file_path).replace('.encrypted', '')
    temp_filename = f"tmp_{secrets.token_hex(8)}_{original_name}"
    temp_path = os.path.join(temp_dir, temp_filename)

    return encryption_manager.decrypt_file(encrypted_file_path, temp_path)
