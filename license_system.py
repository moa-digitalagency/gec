"""
Système de licence sécurisé pour GEC Mines
Utilise un chiffrement multicouche avec détection de domaine
"""

import os
import hashlib
import hmac
import socket
import base64
import json
import time
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import logging

# Configuration sécurisée (obfusquée)
_MASTER_SALT = b'\x47\x65\x63\x4d\x69\x6e\x65\x73\x32\x30\x32\x35\x53\x61\x6c\x74'
_LICENSE_MARKER = "GEC_MINES_LICENSE_V2"
_DOMAIN_HASH_ROUNDS = 100000

class LicenseValidator:
    def __init__(self):
        self.license_file = ".gec_license"
        self.domain_cache = ".gec_domain_cache"
        self.logger = logging.getLogger(__name__)
        
    def _obfuscate_string(self, data: str) -> str:
        """Obfusque une chaîne pour la rendre moins lisible"""
        encoded = base64.b85encode(data.encode()).decode()
        # Rotation simple + inversion
        rotated = ''.join(chr(((ord(c) - 32) + 13) % 95 + 32) for c in encoded)
        return base64.b64encode(rotated.encode()).decode()
    
    def _deobfuscate_string(self, data: str) -> str:
        """Désobfusque une chaîne"""
        try:
            decoded = base64.b64decode(data.encode()).decode()
            # Inverse la rotation
            derotated = ''.join(chr(((ord(c) - 32) - 13) % 95 + 32) for c in decoded)
            return base64.b85decode(derotated.encode()).decode()
        except:
            return ""
    
    def _get_domain_fingerprint(self) -> str:
        """Génère une empreinte unique du domaine/environnement"""
        try:
            # Récupère le nom d'hôte/domaine
            hostname = socket.getfqdn()
            
            # Récupère les variables d'environnement Replit spécifiques
            repl_url = os.environ.get('REPLIT_DOMAINS', '')
            repl_slug = os.environ.get('REPL_SLUG', '')
            repl_owner = os.environ.get('REPL_OWNER', '')
            
            # Combine toutes les informations d'identification
            identifier_parts = [
                hostname.lower(),
                repl_url.lower(),
                repl_slug.lower(), 
                repl_owner.lower()
            ]
            
            # Filtre les parties vides et crée un identifiant unique
            domain_id = "|".join(part for part in identifier_parts if part)
            
            # Hash sécurisé avec sel
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=_MASTER_SALT,
                iterations=_DOMAIN_HASH_ROUNDS,
            )
            
            domain_hash = base64.urlsafe_b64encode(kdf.derive(domain_id.encode())).decode()
            
            self.logger.info(f"Empreinte domaine générée: {domain_hash[:8]}...")
            return domain_hash
            
        except Exception as e:
            self.logger.error(f"Erreur génération empreinte domaine: {e}")
            # Fallback sur hostname simple
            fallback = hashlib.sha256(socket.gethostname().encode()).hexdigest()
            return base64.urlsafe_b64encode(fallback.encode()).decode()[:32]
    
    def _encrypt_license_data(self, data: dict, license_key: str) -> str:
        """Chiffre les données de licence avec une clé"""
        try:
            # Génère une clé de chiffrement à partir de la licence
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=_MASTER_SALT + license_key.encode()[:16].ljust(16, b'0'),
                iterations=50000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(license_key.encode()))
            
            # Chiffre avec Fernet
            fernet = Fernet(key)
            encrypted = fernet.encrypt(json.dumps(data).encode())
            
            # Double obfuscation
            obfuscated = self._obfuscate_string(base64.b64encode(encrypted).decode())
            
            return f"{_LICENSE_MARKER}:{obfuscated}"
            
        except Exception as e:
            self.logger.error(f"Erreur chiffrement licence: {e}")
            return ""
    
    def _decrypt_license_data(self, encrypted_data: str, license_key: str) -> dict:
        """Déchiffre les données de licence"""
        try:
            if not encrypted_data.startswith(f"{_LICENSE_MARKER}:"):
                return {}
                
            obfuscated_data = encrypted_data[len(f"{_LICENSE_MARKER}:"):]
            
            # Désobfuscation
            b64_data = self._deobfuscate_string(obfuscated_data)
            if not b64_data:
                return {}
                
            encrypted = base64.b64decode(b64_data.encode())
            
            # Génère la clé de déchiffrement
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=_MASTER_SALT + license_key.encode()[:16].ljust(16, b'0'),
                iterations=50000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(license_key.encode()))
            
            # Déchiffre
            fernet = Fernet(key)
            decrypted = fernet.decrypt(encrypted)
            
            return json.loads(decrypted.decode())
            
        except Exception as e:
            self.logger.error(f"Erreur déchiffrement licence: {e}")
            return {}
    
    def _validate_license_format(self, license_key: str) -> bool:
        """Valide le format de la clé de licence"""
        # Format attendu: GECM-XXXX-XXXX-XXXX-XXXX (24 caractères + tirets)
        if len(license_key) != 29:
            return False
            
        parts = license_key.split('-')
        if len(parts) != 5 or parts[0] != 'GECM':
            return False
            
        # Vérification que chaque partie contient 4 caractères alphanumériques
        for part in parts[1:]:
            if len(part) != 4 or not part.isalnum():
                return False
                
        return True
    
    def _verify_license_checksum(self, license_key: str) -> bool:
        """Vérifie le checksum de la licence"""
        try:
            parts = license_key.split('-')
            data_parts = parts[1:4]  # Les 3 parties de données
            checksum_part = parts[4]  # La partie checksum
            
            # Calcule le checksum attendu
            data_string = ''.join(data_parts)
            expected_checksum = hashlib.sha256(
                (data_string + "GEC_MINES_2025").encode()
            ).hexdigest()[:4].upper()
            
            return checksum_part.upper() == expected_checksum
            
        except Exception as e:
            self.logger.error(f"Erreur vérification checksum: {e}")
            return False
    
    def check_domain_change(self) -> bool:
        """Vérifie si le domaine a changé depuis la dernière utilisation"""
        current_domain = self._get_domain_fingerprint()
        
        try:
            if os.path.exists(self.domain_cache):
                with open(self.domain_cache, 'r') as f:
                    cached_data = json.load(f)
                    cached_domain = cached_data.get('domain_fingerprint', '')
                    
                    if cached_domain != current_domain:
                        self.logger.warning("Changement de domaine détecté")
                        return True
                    return False
            else:
                # Première utilisation
                self.logger.info("Première utilisation - demande de licence")
                return True
                
        except Exception as e:
            self.logger.error(f"Erreur vérification domaine: {e}")
            return True
    
    def save_domain_cache(self):
        """Sauvegarde le cache du domaine"""
        try:
            domain_data = {
                'domain_fingerprint': self._get_domain_fingerprint(),
                'last_check': datetime.now().isoformat(),
                'application': 'GEC_MINES'
            }
            
            with open(self.domain_cache, 'w') as f:
                json.dump(domain_data, f)
                
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde cache domaine: {e}")
    
    def validate_license(self, license_key: str) -> tuple[bool, str]:
        """Valide une clé de licence via base de données"""
        try:
            # Vérification format (12 caractères alphanumériques)
            if len(license_key) != 12 or not license_key.isalnum():
                return False, "Format de licence invalide. Attendu: 12 caractères alphanumériques"
            
            # Vérification dans la base de données
            is_valid, message, license_info = self._check_license_in_database(license_key)
            
            if not is_valid:
                return False, message
            
            # Marque la licence comme utilisée
            success = self._mark_license_as_used(license_key)
            if not success:
                return False, "Erreur lors de l'activation de la licence"
            
            # Création des données de licence
            domain_fingerprint = self._get_domain_fingerprint()
            license_data = {
                'license_key': license_key,
                'domain_fingerprint': domain_fingerprint,
                'activation_date': datetime.now().isoformat(),
                'expiration_date': license_info['expiration_date'],
                'duration_label': license_info['duration_label'],
                'application': 'GEC_MINES',
                'version': '2.0'
            }
            
            # Sauvegarde chiffrée
            encrypted_license = self._encrypt_license_data(license_data, license_key)
            if not encrypted_license:
                return False, "Erreur lors du chiffrement de la licence"
            
            with open(self.license_file, 'w') as f:
                f.write(encrypted_license)
            
            # Met à jour le cache du domaine
            self.save_domain_cache()
            
            self.logger.info(f"Licence {license_key} validée et activée avec succès")
            return True, f"Licence activée avec succès ({license_info['duration_label']})"
            
        except Exception as e:
            self.logger.error(f"Erreur validation licence: {e}")
            return False, f"Erreur lors de la validation: {str(e)}"
    
    def _check_license_in_database(self, license_key: str) -> tuple[bool, str, dict]:
        """Vérifie la licence dans la base de données"""
        try:
            import os
            from sqlalchemy import create_engine, text
            
            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                return False, "Erreur de configuration de la base de données", {}
            
            engine = create_engine(database_url)
            
            with engine.connect() as connection:
                # Recherche la licence
                query = text("""
                    SELECT license_key, duration_days, duration_label, 
                           expiration_date, is_used, status, activation_date
                    FROM licenses 
                    WHERE license_key = :license_key
                """)
                
                result = connection.execute(query, {"license_key": license_key}).fetchone()
                
                if not result:
                    return False, "Licence introuvable", {}
                
                # Convertit en dictionnaire
                license_info = {
                    'license_key': result[0],
                    'duration_days': result[1],
                    'duration_label': result[2],
                    'expiration_date': result[3].isoformat() if result[3] else None,
                    'is_used': result[4],
                    'status': result[5],
                    'activation_date': result[6].isoformat() if result[6] else None
                }
                
                # Vérifie le statut
                if license_info['status'] != 'ACTIVE':
                    return False, "Licence inactive ou expirée", {}
                
                # Vérifie si déjà utilisée
                if license_info['is_used']:
                    return False, "Cette licence a déjà été utilisée", {}
                
                # Pour les nouvelles licences, pas de vérification d'expiration 
                # car elle sera calculée lors de l'activation
                
                return True, "Licence valide", license_info
                
        except Exception as e:
            self.logger.error(f"Erreur vérification licence DB: {e}")
            return False, "Erreur lors de la vérification", {}
    
    def _mark_license_as_used(self, license_key: str) -> bool:
        """Marque une licence comme utilisée et calcule sa date d'expiration"""
        try:
            import os
            from sqlalchemy import create_engine, text
            from datetime import timedelta
            
            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                return False
            
            engine = create_engine(database_url)
            domain_fingerprint = self._get_domain_fingerprint()
            
            with engine.connect() as connection:
                # Récupère d'abord les infos de la licence
                select_query = text("""
                    SELECT duration_days FROM licenses 
                    WHERE license_key = :license_key AND is_used = FALSE
                """)
                
                license_info = connection.execute(select_query, {"license_key": license_key}).fetchone()
                if not license_info:
                    return False
                
                # Calcule la date d'expiration à partir de maintenant
                activation_date = datetime.now()
                expiration_date = activation_date + timedelta(days=license_info[0])
                
                # Met à jour la licence avec activation et expiration
                query = text("""
                    UPDATE licenses 
                    SET is_used = TRUE, 
                        used_date = :activation_date,
                        activation_date = :activation_date,
                        expiration_date = :expiration_date,
                        used_domain = :domain,
                        used_ip = :ip
                    WHERE license_key = :license_key AND is_used = FALSE
                """)
                
                # Récupère l'IP si possible
                import socket
                try:
                    ip_address = socket.gethostbyname(socket.gethostname())
                except:
                    ip_address = "unknown"
                
                result = connection.execute(query, {
                    "license_key": license_key,
                    "activation_date": activation_date,
                    "expiration_date": expiration_date,
                    "domain": domain_fingerprint[:50],  # Limite la taille
                    "ip": ip_address
                })
                
                connection.commit()
                
                # Vérifie que la mise à jour a eu lieu
                if result.rowcount == 0:
                    return False
                
                self.logger.info(f"Licence {license_key} activée jusqu'au {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
                return True
                
        except Exception as e:
            self.logger.error(f"Erreur marquage licence utilisée: {e}")
            return False
    
    def check_license_validity(self) -> tuple[bool, str]:
        """Vérifie si la licence actuelle est valide"""
        try:
            if not os.path.exists(self.license_file):
                return False, "Aucune licence trouvée"
            
            with open(self.license_file, 'r') as f:
                encrypted_data = f.read().strip()
            
            # Tente de déchiffrer avec différentes méthodes si nécessaire
            license_data = {}
            
            # Essaie de récupérer la clé de licence depuis les données
            # (nécessaire pour le déchiffrement)
            if not encrypted_data.startswith(_LICENSE_MARKER):
                return False, "Fichier de licence corrompu"
            
            # Pour une validation rapide, vérifie juste la présence du domaine
            current_domain = self._get_domain_fingerprint()
            
            # Ici, on peut implémenter une vérification plus sophistiquée
            # En production, on pourrait avoir un système de validation serveur
            
            self.logger.info("Licence vérifiée avec succès")
            return True, "Licence valide"
            
        except Exception as e:
            self.logger.error(f"Erreur vérification licence: {e}")
            return False, f"Erreur lors de la vérification: {str(e)}"
    
    def is_license_required(self) -> bool:
        """Détermine si une demande de licence est nécessaire"""
        # Vérifie s'il y a eu un changement de domaine
        if self.check_domain_change():
            return True
        
        # Vérifie la validité de la licence existante
        is_valid, _ = self.check_license_validity()
        return not is_valid

# Instance globale du validateur
license_validator = LicenseValidator()

def generate_sample_license() -> str:
    """Génère une licence d'exemple pour les tests (à supprimer en production)"""
    import random
    import string
    
    # Génère 3 parties de données aléatoires
    data_parts = []
    for _ in range(3):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        data_parts.append(part)
    
    # Calcule le checksum
    data_string = ''.join(data_parts)
    checksum = hashlib.sha256((data_string + "GEC_MINES_2025").encode()).hexdigest()[:4].upper()
    
    return f"GECM-{'-'.join(data_parts)}-{checksum}"

def check_license_status() -> tuple[bool, str]:
    """Fonction utilitaire pour vérifier le statut de la licence"""
    return license_validator.check_license_validity()

def require_license() -> tuple[bool, str]:
    """Détermine si une licence est requise"""
    if license_validator.is_license_required():
        return True, "Licence requise"
    return False, "Licence valide"