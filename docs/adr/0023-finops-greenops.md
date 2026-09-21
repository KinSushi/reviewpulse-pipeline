# ADR 0023 — FinOps et GreenOps

**Date** : 20/09/2026 · **Statut** : acceptée

## Contexte

Le référentiel AIA 4 impose la mise en place de pratiques FinOps et de soutenabilité (GreenOps).  
Le projet tourne exclusivement sur une machine Windows locale, via Docker. Aucun service cloud n’est facturé ; le coût monétaire d’infrastructure est donc **zéro**.  

Malgré l’absence de dépense financière, les ressources suivantes sont consommées :

* Temps CPU / temps d’exécution des pipelines (ex. DAG complet : 34 min 27 s).  
* Espace disque occupé par les images Docker (`reviewpulse-airflow` 4,18 Go, `reviewpulse-app` 3,37 Go, `reviewpulse-dev` 3,35 Go).  
* Énergie électrique liée à l’utilisation du serveur local (mesure non disponible).  

Le projet ne possède aucune métrique de coût monétaire, ni de mesure d’énergie. Il faut donc définir ce qui sera mesuré à partir des artefacts déjà disponibles.

## Decision

1. **Reconnaître que le coût monétaire est nul** mais que le FinOps reste applicable : le « coût » inclut le temps machine, l’espace disque et l’énergie consommée.  
2. **Indicateurs mesurables retenus** (exploités avec les outils déjà présents) :  
   - **Durée totale du DAG quotidien** – 34 min 27 s (mesure déjà disponible dans les logs Airflow).  
   - **Taille des images Docker** – 4,18 Go, 3,37 Go, 3,35 Go (obtenues via `docker images`).  
   - **Durée de la batterie de tests** – 8 min 07 s pour 125 tests (rapport de `pytest`).  
   Aucun indicateur ne nécessite l’ajout d’un outil externe (ex. monitoring cloud, collecteur d’énergie).  
3. **Retrait de `confluent-kafka`** (19/09/2026) est consigné comme la première décision FinOps du projet : la dépendance était présente dans chaque image sans être utilisée, augmentant inutilement la taille des images. Sa suppression a réduit l’enveloppe disque de chaque image de façon mesurable.  
4. **GreenOps** – aucune donnée de consommation énergétique n’est collectée. Pour se conformer aux exigences, il faut :  
   - Installer un moniteur de puissance (ex. `powermetrics` sous Windows ou un wattmètre externe).  
   - Enregistrer la consommation pendant les exécutions du DAG et des tests.  
   - Rapporter les kWh par jour/semaine/mois.  
5. **Déploiement réparti** – passer d’une exécution monolithique sur une seule machine à un déploiement multi‑noeuds (ex. plusieurs containers sur des machines distinctes) impliquerait :  
   - La nécessité de mesurer la latence réseau et la synchronisation des tâches.  
   - Un suivi du coût total de possession (CAPEX) des machines additionnelles.  
   - Aucun chiffre n’est fourni car aucune mesure n’a été réalisée à ce jour.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Ne mesurer que le coût monétaire | Le projet n’a aucun coût monétaire, mais le référentiel exige la prise en compte du temps, du disque et de l’énergie. |
| Introduire un outil de monitoring cloud (ex. Datadog) | Aucun service cloud n’est utilisé ; l’ajout d’un tel outil introduirait un coût monétaire non justifié. |
| Reporter la décision FinOps à plus tard | Le retrait de `confluent-kafka` a déjà démontré un gain mesurable ; attendre ne respecterait pas l’obligation de décision immédiate. |

## Consequences

* Le tableau de bord FinOps affichera : durée du DAG, tailles d’images et durée des tests.  
* La suppression de `confluent-kafka` réduit l’enveloppe disque, améliore les temps de pull d’image et constitue un gain concret.  
* L’absence de mesures énergétiques crée un gap : il faudra planifier l’acquisition d’un dispositif de mesure d’énergie.  
* Un futur passage à un déploiement réparti devra être accompagné d’une nouvelle série d’indicateurs (latence réseau, utilisation CPU par nœud, coût matériel).  
* Le projet reste conforme au référentiel AIA 4 tout en restant réaliste quant aux données disponibles.  

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
