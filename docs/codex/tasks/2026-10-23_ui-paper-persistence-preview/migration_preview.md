# Prévisualisation — SQLite v2 Paper

## Justification

Le journal v1 ne contient pas toutes les données nécessaires pour reconstruire avec certitude une
position Paper ouverte, ses niveaux, ses hypothèses de remplissage et son contexte de risque. Un
checkpoint complet et contrôlé évite une reconstitution partielle ou silencieusement erronée.

## Changement de schéma proposé

`CURRENT_SCHEMA_VERSION` passe de `1` à `2`.

```sql
CREATE TABLE paper_session_snapshots (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL,
    saved_at_utc TEXT NOT NULL,
    format_version INTEGER NOT NULL CHECK (format_version = 1),
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64)
);

CREATE TRIGGER paper_session_snapshots_no_update
BEFORE UPDATE ON paper_session_snapshots
BEGIN
    SELECT RAISE(ABORT, 'paper_session_snapshots is append-only');
END;

CREATE TRIGGER paper_session_snapshots_no_delete
BEFORE DELETE ON paper_session_snapshots
BEGIN
    SELECT RAISE(ABORT, 'paper_session_snapshots is append-only');
END;
```

La migration ajoute ensuite la version `2` à `schema_migrations` et positionne
`PRAGMA user_version = 2` dans la même transaction.

## Contenu du checkpoint

- Identité locale de session Paper, version de format et date UTC.
- Soumissions Paper nécessaires à l'audit et à la reprise.
- Positions ouvertes/fermées, niveaux stop/objectif/KO et P&L.
- Dernières cotations Paper et hypothèses de frais/slippage.
- Journal local append-only.
- `Decimal` encodés en texte et dates en UTC `Z`.

Sont interdits : mot de passe, identifiant de connexion IG, clé API, token/session IG, payload brut
authentifié et identifiant de compte broker réel/démo.

## Comportement runtime proposé

- Aucun fichier n'est créé à l'import ni au démarrage.
- `Sauvegarder la session Paper` initialise/migre puis écrit un nouveau checkpoint atomique.
- `Restaurer la session Paper` charge le dernier checkpoint valide ; si la session courante n'est
  pas vide, une confirmation visible est obligatoire.
- Une restauration invalide laisse la session courante intacte et affiche la cause.
- La reprise reste locale : aucune connexion ni synchronisation IG.

## Migration et retour arrière

- Base inexistante : création transactionnelle directe du schéma v1 puis v2.
- Base v1 existante : copie sœur horodatée avant migration.
- Base non versionnée avec tables ou version >2 : refus sans mutation.
- Échec SQL, validation ou intégrité : fermeture, restauration exacte du backup et erreur visible.
- Le backup n'est jamais supprimé automatiquement.

## État local observé

- Base runtime proposée : absente au 23 octobre 2026.
- Aucun fichier utilisateur ne serait donc migré lors de la première sauvegarde, sauf création
  externe entre cette prévisualisation et l'exécution ; le code doit néanmoins couvrir v1→v2.

## Alternatives écartées

- JSON séparé : évite la migration mais crée un second contrat de stockage et affaiblit l'audit
  transactionnel.
- Journal v1 seul : données insuffisantes pour une reprise exacte et sûre.
- Sauvegarde automatique à chaque tick : I/O implicite et bruit excessif, contraire au choix d'une
  persistance explicite.

