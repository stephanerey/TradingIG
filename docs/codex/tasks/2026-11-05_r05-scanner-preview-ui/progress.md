# Progress

- [x] Portée fonctionnelle définie.
- [x] Service preview.
- [x] Widget et branchement MainWindow.
- [x] Tests et documentation.
- [x] Snapshot REST borné aux 32 dernières bougies du sous-jacent et du timeframe sélectionné.
- [x] Disjoncteur de quota historique persisté entre redémarrages depuis les métadonnées IG.
- [x] Flux direct au timeframe sélectionné ; le cache stream clairsemé n'est plus restauré dans la GUI.
- [x] Exclusion du préfixe antérieur au dernier trou de données dans le Scanner.
- [x] Refus Scanner explicite d'un snapshot périmé après redémarrage ou interruption prolongée.
- [x] Réparation REST bornée déclenchée une seule fois lorsqu'un trou apparaît au bord live.
- [x] Validation Windows sur 25 bougies M1 d'un flux IG réel ; breakout SELL confirmé.
- [ ] Validation future des paramètres de stratégie et des nouvelles colonnes de score.
