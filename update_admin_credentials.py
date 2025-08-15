#!/usr/bin/env python3
"""Script pour mettre à jour les identifiants du super admin"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    print("Mise à jour des identifiants du super admin...")
    
    # Trouver l'utilisateur admin actuel
    admin_user = User.query.filter_by(username='admin').first()
    
    if admin_user:
        # Mettre à jour le username et le mot de passe
        admin_user.username = 'sa.gec001'
        admin_user.password_hash = generate_password_hash('Xzf)psYv%')
        
        # S'assurer que c'est bien un super admin
        admin_user.role = 'super_admin'
        
        # Sauvegarder les modifications
        db.session.commit()
        
        print("✓ Identifiants mis à jour avec succès!")
        print(f"  - Nouveau username: sa.gec001")
        print(f"  - Nouveau mot de passe: Xzf)psYv%")
        print(f"  - Rôle: {admin_user.role}")
        print(f"  - Nom complet: {admin_user.nom_complet}")
        print(f"  - Email: {admin_user.email}")
    else:
        print("✗ Utilisateur admin non trouvé. Création d'un nouveau super admin...")
        
        # Créer un nouveau super admin
        new_admin = User(
            username='sa.gec001',
            email='admin@gec-mines.cd',
            nom_complet='Super Admin GEC',
            role='super_admin',
            password_hash=generate_password_hash('Xzf)psYv%'),
            actif=True
        )
        
        db.session.add(new_admin)
        db.session.commit()
        
        print("✓ Nouveau super admin créé avec succès!")
        print(f"  - Username: sa.gec001")
        print(f"  - Mot de passe: Xzf)psYv%")
        print(f"  - Rôle: super_admin")