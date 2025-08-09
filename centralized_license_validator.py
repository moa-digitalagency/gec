#!/usr/bin/env python3
"""
Système de validation centralisé des licences GEC Mines
Valide les licences contre la base de données PostgreSQL centralisée
"""

import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

def validate_license_centralized(license_key):
    """
    Valide une licence contre la base de données centralisée
    Returns: (is_valid, message, license_info)
    """
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return False, "Base de données non configurée", {}
        
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Recherche la licence dans la base
            query = text("""
                SELECT license_key, duration_days, duration_label, status, is_used,
                       created_date, used_date, expiration_date, used_domain
                FROM licenses 
                WHERE license_key = :license_key
            """)
            
            result = connection.execute(query, {"license_key": license_key.upper()}).fetchone()
            
            if not result:
                return False, "Licence introuvable dans la base de données", {}
            
            # Convertit le résultat en dictionnaire
            if hasattr(result, '_asdict'):
                license_data = result._asdict()
            elif hasattr(result, '_mapping'):
                license_data = dict(result._mapping)
            else:
                # Fallback pour les anciennes versions de SQLAlchemy
                license_data = {
                    'license_key': result[0],
                    'duration_days': result[1],
                    'duration_label': result[2],
                    'status': result[3],
                    'is_used': result[4],
                    'created_date': result[5],
                    'used_date': result[6],
                    'expiration_date': result[7],
                    'used_domain': result[8]
                }
            
            if license_data['is_used']:
                used_date = license_data['used_date']
                date_str = used_date.strftime('%d/%m/%Y') if used_date else 'date inconnue'
                return False, f"Licence déjà utilisée le {date_str}", {}
            
            if license_data['status'] != 'ACTIVE':
                return False, "Licence inactive", {}
            
            # Licence valide
            license_info = {
                'license_key': license_data['license_key'],
                'duration_days': license_data['duration_days'],
                'duration_label': license_data['duration_label'],
                'status': license_data['status'],
                'is_used': license_data['is_used'],
                'created_date': license_data['created_date']
            }
            
            return True, f"Licence valide ({license_data['duration_label']})", license_info
            
    except Exception as e:
        logger.error(f"Erreur validation base de données: {e}")
        return False, f"Erreur de validation: {str(e)}", {}

def activate_license_centralized(license_key, domain_fingerprint=None):
    """
    Active une licence dans la base de données centralisée
    Returns: (is_activated, message, license_info)
    """
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return False, "Base de données non configurée", {}
        
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Valide d'abord la licence
            is_valid, message, license_info = validate_license_centralized(license_key)
            
            if not is_valid:
                return False, message, {}
            
            # Active la licence
            now = datetime.utcnow()
            expiration_date = now + timedelta(days=license_info['duration_days'])
            
            update_query = text("""
                UPDATE licenses 
                SET is_used = true,
                    used_date = :used_date,
                    activation_date = :activation_date,
                    expiration_date = :expiration_date,
                    used_domain = :used_domain
                WHERE license_key = :license_key
            """)
            
            connection.execute(update_query, {
                'license_key': license_key.upper(),
                'used_date': now,
                'activation_date': now,
                'expiration_date': expiration_date,
                'used_domain': domain_fingerprint or 'unknown'
            })
            
            connection.commit()
            
            # Met à jour les informations de la licence
            license_info.update({
                'is_used': True,
                'used_date': now,
                'activation_date': now,
                'expiration_date': expiration_date,
                'used_domain': domain_fingerprint
            })
            
            return True, f"Licence activée avec succès ({license_info['duration_label']})", license_info
            
    except Exception as e:
        logger.error(f"Erreur activation base de données: {e}")
        return False, f"Erreur d'activation: {str(e)}", {}

def get_current_domain():
    """Génère l'empreinte du domaine actuel"""
    import hashlib
    import os
    
    try:
        # Utilise les variables d'environnement pour générer l'empreinte
        domain_data = f"{os.environ.get('REPL_ID', '')}{os.environ.get('REPL_OWNER', '')}{os.getcwd()}"
        return hashlib.sha256(domain_data.encode()).hexdigest()[:32]
    except:
        return "local_domain_fingerprint"

