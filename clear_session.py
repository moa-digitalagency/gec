#!/usr/bin/env python3
"""Script pour forcer le rechargement des permissions dans la session"""

from app import app, db
from models import User

with app.app_context():
    print("Forçage du rechargement des permissions...")
    
    # Récupérer l'utilisateur admin
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user:
        # Vérifier ses permissions actuelles
        print(f"\nUtilisateur: {admin_user.username} (rôle: {admin_user.role})")
        print("Permissions actuelles:")
        print(f"  - delete_mail: {admin_user.has_permission('delete_mail')}")
        print(f"  - view_trash: {admin_user.has_permission('view_trash')}")
        print(f"  - restore_mail: {admin_user.has_permission('restore_mail')}")
        
        # Forcer la mise à jour du timestamp pour invalider le cache
        admin_user.date_modification = db.func.now()
        db.session.commit()
        print("\n✓ Cache des permissions réinitialisé!")
    else:
        print("Utilisateur admin non trouvé")