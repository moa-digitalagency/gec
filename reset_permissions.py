#!/usr/bin/env python3
"""Script pour réinitialiser les permissions dans la base de données"""

from app import app, db
from models import Role, RolePermission, User

with app.app_context():
    print("Réinitialisation des permissions...")
    
    # Supprimer toutes les permissions existantes
    RolePermission.query.delete()
    db.session.commit()
    print("✓ Anciennes permissions supprimées")
    
    # Permissions par rôle
    permissions_defaut = {
        'super_admin': [
            'manage_users', 'manage_roles', 'manage_system_settings', 
            'view_all_logs', 'manage_statuses', 'manage_departments',
            'register_mail', 'view_mail', 'search_mail', 'export_data', 
            'delete_mail', 'view_trash', 'restore_mail', 'view_all', 'edit_all', 'read_all_mail'
        ],
        'admin': [
            'manage_statuses', 'register_mail', 'view_mail', 
            'search_mail', 'export_data', 'manage_system_settings',
            'view_department', 'edit_department', 'read_department_mail', 
            'view_trash'  # Ajout de la permission pour les admins aussi
        ],
        'user': [
            'register_mail', 'view_mail', 'search_mail', 'export_data',
            'view_own', 'edit_own', 'read_own_mail'
        ]
    }
    
    for role_nom, perms in permissions_defaut.items():
        role = Role.query.filter_by(nom=role_nom).first()
        if role:
            print(f"\n✓ Ajout des permissions pour le rôle {role_nom}:")
            for perm_nom in perms:
                permission = RolePermission(role_id=role.id, permission_nom=perm_nom)
                db.session.add(permission)
                print(f"  - {perm_nom}")
    
    db.session.commit()
    print("\n✓ Permissions réinitialisées avec succès!")
    
    # Vérifier les permissions du super admin
    super_admin = User.query.filter_by(role='super_admin').first()
    if super_admin:
        print(f"\n✓ Vérification pour {super_admin.username}:")
        print(f"  - delete_mail: {super_admin.has_permission('delete_mail')}")
        print(f"  - view_trash: {super_admin.has_permission('view_trash')}")
        print(f"  - restore_mail: {super_admin.has_permission('restore_mail')}")