def check_license_status_centralized():
    """
    Vérifie le statut des licences actives pour le domaine actuel
    Returns: (has_valid_license, message, license_info)
    """
    try:
        
        domain_fingerprint = get_current_domain()
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            return False, "Base de données non configurée", {}
        
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Recherche les licences actives pour ce domaine
            query = text("""
                SELECT license_key, duration_days, duration_label, 
                       activation_date, expiration_date, used_domain
                FROM licenses 
                WHERE used_domain = :domain AND is_used = true 
                  AND expiration_date > :now
                ORDER BY expiration_date DESC
                LIMIT 1
            """)
            
            result = connection.execute(query, {
                'domain': domain_fingerprint,
                'now': datetime.utcnow()
            }).fetchone()
            
            if not result:
                return False, "Aucune licence active trouvée", {}
            
            # Convertit le résultat
            if hasattr(result, '_asdict'):
                license_data = result._asdict()
            elif hasattr(result, '_mapping'):
                license_data = dict(result._mapping)
            else:
                license_data = {
                    'license_key': result[0],
                    'duration_days': result[1],
                    'duration_label': result[2],
                    'activation_date': result[3],
                    'expiration_date': result[4],
                    'used_domain': result[5]
                }
            
            # Calcule les jours restants
            days_remaining = (license_data['expiration_date'] - datetime.utcnow()).days
            
            license_info = {
                'license_key': license_data['license_key'],
                'duration_days': license_data['duration_days'],
                'duration_label': license_data['duration_label'],
                'activation_date': license_data['activation_date'],
                'expiration': license_data['expiration_date'].isoformat(),
                'days_remaining': max(0, days_remaining),
                'total_licenses': 1,  # Pour compatibilité
                'used_domain': license_data['used_domain']
            }
            
            return True, f"Licence active ({license_data['duration_label']})", license_info
            
    except Exception as e:
        logger.error(f"Erreur vérification statut: {e}")
        return False, f"Erreur de vérification: {str(e)}", {}

def get_license_history_centralized():
    """
    Récupère l'historique des licences pour le domaine actuel
    Returns: list of license records
    """
    try:
        
        domain_fingerprint = get_current_domain()
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            return []
        
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            query = text("""
                SELECT license_key, duration_days, duration_label,
                       activation_date, expiration_date, used_date
                FROM licenses 
                WHERE used_domain = :domain AND is_used = true
                ORDER BY activation_date DESC
            """)
            
            results = connection.execute(query, {'domain': domain_fingerprint}).fetchall()
            
            licenses = []
            for result in results:
                if hasattr(result, '_asdict'):
                    license_data = result._asdict()
                elif hasattr(result, '_mapping'):
                    license_data = dict(result._mapping)
                else:
                    license_data = {
                        'license_key': result[0],
                        'duration_days': result[1],
                        'duration_label': result[2],
                        'activation_date': result[3],
                        'expiration_date': result[4],
                        'used_date': result[5]
                    }
                
                licenses.append({
                    'license_key': license_data['license_key'],
                    'duration_days': license_data['duration_days'],
                    'duration_label': license_data['duration_label'],
                    'activation_date': license_data['activation_date'],
                    'expiration': license_data['expiration_date'].isoformat() if license_data['expiration_date'] else None,
                    'used_date': license_data['used_date']
                })
            
            return licenses
            
    except Exception as e:
        logger.error(f"Erreur historique licences: {e}")
        return []

def get_available_demo_licenses():
    """
    Récupère quelques licences disponibles pour démonstration (mode dev uniquement)
    """
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return {}
        
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            demo_licenses = {}
            
            for duration in ['1 jour', '5 jours']:
                query = text("""
                    SELECT license_key FROM licenses 
                    WHERE duration_label = :duration AND is_used = false 
                    LIMIT 5
                """)
                result = connection.execute(query, {"duration": duration}).fetchall()
                key = duration.replace(' ', '_')
                demo_licenses[key] = [row[0] for row in result]
            
            return demo_licenses
            
    except Exception:
        return {}

if __name__ == "__main__":
    # Test du système
    print("🔑 Test du système de validation centralisé")
    
    # Test de validation
    test_key = "RAAFAXKE9VRY"  # Une des licences générées
    is_valid, message, info = validate_license_centralized(test_key)
    
    print(f"Validation {test_key}: {is_valid} - {message}")
    if info:
        print(f"Info: {info}")