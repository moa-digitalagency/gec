"""
Module de cryptage avancé pour GEC
Gère le cryptage des données sensibles et des fichiers
"""

import os
import base64
import hashlib
import secrets
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import logging

class EncryptionManager:
    """Gestionnaire de cryptage pour l'application GEC"""
    
    def __init__(self):
        self.backend = default_backend()
        self.key_size = 256  # Taille de clé AES-256
        self.iv_size = 16    # Taille du vecteur d'initialisation
        
        # Générer ou récupérer la clé maître depuis les variables d'environnement
        self.master_key = self._get_or_create_master_key()
        
        # Clé de hachage pour les mots de passe
        self.password_salt = self._get_password_salt()
    
    def _get_or_create_master_key(self):
        """Récupère ou crée la clé maître de cryptage"""
        master_key_env = os.environ.get('GEC_MASTER_KEY')
        if master_key_env:
            return base64.b64decode(master_key_env.encode('utf-8'))
        
        # Générer une nouvelle clé maître
        master_key = secrets.token_bytes(32)  # 256 bits
        master_key_b64 = base64.b64encode(master_key).decode('utf-8')
        
        # Avertir l'administrateur de sauvegarder cette clé - SANS EXPOSER LA CLÉ
        logging.critical("NOUVELLE CLÉ MAÎTRE GÉNÉRÉE - Configurez GEC_MASTER_KEY dans les variables d'environnement")
        logging.critical("IMPORTANT: Clé générée automatiquement - configurez GEC_MASTER_KEY pour la persistence")
        
        return master_key
    
    def _get_password_salt(self):
        """Récupère ou crée le sel pour les mots de passe"""
        salt_env = os.environ.get('GEC_PASSWORD_SALT')
        if salt_env:
            return base64.b64decode(salt_env.encode('utf-8'))
        
        # Générer un nouveau sel
        salt = secrets.token_bytes(32)
        salt_b64 = base64.b64encode(salt).decode('utf-8')
        
        logging.critical("NOUVEAU SEL GÉNÉRÉ - Configurez GEC_PASSWORD_SALT dans les variables d'environnement") 
        logging.critical("IMPORTANT: Sel généré automatiquement - configurez GEC_PASSWORD_SALT pour la persistence")
        
        return salt
    
    def derive_key(self, password, salt=None):
        """Dérive une clé à partir d'un mot de passe"""
        if salt is None:
            salt = self.password_salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        
        return kdf.derive(password.encode('utf-8'))
    
    def encrypt_data(self, plaintext, use_master_key=True):
        """
        Crypte des données avec AES-256-CBC
        
        Args:
            plaintext (str): Texte à crypter
            use_master_key (bool): Utiliser la clé maître ou dériver une clé
            
        Returns:
            str: Données cryptées encodées en base64
        """
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')
            
            # Générer un vecteur d'initialisation aléatoire
            iv = get_random_bytes(self.iv_size)
            
            # Utiliser la clé maître ou en dériver une nouvelle
            if use_master_key:
                key = self.master_key
            else:
                # Utiliser un sel aléatoire pour cette opération
                salt = get_random_bytes(32)
                key = self.derive_key(str(datetime.now()), salt)
            
            # Créer le cipher AES
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # Padding et cryptage
            padded_data = pad(plaintext, AES.block_size)
            encrypted_data = cipher.encrypt(padded_data)
            
            # Combiner IV + données cryptées
            result = iv + encrypted_data
            
            # Encoder en base64 pour le stockage
            return base64.b64encode(result).decode('utf-8')
            
        except Exception as e:
            logging.error(f"Erreur lors du cryptage: {e}")
            raise
    
    def decrypt_data(self, encrypted_data, use_master_key=True):
        """
        Décrypte des données AES-256-CBC
        
        Args:
            encrypted_data (str): Données cryptées en base64
            use_master_key (bool): Utiliser la clé maître
            
        Returns:
            str: Texte décrypté
        """
        try:
            # Décoder depuis base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extraire IV et données cryptées
            iv = encrypted_bytes[:self.iv_size]
            ciphertext = encrypted_bytes[self.iv_size:]
            
            # Utiliser la clé maître
            if use_master_key:
                key = self.master_key
            else:
                # Cette méthode nécessiterait de stocker le sel utilisé
                # Pour l'instant, on utilise la clé maître
                key = self.master_key
            
            # Créer le cipher AES
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # Décryptage et suppression du padding
            decrypted_padded = cipher.decrypt(ciphertext)
            decrypted_data = unpad(decrypted_padded, AES.block_size)
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logging.error(f"Erreur lors du décryptage: {e}")
            raise
    
    def encrypt_file(self, file_path, output_path=None):
        """
        Crypte un fichier
        
        Args:
            file_path (str): Chemin du fichier à crypter
            output_path (str): Chemin de sortie (optionnel)
            
        Returns:
            str: Chemin du fichier crypté
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Fichier introuvable: {file_path}")
            
            if output_path is None:
                output_path = file_path + ".encrypted"
            
            # Générer un vecteur d'initialisation
            iv = get_random_bytes(self.iv_size)
            
            # Créer le cipher
            cipher = AES.new(self.master_key, AES.MODE_CBC, iv)
            
            with open(file_path, 'rb') as infile, open(output_path, 'wb') as outfile:
                # Écrire l'IV au début du fichier
                outfile.write(iv)
                
                # Crypter le fichier par blocs
                while True:
                    chunk = infile.read(8192)
                    if len(chunk) == 0:
                        break
                    elif len(chunk) % 16 != 0:
                        # Padding pour le dernier bloc
                        chunk = pad(chunk, AES.block_size)
                    
                    encrypted_chunk = cipher.encrypt(chunk)
                    outfile.write(encrypted_chunk)
            
            logging.info(f"Fichier crypté: {file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logging.error(f"Erreur lors du cryptage du fichier: {e}")
            raise
    
    def decrypt_file(self, encrypted_file_path, output_path=None):
        """
        Décrypte un fichier
        
        Args:
            encrypted_file_path (str): Chemin du fichier crypté
            output_path (str): Chemin de sortie (optionnel)
            
        Returns:
            str: Chemin du fichier décrypté
        """
        try:
            if not os.path.exists(encrypted_file_path):
                raise FileNotFoundError(f"Fichier introuvable: {encrypted_file_path}")
            
            if output_path is None:
                output_path = encrypted_file_path.replace(".encrypted", "")
            
            with open(encrypted_file_path, 'rb') as infile:
                # Lire l'IV
                iv = infile.read(self.iv_size)
                
                # Créer le cipher
                cipher = AES.new(self.master_key, AES.MODE_CBC, iv)
                
                with open(output_path, 'wb') as outfile:
                    # Décrypter le fichier par blocs
                    while True:
                        chunk = infile.read(8192)
                        if len(chunk) == 0:
                            break
                        
                        decrypted_chunk = cipher.decrypt(chunk)
                        
                        # Supprimer le padding du dernier bloc
                        if len(chunk) < 8192:
                            try:
                                decrypted_chunk = unpad(decrypted_chunk, AES.block_size)
                            except ValueError:
                                # Si le padding n'est pas valide, ignorer
                                pass
                        
                        outfile.write(decrypted_chunk)
            
            logging.info(f"Fichier décrypté: {encrypted_file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logging.error(f"Erreur lors du décryptage du fichier: {e}")
            raise
    
    def hash_password(self, password):
        """
        Hache un mot de passe avec bcrypt et un sel personnalisé
        
        Args:
            password (str): Mot de passe à hacher
            
        Returns:
            str: Hash du mot de passe
        """
        import bcrypt
        
        # Combiner le mot de passe avec notre sel personnalisé
        salted_password = password.encode('utf-8') + self.password_salt
        
        # Hacher avec bcrypt
        hashed = bcrypt.hashpw(salted_password, bcrypt.gensalt(rounds=12))
        
        return hashed.decode('utf-8')
    
    def verify_password(self, password, hashed_password):
        """
        Vérifie un mot de passe contre son hash
        
        Args:
            password (str): Mot de passe à vérifier
            hashed_password (str): Hash stocké
            
        Returns:
            bool: True si le mot de passe est correct
        """
        import bcrypt
        
        try:
            # Combiner le mot de passe avec notre sel personnalisé
            salted_password = password.encode('utf-8') + self.password_salt
            
            # Vérifier avec bcrypt
            return bcrypt.checkpw(salted_password, hashed_password.encode('utf-8'))
        except Exception as e:
            logging.error(f"Erreur lors de la vérification du mot de passe: {e}")
            return False
    
    def generate_file_checksum(self, file_path):
        """
        Génère un checksum SHA-256 pour un fichier
        
        Args:
            file_path (str): Chemin du fichier
            
        Returns:
            str: Checksum en hexadécimal
        """
        try:
            hash_sha256 = hashlib.sha256()
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            
            return hash_sha256.hexdigest()
            
        except Exception as e:
            logging.error(f"Erreur lors du calcul du checksum: {e}")
            raise
    
    def secure_delete_file(self, file_path, passes=3):
        """
        Suppression sécurisée d'un fichier (écrasement multiple)
        
        Args:
            file_path (str): Chemin du fichier à supprimer
            passes (int): Nombre de passes d'écrasement
        """
        try:
            if not os.path.exists(file_path):
                return
            
            file_size = os.path.getsize(file_path)
            
            with open(file_path, 'r+b') as file:
                for _ in range(passes):
                    file.seek(0)
                    # Écraser avec des données aléatoires
                    file.write(os.urandom(file_size))
                    file.flush()
                    os.fsync(file.fileno())
            
            # Supprimer le fichier
            os.remove(file_path)
            logging.info(f"Fichier supprimé de façon sécurisée: {file_path}")
            
        except Exception as e:
            logging.error(f"Erreur lors de la suppression sécurisée: {e}")
            raise


# Instance globale du gestionnaire de cryptage
encryption_manager = EncryptionManager()

def encrypt_sensitive_data(data):
    """
    Fonction utilitaire pour crypter des données sensibles
    
    Args:
        data (str): Données à crypter
        
    Returns:
        str: Données cryptées
    """
    return encryption_manager.encrypt_data(data)

def decrypt_sensitive_data(encrypted_data):
    """
    Fonction utilitaire pour décrypter des données
    
    Args:
        encrypted_data (str): Données cryptées
        
    Returns:
        str: Données décryptées
    """
    return encryption_manager.decrypt_data(encrypted_data)

def encrypt_uploaded_file(file_path):
    """
    Crypte un fichier uploadé
    
    Args:
        file_path (str): Chemin du fichier
        
    Returns:
        str: Chemin du fichier crypté
    """
    return encryption_manager.encrypt_file(file_path)

def decrypt_file_for_download(encrypted_file_path, temp_dir=None):
    """
    Décrypte temporairement un fichier pour téléchargement
    
    Args:
        encrypted_file_path (str): Chemin du fichier crypté
        temp_dir (str): Répertoire temporaire
        
    Returns:
        str: Chemin du fichier décrypté temporaire
    """
    if temp_dir is None:
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
        
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    # Nom temporaire unique
    temp_filename = f"temp_{secrets.token_hex(8)}_{os.path.basename(encrypted_file_path).replace('.encrypted', '')}"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    return encryption_manager.decrypt_file(encrypted_file_path, temp_path)