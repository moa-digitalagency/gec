#!/usr/bin/env python3
"""
Système de licence sécurisé et crypté pour GEC Mines
Implémentation avec obfuscation et chiffrement avancé pour empêcher le cracking
"""

import os
import base64
import hashlib
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import json
import logging
import zlib

# Configuration de logging
logging.basicConfig(level=logging.WARNING)  # Réduire le niveau de logging

class SecureLicenseManager:
    def __init__(self):
        # Données obfusquées
        self._k1 = b'R2VjTWluZXNfU2VjdXJlX0xpY2Vuc2VfU3lzdGVt'  # Base64: GecMines_Secure_License_System
        self._k2 = os.environ.get('DATABASE_URL', '').encode()
        
        # Génération de clé de chiffrement basée sur l'environnement
        self._encryption_key = self._generate_env_key()
        self._fernet = Fernet(self._encryption_key) if self._encryption_key else None
        
        # Fichiers cachés et cryptés
        self._license_file = '.gec_lic_sys'
        self._domain_cache = '.gec_dom_cache' 
        self._cumulative_file = '.gec_cumul_lic'
        
        # Logger silencieux
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.ERROR)
    
    def _generate_env_key(self) -> bytes:
        """Génère une clé de chiffrement basée sur l'environnement"""
        try:
            # Utilise des données d'environnement pour générer la clé
            env_data = f"{os.environ.get('DATABASE_URL', '')}{os.environ.get('REPL_ID', '')}{os.getcwd()}"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._k1,
                iterations=100000,
            )
            return base64.urlsafe_b64encode(kdf.derive(env_data.encode()))
        except Exception:
            return None
    
    def _encrypt_data(self, data: str) -> str:
        """Chiffre et compresse les données"""
        if not self._fernet:
            return data
        
        try:
            # Compresse puis chiffre
            compressed = zlib.compress(data.encode())
            encrypted = self._fernet.encrypt(compressed)
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception:
            return data
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Déchiffre et décompresse les données"""
        if not self._fernet:
            return encrypted_data
        
        try:
            # Décode, déchiffre puis décompresse
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(encrypted_bytes)
            decompressed = zlib.decompress(decrypted)
            return decompressed.decode()
        except Exception:
            return encrypted_data
    
    def get_domain_fingerprint(self) -> str:
        """Génère l'empreinte du domaine actuel"""
        try:
            # Données pour l'empreinte
            repl_id = os.environ.get('REPL_ID', 'unknown')
            repl_slug = os.environ.get('REPL_SLUG', 'unknown')
            repl_owner = os.environ.get('REPL_OWNER', 'unknown')
            working_dir = os.getcwd()
            
            # Génère l'empreinte
            fingerprint_data = f"{repl_id}:{repl_slug}:{repl_owner}:{working_dir}"
            fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
            
            return fingerprint[:16]  # 16 premiers caractères
            
        except Exception:
            return "default_domain"
    
    def check_cumulative_licenses(self) -> dict:
        """Vérifie les licences cumulées pour le domaine actuel"""
        try:
            if not os.path.exists(self._cumulative_file):
                return {"active": False, "expiration": None, "licenses": []}
            
            with open(self._cumulative_file, 'r') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._decrypt_data(encrypted_data)
            cumulative_data = json.loads(decrypted_data)
            
            domain_fingerprint = self.get_domain_fingerprint()
            
            if domain_fingerprint not in cumulative_data:
                return {"active": False, "expiration": None, "licenses": []}
            
            domain_licenses = cumulative_data[domain_fingerprint]
            
            # Vérifie si il y a une licence active
            current_time = datetime.now()
            active_until = None
            
            for license_info in domain_licenses.get("licenses", []):
                exp_date = datetime.fromisoformat(license_info["expiration"])
                if exp_date > current_time:
                    if not active_until or exp_date > active_until:
                        active_until = exp_date
            
            return {
                "active": active_until is not None,
                "expiration": active_until.isoformat() if active_until else None,
                "licenses": domain_licenses.get("licenses", [])
            }
            
        except Exception as e:
            return {"active": False, "expiration": None, "licenses": []}
    
    def add_cumulative_license(self, license_key: str, duration_days: int, duration_label: str) -> bool:
        """Ajoute une licence au système cumulatif"""
        try:
            # Charge les données existantes
            cumulative_data = {}
            if os.path.exists(self._cumulative_file):
                with open(self._cumulative_file, 'r') as f:
                    encrypted_data = f.read()
                decrypted_data = self._decrypt_data(encrypted_data)
                cumulative_data = json.loads(decrypted_data)
            
            domain_fingerprint = self.get_domain_fingerprint()
            
            if domain_fingerprint not in cumulative_data:
                cumulative_data[domain_fingerprint] = {"licenses": []}
            
            # Calcule la date d'activation et d'expiration
            current_licenses = self.check_cumulative_licenses()
            
            if current_licenses["active"] and current_licenses["expiration"]:
                # Prolonge à partir de la dernière expiration
                base_date = datetime.fromisoformat(current_licenses["expiration"])
            else:
                # Commence maintenant
                base_date = datetime.now()
            
            activation_date = datetime.now()
            expiration_date = base_date + timedelta(days=duration_days)
            
            # Ajoute la nouvelle licence
            new_license = {
                "license_key": license_key,
                "duration_days": duration_days,
                "duration_label": duration_label,
                "activation_date": activation_date.isoformat(),
                "expiration": expiration_date.isoformat()
            }
            
            cumulative_data[domain_fingerprint]["licenses"].append(new_license)
            
            # Sauvegarde chiffrée
            json_data = json.dumps(cumulative_data, indent=2)
            encrypted_data = self._encrypt_data(json_data)
            
            with open(self._cumulative_file, 'w') as f:
                f.write(encrypted_data)
            
            return True
            
        except Exception as e:
            return False
    
    def validate_license_from_db(self, license_key: str) -> tuple[bool, str]:
        """Valide une licence via la base de données et l'ajoute au système cumulatif"""
        try:
            from sqlalchemy import create_engine, text
            
            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                return False, "Erreur de configuration"
            
            engine = create_engine(database_url)
            
            with engine.connect() as connection:
                # Vérifie la licence
                select_query = text("""
                    SELECT license_key, duration_days, duration_label, is_used, status 
                    FROM licenses 
                    WHERE license_key = :license_key
                """)
                
                result = connection.execute(select_query, {"license_key": license_key}).fetchone()
                
                if not result:
                    return False, "Licence introuvable"
                
                if result[3]:  # is_used
                    return False, "Licence déjà utilisée"
                
                if result[4] != 'ACTIVE':  # status
                    return False, "Licence inactive"
                
                # Marque comme utilisée dans la DB
                domain_fingerprint = self.get_domain_fingerprint()
                activation_date = datetime.now()
                expiration_date = activation_date + timedelta(days=result[1])
                
                update_query = text("""
                    UPDATE licenses 
                    SET is_used = TRUE, 
                        used_date = :activation_date,
                        activation_date = :activation_date,
                        expiration_date = :expiration_date,
                        used_domain = :domain
                    WHERE license_key = :license_key
                """)
                
                connection.execute(update_query, {
                    "license_key": license_key,
                    "activation_date": activation_date,
                    "expiration_date": expiration_date,
                    "domain": domain_fingerprint
                })
                
                connection.commit()
                
                # Ajoute au système cumulatif
                success = self.add_cumulative_license(license_key, result[1], result[2])
                
                if success:
                    return True, f"Licence activée avec succès ({result[2]})"
                else:
                    return False, "Erreur lors de l'activation"
                
        except Exception as e:
            return False, "Erreur lors de la validation"
    
    def is_license_valid(self) -> tuple[bool, str, dict]:
        """Vérifie si le domaine actuel a une licence valide"""
        try:
            current_licenses = self.check_cumulative_licenses()
            
            if current_licenses["active"]:
                expiration = datetime.fromisoformat(current_licenses["expiration"])
                days_remaining = (expiration - datetime.now()).days
                
                return True, f"Licence valide jusqu'au {expiration.strftime('%d/%m/%Y')}", {
                    "expiration": current_licenses["expiration"],
                    "days_remaining": days_remaining,
                    "total_licenses": len(current_licenses["licenses"])
                }
            else:
                return False, "Aucune licence active", {}
                
        except Exception as e:
            return False, "Erreur de vérification", {}

# Instance globale sécurisée
secure_license_manager = SecureLicenseManager()

def check_license_status() -> tuple[bool, str, dict]:
    """Point d'entrée principal pour vérifier le statut de licence"""
    return secure_license_manager.is_license_valid()

def activate_license(license_key: str) -> tuple[bool, str]:
    """Point d'entrée principal pour activer une licence"""
    return secure_license_manager.validate_license_from_db(license_key)

def get_current_domain() -> str:
    """Retourne l'empreinte du domaine actuel"""
    return secure_license_manager.get_domain_fingerprint()