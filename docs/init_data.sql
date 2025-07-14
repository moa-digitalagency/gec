-- =============================================================================
-- DONNÉES D'INITIALISATION - GEC MINES
-- =============================================================================

-- Insertion des départements par défaut (si pas déjà existants)
INSERT INTO departement (nom, description, code) 
SELECT * FROM (VALUES
    ('Ressources Humaines', 'Gestion du personnel et des ressources humaines', 'RH'),
    ('Informatique', 'Services informatiques et technologies', 'IT'),
    ('Finance', 'Gestion financière et comptabilité', 'FIN'),
    ('Administration Générale', 'Administration et coordination générale', 'ADM'),
    ('Mines et Géologie', 'Affaires minières et géologiques', 'MIN')
) AS t(nom, description, code)
WHERE NOT EXISTS (SELECT 1 FROM departement WHERE departement.code = t.code);

-- Insertion des rôles par défaut (si pas déjà existants)
INSERT INTO role (nom, nom_affichage, description, couleur, icone, modifiable) 
SELECT * FROM (VALUES
    ('super_admin', 'Super Administrateur', 'Accès complet au système', 'bg-red-100 text-red-800', 'fas fa-crown', FALSE),
    ('admin', 'Administrateur', 'Administration départementale', 'bg-blue-100 text-blue-800', 'fas fa-user-shield', FALSE),
    ('user', 'Utilisateur', 'Utilisateur standard', 'bg-green-100 text-green-800', 'fas fa-user', FALSE)
) AS t(nom, nom_affichage, description, couleur, icone, modifiable)
WHERE NOT EXISTS (SELECT 1 FROM role WHERE role.nom = t.nom);

-- Insertion des permissions par défaut (si pas déjà existantes)
-- Super Admin - toutes les permissions
INSERT INTO role_permission (role_id, permission_nom) 
SELECT r.id, p.permission_nom FROM role r 
CROSS JOIN (VALUES
    ('manage_users'),
    ('manage_system'),
    ('manage_statuses'),
    ('manage_departments'),
    ('manage_roles'),
    ('view_logs'),
    ('read_all_mail'),
    ('backup_system')
) AS p(permission_nom)
WHERE r.nom = 'super_admin' 
AND NOT EXISTS (
    SELECT 1 FROM role_permission rp 
    WHERE rp.role_id = r.id AND rp.permission_nom = p.permission_nom
);

-- Admin - permissions départementales
INSERT INTO role_permission (role_id, permission_nom) 
SELECT r.id, p.permission_nom FROM role r 
CROSS JOIN (VALUES
    ('manage_statuses'),
    ('read_department_mail')
) AS p(permission_nom)
WHERE r.nom = 'admin' 
AND NOT EXISTS (
    SELECT 1 FROM role_permission rp 
    WHERE rp.role_id = r.id AND rp.permission_nom = p.permission_nom
);

-- User - permissions de base
INSERT INTO role_permission (role_id, permission_nom) 
SELECT r.id, p.permission_nom FROM role r 
CROSS JOIN (VALUES
    ('read_own_mail')
) AS p(permission_nom)
WHERE r.nom = 'user' 
AND NOT EXISTS (
    SELECT 1 FROM role_permission rp 
    WHERE rp.role_id = r.id AND rp.permission_nom = p.permission_nom
);

-- Insertion des statuts de courrier par défaut (si pas déjà existants)
INSERT INTO statut_courrier (nom, description, couleur, ordre) 
SELECT * FROM (VALUES
    ('RECU', 'Courrier reçu et enregistré', 'bg-blue-100 text-blue-800', 1),
    ('EN_COURS', 'Courrier en cours de traitement', 'bg-yellow-100 text-yellow-800', 2),
    ('TRAITE', 'Courrier traité', 'bg-green-100 text-green-800', 3),
    ('URGENT', 'Courrier urgent nécessitant une attention immédiate', 'bg-red-100 text-red-800', 4),
    ('ARCHIVE', 'Courrier archivé', 'bg-gray-100 text-gray-800', 5),
    ('EN_ATTENTE', 'En attente de validation', 'bg-orange-100 text-orange-800', 6)
) AS t(nom, description, couleur, ordre)
WHERE NOT EXISTS (SELECT 1 FROM statut_courrier WHERE statut_courrier.nom = t.nom);

-- Création de l'utilisateur administrateur par défaut (si pas déjà existant)
INSERT INTO "user" (username, email, nom_complet, password_hash, role, actif, departement_id) 
SELECT 'admin', 'admin@gec-mines.cd', 'Administrateur Système', 
       'PLACEHOLDER_PASSWORD_HASH', 
       'super_admin', TRUE, d.id
FROM departement d
WHERE d.code = 'RH'
AND NOT EXISTS (SELECT 1 FROM "user" WHERE username = 'admin');

-- Insertion des paramètres système par défaut (si pas déjà existants)
INSERT INTO parametres_systeme (
    nom_logiciel, 
    format_numero_accuse, 
    adresse_organisme, 
    telephone, 
    email_contact,
    titre_pdf,
    sous_titre_pdf,
    copyright_crypte
) 
SELECT 
    'GEC - Mines RDC',
    'GEC-{year}-{counter:05d}',
    'Ministère des Mines, Kinshasa, République Démocratique du Congo',
    '+243 XX XXX XXXX',
    'contact@gec-mines.cd',
    'Ministère des Mines',
    'Secrétariat Général',
    'wqkgwqjlgwqjlgwqjlgwqjlgwqjlgwqjlgwqjlgwqjl=' -- Copyright crypté
WHERE NOT EXISTS (SELECT 1 FROM parametres_systeme);