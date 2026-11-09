# Plan — confirmation explicite de devise du ticket Paper

## Objectif vérifiable

Permettre l'évaluation sûre d'un produit dont la découverte IG ne fournit pas la devise, sans
fallback implicite : l'utilisateur doit confirmer un code devise explicite, et le veto FX reste
actif pour toute devise différente de l'EUR sans taux fourni.

## Symptôme reproduit

Une Barrière avec cotation directe valide mais `TradableProduct.currency=None` est refusée avec
`devise produit inconnue`; aucun champ GUI ne permet actuellement de lever ce manque de donnée.

## Approche minimale

1. Ajouter au ticket un champ de devise à trois lettres : verrouillé quand la métadonnée IG est
   connue, éditable et vide lorsqu'elle manque.
2. Conserver une provenance visible et un avertissement dans la proposition lors d'une
   confirmation utilisateur.
3. Clarifier les libellés stop/objectif/KO comme niveaux absolus et afficher la règle directionnelle.
4. Couvrir devise manquante, confirmation EUR, code invalide et veto FX non-EUR.

## Skills déclarées

- `aurora-diagnose`
- `codex-tradingig-accounts-risk`

## Limites

- Aucune devise n'est déduite du compte, du nom du produit ou de l'EPIC.
- Aucun taux FX n'est fabriqué et aucune métadonnée réseau supplémentaire n'est appelée.
- Aucun ordre IG, dépendance, migration ou stockage n'est ajouté.

