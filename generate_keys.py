#!/usr/bin/env python3
"""
Script to generate encryption keys for GEC system
Script pour générer les clés de chiffrement pour le système GEC
"""

import secrets
import base64

def generate_key():
    """Generate a secure 256-bit key encoded in base64"""
    return base64.b64encode(secrets.token_bytes(32)).decode()

def main():
    print("=" * 70)
    print("GEC System - Encryption Keys Generator")
    print("Système GEC - Générateur de Clés de Chiffrement")
    print("=" * 70)
    print()
    
    print("🔐 Generating encryption keys / Génération des clés de chiffrement...")
    print()
    
    master_key = generate_key()
    password_salt = generate_key()
    
    print("✅ Keys generated successfully! / Clés générées avec succès!")
    print()
    print("=" * 70)
    print("COPY THESE TO YOUR .env FILE / COPIEZ CECI DANS VOTRE FICHIER .env")
    print("=" * 70)
    print()
    print(f"GEC_MASTER_KEY={master_key}")
    print(f"GEC_PASSWORD_SALT={password_salt}")
    print()
    print("=" * 70)
    print("⚠️  IMPORTANT / IMPORTANT:")
    print("=" * 70)
    print()
    print("English:")
    print("1. Copy these keys to your .env file")
    print("2. KEEP THESE KEYS SECURE - Never share them!")
    print("3. Backup these keys in a secure location")
    print("4. Once set, DO NOT change them or data will be lost")
    print()
    print("Français:")
    print("1. Copiez ces clés dans votre fichier .env")
    print("2. GARDEZ CES CLÉS EN SÉCURITÉ - Ne les partagez jamais!")
    print("3. Sauvegardez ces clés dans un endroit sécurisé")
    print("4. Une fois définies, NE LES CHANGEZ PAS ou les données seront perdues")
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
