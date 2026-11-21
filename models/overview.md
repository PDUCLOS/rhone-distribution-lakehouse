{% docs __overview__ %}
# Rhône Distribution Lakehouse

**Un distributeur B2B lyonnais fictif, un entrepôt de données modélisé avec dbt.**

Rhône Distribution (5 agences, environ 1 200 clients professionnels) veut piloter chiffre d'affaires, marge, DSO et taux de service, sans que chacun voie tout : les commerciaux ne voient que leur agence, les contacts clients (RGPD) et les coûts sont masqués selon le rôle.

Ce site est la documentation générée par dbt à chaque mise à jour du code : modèles, colonnes, tests et graphe de lignage.

## Comment lire ce site

- **Projet → rhone_distribution → models** : les couches **silver** (données nettoyées, anomalies en quarantaine) et **gold** (dimensions, faits et agrégats prêts pour Power BI).
- **Sources → bronze** : les extractions nocturnes de l'ERP simulé.
- **Graphe de lignage** : bouton bleu en bas à droite, ou l'onglet « Lineage » d'un modèle.

## Ce qu'il faut regarder

- `silver_quarantine` et le test `assert_quarantine_matches_injected_anomalies` : 70 anomalies injectées par le générateur, le test exige de les retrouver toutes, ni plus ni moins.
- `fct_ventes_jour` : table de faits incrémentale, grain jour × client × produit × agence × commercial × canal.
- `dim_client`, `dim_produit` : les champs marqués `pii` ou `confidentiel_finance` reçoivent un masquage Snowflake par post-hook.

## Statut

Construit avec dbt Core et validé en local (PostgreSQL + DuckDB), 64 tests rejoués à chaque push. Scripts Snowflake (chargement, rôles, row access, masking) prêts, pas encore exécutés sur un compte Snowflake.

**Données fictives** : ERP simulé, profil clients issu d'un agrégat SIRENE réel, aucun nom ni SIREN réel associé à un historique simulé.

Code : [github.com/PDUCLOS/rhone-distribution-lakehouse](https://github.com/PDUCLOS/rhone-distribution-lakehouse) · Projet présenté sur [pduclos.github.io](https://pduclos.github.io/projets/rhone-distribution.html) · Patrice Duclos
{% enddocs %}
