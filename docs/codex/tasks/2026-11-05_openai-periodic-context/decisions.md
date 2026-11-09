# Decisions

- Le consentement périodique est distinct du consentement au probe et n'est jamais persisté.
- Le premier cycle automatique intervient après l'intervalle de 15 minutes ; l'action manuelle reste
  disponible immédiatement.
- Un cycle sans preuve `ai_evidence`, sans clé ou pendant un appel actif est ignoré sans file
  d'attente ni retry agressif.
- Une analyse IA ne produit qu'un contexte typé. Toute intention d'ordre future reste soumise à un
  orchestrateur déterministe, au Risk Engine et à une activation AUTO distincte.

