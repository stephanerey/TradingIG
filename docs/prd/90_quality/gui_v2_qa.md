# GUI V2 — Qualité, scénarios et critères d'acceptation

## Préambule

La référence visuelle est la série de maquettes V2. **Les maquettes ne sont pas des tests et leurs cotations ne sont pas des fixtures financières**. Chaque test utilise des données synthétiques explicitement marquées ou des sources autorisées, distingue Paper/DEMO/LIVE et ne place aucun ordre réel.

## Matrice d'acceptation

| ID | Vérification | Critère précis | Preuve |
|---|---|---|---|
| AC-GUI2-01 | Shell & navigation | 8 rubriques, tabs internes, header persistent, pas de reconnexion au clic | Windows screencast + mock session counter |
| AC-GUI2-02 | Thème sombre | palette, hiérarchie, contrastes, boutons vrais | captures Windows 1920×1080 et 1366×768 |
| AC-GUI2-03 | DPI | 100/125/150 %, aucun contrôle critique coupé | captures + navigation clavier |
| AC-GUI2-04 | FR / EN | navigation/menu/table/tooltips/erreurs/axes traduits; état inchangé FR→EN→FR | tests Qt + screenshots |
| AC-GUI2-05 | Header comptes | compte, environnement marché, mode Paper/Analysis, fonds/PnL seulement s'ils existent | mocks + changement de compte |
| AC-GUI2-06 | Santé IG | REST OK/stream refusé séparés, âge de quote exact, pas de faux connecté | fake adapter, clock contrôlée |
| AC-GUI2-07 | Santé IA | sans token: not-configured; pas de ping/payeur; dernière analyse expirée | fake OpenAI compteur appels |
| AC-GUI2-08 | Dashboard PnL | jour/semaine/mois/année EUR/%; équité synchronisée; N/A si historique absent | dataset fixtures avec trous |
| AC-GUI2-09 | Comptabilité stats | ordres refusés ≠ trades perdants; gagnants/perdants/nuls séparés | calcul connu, tests déterministes |
| AC-GUI2-10 | Portefeuille | table Paper et IG toujours identifiées, position stale marquée | replay Paper/connexion en lecture seule |
| AC-GUI2-11 | Scanner | multi-marchés, scores séparés, NO_TRADE, UNKNOWN non = 0 | fixtures et snapshot test |
| AC-GUI2-12 | Performance catalogue | 500+ lignes scroll/tri/filtre sans UI freeze | mesure Windows durée update |
| AC-GUI2-13 | Bindings | EPIC non lié ⇒ IA not-applicable et aucune inférence par nom | fixture DEMO barrière CAC |
| AC-GUI2-14 | Watchlist | chart existant + indicateurs sans valeurs sur données warmup | replay candle fragments |
| AC-GUI2-15 | LONG/SHORT | décisions marché séparées d'order_side d'un dérivé | 4 cas CFD/Barrière, sans ordre |
| AC-GUI2-16 | Paper actions | ouverture, save, restart, restore manuel, stop tighten, close | scénario intégration local |
| AC-GUI2-17 | Broker safety | aucun ordre LIVE/AUTO nouveau; méthodes disabled conservées | tests de negative capabilities |
| AC-GUI2-18 | Macro / calendrier | source/heure/TTL et données absentes ⇒ unknown, pas d'événement inventé | fixture sans provider |
| AC-GUI2-19 | IA apprentissage | proposition sans apply, dataset fingerprint, test/review/rollback | scenario offline + UI |
| AC-GUI2-20 | Persistance UI | géométrie, langue, onglet, palette et layout restaurés; JSON historique lu | migrations conf tests |
| AC-GUI2-21 | Timezone/devise | FR et EN formatent sans modifier Decimal ni UTC | tests num + DST |
| AC-GUI2-22 | Qt threading | aucune mise à jour model hors thread UI, aucun HTTP synchrone UI | instrumentation et tests |
| AC-GUI2-23 | Streaming quota | pas d'abonnement multi-produits à chaque navigation | fake IG adapter spy |
| AC-GUI2-24 | Stale/gap | screenshot affiche état réel, prix et horodatage stables pendant panne | fake clock + drop events |
| AC-GUI2-25 | Accessibilité | tab navigation, focus visible, non dépendance à la seule couleur | manual + smoke |
| AC-GUI2-26 | Erreurs / logs | messages lisibles, absence secrets, erreurs persistantes | sanitized export + tests |

## Objectifs mesurables proposés (non garantis)

- Temps de réponse à interaction souris/menu dans le shell : cible p95 < 150 ms sur machine de test Windows, à mesurer en contexte réaliste.
- Rafraîchissement des tables/catalogue : pas de freeze > 250 ms dû au rendu sur jeu mock 500+ produits; les couches réseau sont exclues du benchmark de rendu.
- Temps complet d'ouverture Dashboard avec mock data : cible < 2 s sans lancer de connexion supplémentaire.
- Mémoire, abonnements actifs, timers/workers et taille de file stables après 1 h de bascule entre pages; vérifier un scénario de 4 h de streaming réel autorisé dans une validation ultérieure.
- Pas de crash lors de déconnexion IG, switch compte, redimensionnement, restauration layout corrompu et changement de langue.

Les seuils sont des **objectifs initialement proposés**, à ajuster après la baseline mesurée et les contraintes matériel/flux.

## Stratégie de tests

1. **Unitaires** : projections PnL, dates, score labels, trad/format, mapping DTO, filters/model data roles, permissions, config migration.
2. **Intégration hors ligne** : faux adaptateurs IG/OpenAI, séries fictives bougies, PaperSessionService et SQLite temporaire, sans secrets; compteur de réseau.
3. **GUI offscreen** : création `QApplication`, changement de pages/langue, déclenchement d'intentions, stabilités, pas de demande réseau.
4. **Tests natifs Windows** : captures avant/après aux dimensions annoncées, navigation clavier, DPI, contraste, scroll, stress catalogue. Le validateur navigateur Playwright de SR Method ne prouve pas le rendu d'une app PyQt5 desktop : utiliser un outil/capture natif ou validation visuelle humaine.
5. **DEMO/LIVE readonly** : facultatif sur accès autorisé, compte correct, streaming uniquement des marchés permis; jamais un test d'ordre réel dans la suite GUI.

## DoD de la phase R09

Tout ce qui précède est soit validé par preuve ou explicitement marqué `user_testing`, `blocked` ou `deferred`. Le code de l'ancienne fenêtre n'est supprimé qu'après parité des flux IG, du Paper, du scanner et des workflows IA + validation utilisateur. Aucune nouvelle méthode d'ordre LIVE ou AUTO n'est activée.
