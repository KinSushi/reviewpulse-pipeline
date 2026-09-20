# Exécution réelle du DAG quotidien — preuve

*Run* : `preuve-230932` · *Date UTC* : 2026-09-20T04:11:59Z → 04:46:26Z · *Durée* : 34 min 27 s

*Commit* : 4905007 · *Machine* : dépôt et données Docker sur le disque externe, d'où les durées.


## Les neuf tâches

| Tâche | État | Début UTC | Fin UTC |
|---|---|---|---|
| `ingest` | **success** | 04:12:30 | 04:13:46 |
| `spark_silver` | **success** | 04:13:51 | 04:27:49 |
| `gx_validate` | **success** | 04:28:31 | 04:32:17 |
| `score` | **success** | 04:32:22 | 04:37:49 |
| `drift` | **success** | 04:37:59 | 04:38:09 |
| `gold` | **success** | 04:38:19 | 04:46:15 |
| `gx_lake` | **success** | 04:46:17 | 04:46:26 |
| `derive_exige_reentrainement` | **success** | 04:38:19 | 04:38:32 |
| `declencher_reentrainement` | **skipped** | 04:38:28 | 04:38:28 |

Huit au vert, une `skipped`. Le saut n'est pas un incident : c'est le comportement attendu
quand la dérive ne dépasse pas le seuil, et le journal ci-dessous le montre chiffre en main.


## Ce que la porte de qualité a réellement validé (tâche `gx_lake`)

| Suite | Succès | Attentes évaluées | Échecs |
|---|---|---|---|
| `silver_reviews` | True | 8 | 0 |
| `silver_predictions` | True | 7 | 0 |
| `gold_faits` | True | 7 | 0 |
| `gold_mart` | True | 7 | 0 |

**29 attentes, aucun échec**, sur les deux zones que la campagne ne couvrait pas jusqu'ici :
silver (Iceberg) et gold (DuckDB). C'est ce qui ferme le sujet R10.


## Pourquoi le réentraînement n'a pas été déclenché (tâche `drift`)

```
PSI sur les entrées : text_len 0,0399 · language 3,0558 · app_id 0,3410 · sample_source 0,0000
```

Seul `text_len` appartient à `COLONNES_ALERTE`, et il vaut **0,0399** pour un seuil de **0,2**.
Le PSI de `language` est élevé — 3,056 — mais il mesure notre **plan de collecte**, pas la
population : c'est le défaut trouvé le 19/09, et la raison pour laquelle cette colonne est
hors alerte. `derive_exige_reentrainement` a donc rendu « non », et
`declencher_reentrainement` a été sautée. La branche a été **évaluée**, pas contournée :
c'est ce qui ferme le sujet R11.


## Ce que cette exécution n'établit pas

Un passage vert ne prouve pas que la porte **refuse** une donnée non conforme : c'est le rôle
des mutations M23 et M24, tuées par `tests/test_expectations_lake.py`. Et elle ne prouve pas non
plus qu'une alerte de dérive déclenche bien le réentraînement — seulement que l'absence
d'alerte ne le déclenche pas. Le chemin inverse reste couvert par les tests, pas par cette
exécution.

---

## Première mesure du point d'accès `/metrics` — 20/09/2026

Relevé sur la pile réelle, quelques minutes après un redémarrage à froid de l'API :

```
total_requests  : 6        samples_retained : 5        uptime : 307 s
/health    count=4   p50 =   8 090 ms   p99 = 179 491 ms   max = 184 542 ms
/predict   count=1                                          max =   2 480 ms
```

**Ce que ce relevé établit, dès son premier usage.** Un contrôle de santé a mis **184
secondes**. C'est le sujet R55 enfin chiffré : `/health` déclare `Depends(get_model)`, donc
il charge le champion depuis MLflow, et sur ce disque le chargement s'étire. Jusqu'à ce
relevé, nous savions seulement que l'API « semblait bloquée » ; nous avons maintenant une
durée. C'est précisément ce qu'une surveillance de la latence sert à faire.

**Ce qu'il ne faut pas en conclure.** Ces chiffres sont ceux d'un service **à froid**, et
`/metrics` mélange les deux régimes. Le même système mesuré à chaud rend `/health` en 5 ms
et `/predict` en 96 ms, et l'essai de charge donne un p99 à 925 ms sur 300 requêtes. Annoncer
les 184 secondes sans dire « premier appel après démarrage » serait aussi trompeur
qu'annoncer les 5 ms sans dire « à chaud ». L'ADR 0029 consacre un paragraphe à ce piège.

**Et un détail qui valide un correctif.** `total_requests` vaut 6 quand `samples_retained`
vaut 5 : le sixième appel est celui de `/metrics` lui-même, compté mais non retenu, puisque
le point d'accès d'observation ne s'observe pas. Le compteur réel ajouté à l'audit — là où
le code produit déduisait le total de files bornées — se lit donc dans le premier relevé.
