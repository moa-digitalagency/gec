"""
Script de nettoyage de la base de données GEC
Supprime toutes les données sauf l'utilisateur super admin et les données de configuration système
"""
import os
import sys
from app import app, db
from models import (
    User, Courrier, CourrierModification, LogActivite, 
    Notification, CourrierComment, CourrierForward,
    IPBlock, Departement
)

def cleanup_database():
    """Nettoie la base de données en gardant uniquement le super admin"""
    
    print("=" * 60)
    print("NETTOYAGE DE LA BASE DE DONNÉES GEC")
    print("=" * 60)
    print("\n⚠️  ATTENTION: Cette opération va supprimer toutes les données")
    print("   sauf l'utilisateur super admin et les configurations système.\n")
    
    # Demander confirmation
    confirmation = input("Tapez 'OUI' en majuscules pour confirmer: ")
    
    if confirmation != "OUI":
        print("\n❌ Opération annulée.")
        return
    
    print("\n🔄 Démarrage du nettoyage...\n")
    
    with app.app_context():
        try:
            # 1. Supprimer les transferts de courrier
            print("📧 Suppression des transferts de courrier...")
            count_forwards = CourrierForward.query.delete()
            print(f"   ✓ {count_forwards} transfert(s) supprimé(s)")
            
            # 2. Supprimer les commentaires de courrier
            print("💬 Suppression des commentaires...")
            count_comments = CourrierComment.query.delete()
            print(f"   ✓ {count_comments} commentaire(s) supprimé(s)")
            
            # 3. Supprimer les notifications
            print("🔔 Suppression des notifications...")
            count_notifications = Notification.query.delete()
            print(f"   ✓ {count_notifications} notification(s) supprimée(s)")
            
            # 4. Supprimer les modifications de courrier
            print("📝 Suppression de l'historique des modifications...")
            count_modifications = CourrierModification.query.delete()
            print(f"   ✓ {count_modifications} modification(s) supprimée(s)")
            
            # 5. Supprimer tous les courriers
            print("📄 Suppression des courriers...")
            count_courriers = Courrier.query.delete()
            print(f"   ✓ {count_courriers} courrier(s) supprimé(s)")
            
            # 6. Supprimer les logs d'activité
            print("📊 Suppression des logs d'activité...")
            count_logs = LogActivite.query.delete()
            print(f"   ✓ {count_logs} log(s) supprimé(s)")
            
            # 7. Supprimer les IP bloquées
            print("🚫 Suppression des IP bloquées...")
            count_ip_blocks = IPBlock.query.delete()
            print(f"   ✓ {count_ip_blocks} IP(s) supprimée(s)")
            
            # 8. Retirer les chefs de département
            print("👥 Nettoyage des départements...")
            departements = Departement.query.all()
            for dept in departements:
                dept.chef_departement_id = None
            print(f"   ✓ {len(departements)} département(s) nettoyé(s)")
            
            # 9. Supprimer tous les utilisateurs SAUF le super admin
            print("👤 Suppression des utilisateurs...")
            super_admin = User.query.filter_by(username='sa.gec001').first()
            
            if not super_admin:
                print("\n   ⚠️  ATTENTION: Super admin 'sa.gec001' non trouvé!")
                print("   Tous les utilisateurs seront supprimés.\n")
                count_users = User.query.delete()
            else:
                # Supprimer tous les utilisateurs sauf le super admin
                users_to_delete = User.query.filter(User.id != super_admin.id).all()
                count_users = 0
                for user in users_to_delete:
                    db.session.delete(user)
                    count_users += 1
                
                print(f"   ✓ {count_users} utilisateur(s) supprimé(s)")
                print(f"   ✓ Super admin '{super_admin.username}' conservé")
            
            # Commit toutes les modifications
            print("\n💾 Enregistrement des modifications...")
            db.session.commit()
            
            print("\n" + "=" * 60)
            print("✅ NETTOYAGE TERMINÉ AVEC SUCCÈS!")
            print("=" * 60)
            print(f"\nRésumé:")
            print(f"  • Transferts supprimés: {count_forwards}")
            print(f"  • Commentaires supprimés: {count_comments}")
            print(f"  • Notifications supprimées: {count_notifications}")
            print(f"  • Modifications supprimées: {count_modifications}")
            print(f"  • Courriers supprimés: {count_courriers}")
            print(f"  • Logs supprimés: {count_logs}")
            print(f"  • IP bloquées supprimées: {count_ip_blocks}")
            print(f"  • Utilisateurs supprimés: {count_users}")
            
            if super_admin:
                print(f"\n✓ Utilisateur conservé:")
                print(f"  • Username: {super_admin.username}")
                print(f"  • Email: {super_admin.email}")
                print(f"  • Rôle: {super_admin.role}")
            
            print("\n📌 Les données de configuration système ont été conservées:")
            print("  • Départements")
            print("  • Rôles et permissions")
            print("  • Statuts de courrier")
            print("  • Types de courrier sortant")
            print("  • Paramètres système")
            print("  • Modèles d'email")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERREUR lors du nettoyage: {e}")
            print("   La base de données a été restaurée à son état précédent.")
            sys.exit(1)

def show_stats():
    """Affiche les statistiques de la base de données"""
    print("\n" + "=" * 60)
    print("STATISTIQUES DE LA BASE DE DONNÉES")
    print("=" * 60 + "\n")
    
    with app.app_context():
        print(f"Utilisateurs: {User.query.count()}")
        print(f"Courriers: {Courrier.query.count()}")
        print(f"Commentaires: {CourrierComment.query.count()}")
        print(f"Notifications: {Notification.query.count()}")
        print(f"Transferts: {CourrierForward.query.count()}")
        print(f"Logs d'activité: {LogActivite.query.count()}")
        print(f"Départements: {Departement.query.count()}")
        print(f"IP bloquées: {IPBlock.query.count()}")

if __name__ == "__main__":
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "SCRIPT DE NETTOYAGE BASE DE DONNÉES GEC" + " " * 8 + "║")
    print("╚" + "═" * 58 + "╝" + "\n")
    
    # Afficher les statistiques avant nettoyage
    print("📊 Statistiques AVANT nettoyage:")
    show_stats()
    
    # Effectuer le nettoyage
    cleanup_database()
    
    # Afficher les statistiques après nettoyage
    print("\n📊 Statistiques APRÈS nettoyage:")
    show_stats()
    
    print("\n✨ Script terminé.\n")
