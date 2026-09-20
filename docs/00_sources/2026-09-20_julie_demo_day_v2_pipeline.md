# Source primaire — consigne du Final Project, parcours **Data Lead v2** (`lead-data-v2`)

**Lue le** 20/09/2026, dans le navigateur intégré, session d'Enzo.
**Adresse** : `https://app.jedha.co/course/m05-d01-final-project-lead-data-v2/capstone-project-instructions-lead-data-v2`
**Titre** : « Build a Data Pipeline That Feeds an AI Model 🏗️ » · **840 min** · module *Project Prep*

> **C'est la consigne qui prime pour le Demo Day du 25/09/2026.** Celle du parcours `dse-lead`
> (« Project Overview », 1 200 min) relève de **Data Lead v1** et est versée séparément dans
> `2026-09-20_julie_demo_day_project_overview.md`. Enzo a demandé que le projet **couvre les
> deux**. Les deux tableaux de conformité vivent donc côte à côte.

## La mission

> « You build one data pipeline, end to end, for a business problem you pick yourself. »

## Les cinq exigences non négociables

| # | Exigence, mot pour mot | ReviewPulse |
|---|---|---|
| 1 | « solve a real business case with **real data you found** » | avis Steam collectés par l'API publique, 8 768 lignes |
| 2 | « land the data **raw and unchanged** in a first storage zone **before anything touches it** » | zone brute immuable, ingestion idempotente par curseur et manifeste (ADR 0002) |
| 3 | « transform that raw data into a clean, model-ready dataset with **dbt, PySpark, or pandas**, protected by **at least one data quality test** » | PySpark vers silver Iceberg, dbt vers gold DuckDB, Great Expectations sur **les trois zones** — 29 attentes, 0 échec |
| 4 | « an **AI step** that consumes the pipeline output: an ML model tracked with **MLflow**, or an LLM chain built with LangChain » | régression logistique suivie dans MLflow, alias `champion`, barrière de promotion |
| 5 | « At least one part of the chain must **run on its own**, through an Airflow DAG, a cron schedule, or a GitHub Actions workflow » | DAG Airflow quotidien, **neuf tâches**, exécuté en réel le 20/09 |

**Les cinq sont tenues.** « Everything else, the domain, the model type, the tools, is your call. »

## Le choix ML ou LLM, et comment le défendre

> « Choose the model type from the task, not from what sounds impressive. If the job is to
> predict or sort structured data […] classic machine learning is usually the right and cheaper
> tool. […] A good Data Lead can say in one sentence why their choice matches their problem. »

Notre phrase : *classer un avis en positif ou négatif est une tâche de tri supervisée sur un
signal textuel court et étiqueté par la plateforme elle-même ; un classifieur linéaire la résout
avec une explication exacte et un coût nul, là où un LLM ajouterait latence, coût et
approximation.* Voir ADR 0006 et ADR 0019.

## Ce que la consigne attend jour par jour

**Jour 1 — livrables** : la charte d'une page, le diagramme d'architecture v1, et une ingestion
qui remplit la zone brute depuis la source vivante. La charte doit dire : **qui est l'utilisateur,
quelle décision il prend aujourd'hui, ce qu'elle lui coûte, ce que « assez bon pour être utile »
signifie**, plus trois lignes — **ce qui est hors périmètre** (« a written cut is a decision, a
silent one is missing work »), **qui possède la donnée**, et **quels champs sont des données
personnelles et comment ils sont protégés**.

**Jour 2 — livrable** : « one end-to-end run, from raw source to AI output, plus **one quality
number you can defend** ». Le nôtre : F1 macro **0,8027** sur un test 100 % naturel tenu à
l'écart (version 5 du registre).

**Jour 3 — livrable** : « the working demo, the repo, the diagram, and your presentation ».

## Le format de la soutenance

> « Prepare a **10-minute presentation with a live demo**, followed by **5 minutes of questions**
> from the panel: your business case, your ML-or-LLM choice, your pipeline design, and
> **what you would build next**. »

**« What you would build next » est une exigence du contenu, pas une politesse.** C'est ce que
porte la dernière diapositive et la minute 8:00–9:20 du script.

## Deux avertissements de la consigne, à ne pas perdre

> « **The model is the easy part.** Most learners want to spend the whole project tuning the
> model. **Do not.** […] The grade and the real-world value come from the chain around it. »

Noter la tension avec la consigne **v1**, qui exige explicitement « Tune hyperparameters ». Les
deux sont satisfaites — le réglage a été fait et mesuré (ADR 0006, `reglage_hyperparametres.md`)
— mais la présentation doit suivre v2 : la chaîne d'abord, le modèle comme une boîte du schéma.

> « **Real data, or the project is a toy.** […] Pick a source that updates, that has missing or
> broken records, and that forces your transformations to do real work. The mess is the lesson. »

## Ce qui est explicitement facultatif

FastAPI, Streamlit et Docker sont des **stretch goals**, pas des exigences : « These last two are
stretch goals, not requirements. » Le projet les a tous les trois.

## Un écart de contexte, assumé

La consigne prévoit des **équipes de deux ou trois** — « You work in teams of two or three » — et
précise que le jury interroge chacun sur toute la chaîne. Le projet est porté par une seule
personne. Ce n'est pas un manque à combler, c'est un fait à dire si la question vient.
