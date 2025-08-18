import sys
sys.path.insert(0, '.')
import os
os.environ['DATABASE_URL'] = 'sqlite:///instance/database.db'

from datetime import datetime
from models import Courrier, User, ParametresSysteme
from app import app, db
from utils import export_courrier_pdf, format_date

# Créer un contexte Flask
with app.app_context():
    # Configurer la langue en français
    from flask import session
    
    # Créer un courrier sortant de test
    test_sortant = Courrier(
        numero_accuse_reception='TEST-SORTANT-001',
        type_courrier='SORTANT',
        destinataire='Ministère des Finances',
        objet='Test pour vérifier Date d\'Émission',
        date_redaction=datetime(2025, 1, 18),
        date_enregistrement=datetime.now(),
        statut='EN_COURS',
        utilisateur_id=1,
        fichier_nom='test.pdf'
    )
    
    # Créer un courrier entrant de test
    test_entrant = Courrier(
        numero_accuse_reception='TEST-ENTRANT-001',
        type_courrier='ENTRANT',
        expediteur='Banque Centrale',
        objet='Test pour vérifier Date de Rédaction',
        date_redaction=datetime(2025, 1, 15),
        date_enregistrement=datetime.now(),
        statut='EN_COURS',
        utilisateur_id=1,
        fichier_nom='test2.pdf'
    )
    
    # Récupérer l'utilisateur
    test_sortant.utilisateur_enregistrement = User.query.get(1)
    test_entrant.utilisateur_enregistrement = User.query.get(1)
    
    # Test format français
    os.environ['FLASK_SESSION_LANGUAGE'] = 'fr'
    print("=== Test Format Français ===")
    
    # Exporter le courrier sortant
    try:
        pdf_path_sortant = export_courrier_pdf(test_sortant)
        print(f"PDF Sortant généré: {pdf_path_sortant}")
        
        # Lire le contenu du PDF avec strings pour vérifier le label
        import subprocess
        content = subprocess.check_output(['strings', pdf_path_sortant], text=True)
        
        if "Date d" in content:
            lines = [line for line in content.split('\n') if 'Date' in line]
            for line in lines[:5]:
                print(f"  Trouvé: {line}")
        
    except Exception as e:
        print(f"Erreur export sortant: {e}")
    
    # Exporter le courrier entrant
    try:
        pdf_path_entrant = export_courrier_pdf(test_entrant)
        print(f"PDF Entrant généré: {pdf_path_entrant}")
        
        # Lire le contenu
        content = subprocess.check_output(['strings', pdf_path_entrant], text=True)
        
        if "Date de" in content:
            lines = [line for line in content.split('\n') if 'Date' in line]
            for line in lines[:5]:
                print(f"  Trouvé: {line}")
                
    except Exception as e:
        print(f"Erreur export entrant: {e}")
    
    print("\n=== Test formatage des dates ===")
    test_date = datetime(2025, 1, 18, 14, 30)
    
    # Mock session pour test
    class MockRequest:
        def __init__(self):
            self.values = {}
            
    from flask import _request_ctx_stack
    from werkzeug.test import EnvironBuilder
    
    # Test avec langue française
    with app.test_request_context():
        session['language'] = 'fr'
        print(f"FR sans heure: {format_date(test_date, False)}")
        print(f"FR avec heure: {format_date(test_date, True)}")
        
        session['language'] = 'en'
        print(f"EN sans heure: {format_date(test_date, False)}")
        print(f"EN avec heure: {format_date(test_date, True)}")
