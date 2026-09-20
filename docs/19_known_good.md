# Points de reprise — KNOWN_GOOD

Ce fichier existe pour qu'on n'ait **jamais** à reconstruire l'état du projet de mémoire.
Chaque entrée dit ce qui était sain, ce qui le prouvait, et comment y revenir.

**Règle** : un état n'est `KNOWN_GOOD` que si compilation, imports, exécution, test avant,
test inverse et non-régression ont été vérifiés **et datés**. Si un seul de ces éléments est
inconnu, l'état est `PARTIELLEMENT_VALIDE`, `BLOQUE` ou `EN_ECHEC` — jamais `KNOWN_GOOD`.

---

## KG-2026-09-19-a — `KNOWN_GOOD`

**Commit** : `b44a5d2` · **Date** : 19/09/2026, 17 h.

| Preuve | Résultat | Quand |
|---|---|---|
| Compilation (`compileall`) | verte | 19/09 |
| Batterie complète, copie neuve | **90 tests verts**, 53 min | 19/09 |
| Test de la stack déployée | **16 contrôles sur 16** | 19/09 |
| Tests inverses | 16 mutations sur 16, sur l'arbre du 18/09 | 18/09 |
| DAG Airflow | 8 tâches listées, aucune erreur d'import | 19/09 |
| Retour arrière du modèle | champion 2 → 1 → 2, vérifié à chaque pas | 19/09 |
| Restauration MLflow | archive restaurée dans un volume d'essai, versions 1 à 4 et alias retrouvés | 19/09 |

**Ce qui le constitue** : tout le dépôt à ce commit, plus le lac sur `D:\ReviewPulse_work\data`
(hors dépôt, intact depuis le 16/09) et les images `reviewpulse-app`, `reviewpulse-airflow`,
`reviewpulse-dev`.

**Comment y revenir** : `git checkout b44a5d2`. Le lac n'est pas versionné : il n'est pas à
restaurer, il n'a pas bougé. Les images se reconstruisent depuis le dépôt.

**Risque connu à cette date** : les tests inverses dataient de l'arbre du 18/09, avec 16
mutations et non 26.

---

## KG-2026-09-19-b — `PARTIELLEMENT_VALIDE`

**Commit** : `116c486` · **Date** : 19/09/2026, 18 h 45.

**Pourquoi pas `KNOWN_GOOD`** : depuis `b44a5d2`, quatre lots de tests ont été ajoutés et
vérifiés **isolément**, mais **aucune batterie complète n'a rendu son résultat** sur cet arbre,
et la campagne des 26 mutations tourne encore. Tant qu'elle n'a pas rendu, cet état ne peut pas
être déclaré sain.

| Preuve | Résultat | Quand |
|---|---|---|
| Compilation | verte sur chaque fichier touché | 19/09 |
| Imports | vérifiés module par module | 19/09 |
| `tests/test_expectations_lake.py` | 7 verts | 19/09 |
| `tests/test_verifier_justifications.py` | 9 verts | 19/09 |
| `tests/test_verifier_briques.py` | 9 verts | 19/09 |
| `tests/test_drift.py` | 11 verts | 19/09 |
| `make justifications` | code 0 — 20 ADR sur 20 cités dans le code **et** dans les questions | 19/09 |
| `make briques` | code 0 — 73 briques classées, chaque manque porte un sujet | 19/09 |
| Porte silver et gold, données réelles | 28 attentes vertes, témoin rouge sur données faussées | 19/09 |
| **Batterie complète** | **non rendue** | — |
| **26 mutations** | **en cours** | — |

**Ce qui manque pour passer `KNOWN_GOOD`** : la batterie complète verte et les 26 mutations
détectées sur cet arbre. La campagne est lancée ; son résultat conditionne l'étiquette.

**En cas d'échec** : revenir à `KG-2026-09-19-a` (`git checkout b44a5d2`), qui est prouvé sain.

---

## KG-2026-09-19-c — `BLOQUE` (environnement)

**Commit** : `563e675` · **Date** : 19/09/2026, 20 h 30.

**Ce qui bloque** : Docker Desktop ne démarre plus — `docker daemon did not become ready`.
Les processus `Docker Desktop.exe` et `com.docker.backend.exe` tournent, le démon non.
Cause déclarée par Enzo : un redémarrage de Docker pour un réglage IPv4/IPv6.

**Ce qui a précédé, et qui compte** : la campagne lancée à 17 h 30 a tourné **3 h 09 à
0,13 % de CPU**. Observation à la source : `wchan` du processus pytest = `submit_bio_wait`,
descripteurs ouverts sur une base SQLite MLflow d'un dossier temporaire de test, et une JVM
Spark vivante depuis 2 h 25 sans activité. Ce n'était donc **pas** un défaut du projet mais
un blocage d'entrées-sorties du disque virtuel. La campagne est morte avec le démon, sans
rien produire.

**Deux causes, deux remèdes** :
1. *Environnement* : le démon doit redémarrer. Hors de mon périmètre, c'est l'interface
   d'Enzo.
2. *Harnais, de mon fait* : la sortie était tuyautée dans `tail -12`, donc invisible pendant
   trois heures, et aucune garde de temps ne bornait la course. Corrigé par
   `tools/campagne_preuves.sh` (`make campagne`) : journal daté écrit au fil de l'eau par
   `stdbuf`, une garde `timeout` par phase, code de sortie non nul au dépassement.

**État de la preuve** : inchangé depuis `KG-2026-09-19-a`. Les tests ajoutés depuis restent
vérifiés isolément seulement.

**Prochaine action** : au retour du démon, `make campagne`, puis étiqueter
`KG-2026-09-19-b` selon le résultat.


## Incident 2026-09-19-d — la batterie n'a pas tourné, et le script l'a caché

**Constat** : le journal de la campagne de 20 h 34 passe de « compilation, code 0 en 32 s »
directement à « tests inverses », sans aucune ligne pour la batterie.

**Cause, trouvée dans le conteneur** : `JOURNAL` était un chemin **relatif**
(`docs/evidence/…`). La batterie tourne dans une copie temporaire du dépôt, où `docs/`
n'existe pas — vérifié : `ls /tmp/campagne.zX4NrU` ne contient que `src`, `tests`,
`dashboard`, `dags`, `dbt` et `pyproject.toml`. Le `tee` écrivait donc vers un répertoire
absent, le tuyau se rompait, et la phase mourait en silence, **y compris son propre message
d'erreur**, qui passait par le même tuyau.

**Ironie à retenir** : ce script avait été écrit le matin même pour empêcher qu'une campagne
meure sans rien montrer. Il a reproduit le défaut sous une autre forme. Un mécanisme de
surveillance doit être éprouvé comme le reste — le voir produire une ligne ne prouve pas
qu'il en produira toutes les lignes.

**Correction** : le chemin du journal est rendu absolu dès l'en-tête, par
`JOURNAL_DIR=$(cd "${JOURNAL_DIR}" && pwd)`.

**Conséquence sur les preuves** : aucune batterie n'a tourné sur l'arbre courant. L'état
reste celui de `KG-2026-09-19-a`. Les tests inverses, eux, tournent depuis 20 h 46 et
journalisent correctement, car cette phase s'exécute depuis `/app`.


## Incident 2026-09-19-e — le disque virtuel était le goulot, pas le code

**Signature** : un processus pytest en état `Dl` — sommeil **non interruptible** — attendant
`jbd2_log_wait_commit`, c'est-à-dire la validation du journal ext4 du disque virtuel. CPU du
conteneur à 0,2 % sur trois échantillons consécutifs. Même classe que le blocage de
l'après-midi, qui attendait `submit_bio_wait`.

**Cause** : les tests inverses recopient le dépôt **une fois par mutation**, soit 26 fois,
dans la couche d'écriture du conteneur — donc dans le `.vhdx` de WSL2. Le journal du système
de fichiers devient le goulot, et le travail utile tombe à zéro.

**Remède, dans notre périmètre** : monter `/tmp` en mémoire, `--tmpfs /tmp:size=3g`. La
machine a 30 Go, la copie du dépôt en pèse quelques dizaines. Le disque virtuel sort du
chemin critique.

**Mesure avant / après**, même image, même dépôt :

| | Sans tmpfs | Avec tmpfs |
|---|---|---|
| Phase de compilation | 32 s | **10 s** |
| Copie du dépôt avant la batterie | ~12 min | quelques secondes |
| Progression de la campagne | bloquée deux fois | la batterie démarre |

**À retenir** : un blocage qui ressemble à une lenteur du code peut être un blocage du
système de fichiers. La distinction se fait en une commande — `cat /proc/<pid>/wchan` — pas
en relisant le code.


## KG-2026-09-19-f — `PARTIELLEMENT_VALIDE`

**Commit** : `02f8f12` · **Date** : 19/09/2026, 21 h 45.

| Preuve | Résultat | Quand |
|---|---|---|
| Compilation | code 0 en 10 s | 19/09 |
| **Batterie complète**, copie neuve, `tools/` compris | **125 tests verts en 8 min 07** | 19/09 |
| `make justifications` | code 0 — 20 ADR sur 20 | 19/09 |
| `make briques` | code 0 — 73 briques classées | 19/09 |
| Test de la stack déployée | 16 contrôles sur 16 | 19/09 |
| **26 mutations** | **en cours** | — |
| Essai de charge | outil écrit, 10 tests verts, **jamais lancé contre la stack** | — |

**Pourquoi pas encore `KNOWN_GOOD`** : les mutations n'ont pas rendu, et l'essai de charge
n'a pas tourné contre un service réel. Deux preuves manquent, donc l'état n'est pas sain au
sens de ce fichier.

**Ce que cette batterie ferme** : R21, R24, R27 et R28, avec leur preuve (F29 à F32).

**Gain mesuré du `tmpfs`** : la même batterie passait de 53 minutes à **8 minutes 07**, soit
six fois et demie plus vite, et sans blocage. Le disque virtuel était le goulot, pas le code.

**Comment y revenir** : `git checkout 02f8f12`, puis
`docker run --rm --tmpfs /tmp:size=3g … sh tools/campagne_preuves.sh`.


## KG-2026-09-19-g — `KNOWN_GOOD`

**Commit** : à celui de ce commit · **Date** : 19/09/2026, 23 h 15.

| Niveau | Preuve | Résultat |
|---|---|---|
| 1 — compilation | `compileall src tools dags tests` | code 0 |
| 2 — imports | `essai_charge` importé sur le Python 3.14 de l'hôte, sans dépendance du projet | OK |
| 3 — exécution | API et MLflow levés, `/predict` interrogé | 200 en 170 ms |
| 4 — test avant | batterie complète, copie neuve | **125 tests verts en 8 min 07** — `docs/evidence/batterie_125_tests.log` |
| 4 — test avant | test de la stack déployée | **16 contrôles sur 16** |
| 5 — test inverse | mutations | **26 sur 26 tuées**, en deux temps — voir la note ci-dessous |
| 6 — machine | essai de charge, 300 requêtes à 10 en parallèle | **0 % d'erreur**, 29,3 req/s, p99 925 ms |
| 7 — non-régression | `make justifications`, `make briques` | code 0 tous les deux |

**Note du 19/09/2026, 21 h — comment ces deux chiffres sont établis, et pourquoi il fallait
le dire.** Un audit a d'abord constaté qu'aucun journal de `docs/evidence/` ne montrait ni les
125 tests, ni les 26 mutations sur 26 : les deux seuls journaux de campagne y sont **antérieurs**
aux correctifs de M17 et M22, et le plus récent rapporte 24 tuées sur 26. Les deux lignes ont donc
été marquées non prouvées. Les journaux existaient pourtant : ils étaient restés **dans les
conteneurs arrêtés**, `rp-batterie` et `rp-m17m22`, et non sur le disque. Ils sont désormais
conservés sous `docs/evidence/`.

Ce qu'ils montrent exactement :

* `batterie_125_tests.log` — `125 passed in 487.75s (0:08:07)`, copie neuve, un seul passage ;
* `mutations_M17_M22.log` — M17 **TUEE** par
  `test_main_rend_un_sur_une_zone_propre_non_conforme`, M22 **TUEE** par
  `test_lakehouse_restore_snapshot`.

**La nuance à dire au jury** : le « 26 sur 26 » n'est pas le résultat d'une seule campagne. Il
compose 24 mutations tuées lors de la campagne de 21 h 17 et 2 tuées lors d'un passage ciblé
qui a suivi les correctifs. La composition est légitime — les correctifs n'ont **ajouté que des
tests**, sans toucher au code de production, si bien que les 24 verdicts antérieurs restent
valides. Elle reste une composition, et la présenter comme un seul passage serait faux. Le sujet
**R44** demande une campagne unique de bout en bout pour remplacer cette composition.

**La leçon, qui vaut plus que le chiffre** : un journal écrit dans un conteneur éphémère n'est
pas une preuve conservée. `campagne_preuves.sh` écrit désormais dans un chemin **absolu** sous
`docs/evidence/` ; c'est la seule raison pour laquelle les campagnes futures survivront à leur
conteneur.

**Ce qui distingue cet état des précédents** : c'est le premier où les six niveaux ont été
franchis et datés le même jour, sur le même arbre.

**Trois défauts trouvés en y arrivant, tous par la machine et non par relecture** :
1. Mon outil de charge envoyait `{"text": …}` alors que `/predict` attend `{"texts": [...]}`.
   Le service répondait 422 ; la campagne n'aurait mesuré que des rejets.
2. J'ai lu un code de sortie **après un tuyau** et conclu à tort que la porte ne fermait pas.
   Le statut lu était celui de `tail`. Vérifié sans tuyau : la porte ferme.
3. Le contrôle de santé de MLflow n'avait pas de `start_period` : mesuré, 170 s pour devenir
   sain, si bien que `compose up` abandonnait sur « dependency failed to start ».

**Nuance à dire au jury** : le premier passage de charge donne un p99 de **5 874 ms**, le
second **925 ms**. L'écart est le démarrage à froid, chargement du modèle compris. Un chiffre
de latence sans cette précision serait trompeur.

**Ce qui reste hors de cet état** : la vidéo, la publication du dépôt, quatre présentations
sur six, et les briques absentes du registre R17. Aucune n'est un défaut du code.

**Comment y revenir** : `git checkout <ce commit>`, puis
`docker run --rm --tmpfs /tmp:size=3g … sh tools/campagne_preuves.sh`, puis `make charge`
contre la stack levée.


## Comment se servir de ce fichier

1. Après une compaction, un changement de modèle ou une interruption : lire **ce fichier
   d'abord**, puis `16_registre_suivi.md`, puis le plan unique.
2. Avant une opération risquée : identifier le dernier `KNOWN_GOOD` et vérifier qu'il est
   réellement restaurable.
3. Ne jamais écraser une entrée : en ajouter une. L'historique des états sert au diagnostic.

## KG-2026-09-20-a — `KNOWN_GOOD`

**Commit** : celui de cette entrée · **Date** : 20/09/2026, 3 h 30.

| Niveau | Preuve | Résultat |
|---|---|---|
| 1 — compilation | `compileall src tools dags tests` | code 0 |
| 1 bis — **lint** | `ruff check src tests dags dashboard tools`, phase neuve de la campagne | code 0 |
| 2 — imports | `reviewpulse.expectations_lake`, `drift`, `lakehouse` vus dans le conteneur Airflow | 17 modules |
| 3 — exécution | `/health` et `/predict` sur le champion en service | 200, **version 5**, 5 ms et 96 ms |
| 4 — test avant | batterie complète, copie neuve, conteneur | **131 tests verts** (`docs/evidence/campagne_20260920-045514.log`) |
| 4 — test avant | **DAG quotidien en réel** | **9 tâches**, 8 vertes et 1 sautée par conception (`docs/evidence/dag_execution_reelle.md`) |
| 4 — test avant | porte de qualité silver et gold | **4 suites, 29 attentes, 0 échec** |
| 5 — test inverse | mutations | 26 sur 26, en **deux passages** (R44) |
| 6 — machine | barrière de promotion interrogée deux fois | **promeut** `C=10.0`, **refuse** `C=4.0` |
| 7 — non-régression | `make justifications`, `make briques` | code 0 tous les deux |

**Ce qui distingue cet état** : c'est le premier où la chaîne quotidienne a tourné **en entier
en conditions réelles**, et où le modèle servi provient d'un hyperparamètre **mesuré** au lieu
d'être posé.

**Sept défauts trouvés en y arrivant, tous par la machine** :

1. `pyproject.toml` et `requirements.txt` se contredisaient sur `confluent-kafka` — dit par la
   porte `pip check`, à la dernière étape d'une construction de 31 minutes.
2. L'écriture d'une image ne se termine jamais sur ce disque : deux constructions complètes
   perdues à `exporting layers`. Contourné par un montage du source, pas masqué (R46).
3. Un `import os` manquant a tué la recherche d'hyperparamètres **après sept minutes de calcul**.
   `ruff` l'aurait vu ; la campagne ne le passait pas. Phase de lint ajoutée (R52).
4. Le détecteur d'exigences ne lisait que le gras : **65 exigences jamais classées** (R43).
5. Nos documents affirmaient un temps de lecture du dossier par le jury qui **n'existe pas**.
6. Le support ne se reconstruisait que sur une seule machine — chemins absolus Windows (R54).
7. `/health` charge le modèle, et le contrôle de santé de l'image l'interrogeait toutes les
   30 s avec un délai de 5 s : l'API se noyait sous ses propres contrôles (R55).

**Deux corrections de mes propres constats** : j'avais écrit que les preuves des 125 tests
étaient perdues — elles étaient dans `docker logs` de conteneurs arrêtés. Et j'avais écrit
qu'aucun test de sur-apprentissage n'existait — il existe, c'est sa portée qui manque.

**Comment y revenir** : `git checkout <ce commit>`, `docker compose --profile airflow up -d`
avec `REVIEWPULSE_SALT` exporté, puis `sh tools/campagne_preuves.sh` en conteneur détaché.
Ne jamais employer `docker run --rm` sur ce disque : le conteneur s'exécute, mais le retrait
de sa couche ne rend jamais la main.

## KG-2026-09-20-b — `PARTIALLY_VALIDATED`

**Date** : 20/09/2026, 10 h 30. **Pas un `KNOWN_GOOD`**, et la raison est nommée plus bas.

| Niveau | Preuve | Résultat |
|---|---|---|
| 1 — compilation | `compileall src tools dags tests` | code 0 |
| 1 bis — lint | `ruff check src tests dags dashboard tools` | **All checks passed** |
| 1 ter — documentation | `tools/verifier_documentation.sh` | code 0, aucun lien mort |
| 2 — imports | `expectations_lake`, `drift`, `lakehouse` dans le conteneur Airflow | 17 modules |
| 3 — exécution | `/health`, `/predict`, **`/metrics`** sur la pile réelle | 200, version 5, 5 ms et 96 ms |
| 4 — test avant | `tests/test_api.py`, dont 6 tests neufs | **17 passés** en 6 min 39 |
| 4 — test avant | DAG quotidien en réel | 9 tâches, 8 vertes, 1 sautée par conception |
| 5 — **test inverse** | témoin de la batterie non mutée | ⛔ **dépassement de 2 400 s** — voir ci-dessous |
| 6 — machine | `/metrics` mesure `/health` à **184 542 ms** | le défaut R55 enfin chiffré |
| 7 — non-régression | `justifications`, `briques`, `documentation` | code 0 tous les trois |

**Pourquoi ce n'est pas un `KNOWN_GOOD`.** Le niveau 5 n'a pas pu être franchi. Le témoin des
tests inverses — la batterie non mutée, qui doit passer avant toute mutation — a dépassé sa
garde de 2 400 s. C'est cohérent avec le reste : la batterie complète a mis **4 650 s** le même
jour, dix fois sa durée habituelle, sur le disque externe. L'outil a refusé de rendre des
résultats sans témoin valide, et le rapport précédent a été restauré plutôt que laissé écrasé
par un passage invalide. Tant que R46 tient, ce niveau reste hors de portée ici.

**Ce que ce point apporte de neuf depuis KG-2026-09-20-a** :

1. **Les hyperparamètres sont mesurés**, plus posés : `C=10.0` retenu sur 12 points, **promu par
   la barrière**, qui a **refusé** le même jour un réentraînement à `C=4.0`. F1 macro 0,8027.
2. **La latence est surveillée en continu** : `/metrics`, journaux structurés par requête.
   Première décision du projet prise par **croisement de trois familles de modèles**.
3. **Le standard de production est transmis aux agents**, mécaniquement, par `tools/deleguer.sh`.
   Jusqu'ici aucune délégation n'en portait.
4. **Dix défauts de lint dormants** trouvés et corrigés par la phase ajoutée le matin même.

**Ressources exploitées pour la première fois** : la bibliothèque technique locale — 4,3 Go
indexés, dont le chapitre « Monitoring Deployed Models » qui fonde l'ADR 0029 — et le croisement
multi-familles du banc, qui a produit **deux décisions réellement divergentes** avant arbitrage.

**Risques connus, non résolus** : R46, l'écriture d'image impossible sur ce disque, qui bloque
R13, R41 et R44. R55, `/health` qui charge le modèle, contourné par le contrôle de santé mais
non corrigé à la racine.

**Prochaine action** : R51 appartient à Enzo — sans les énoncés CDSD, la sixième présentation
reste hors de portée. Côté machine, R46 commande tout le reste.

**Comment y revenir** : `git checkout <ce commit>`, puis `docker compose --profile airflow up -d`
avec `REVIEWPULSE_SALT` exporté. Jamais `--build`, jamais `docker run --rm` : voir
`docs/22_runbook_deploiement.md`.


## KG-2026-09-20-c — `KNOWN_GOOD`

**Commit** : celui de cette entrée · **Date** : 20/09/2026, 21 h 30. **Tous les niveaux sont franchis**,
et pour la première fois le niveau 5 l'est par une machine que nous ne contrôlons pas.

| Niveau | Preuve | Résultat |
|---|---|---|
| 1 — compilation, lint, documentation | campagne : `compileall`, `ruff`, `verifier_documentation.sh` | code 0 chacun ; **aucune signature d'outil**, nulle part |
| 2 — imports | pile levée, 17 modules vus dans Airflow, API sert la version 5 | OK |
| 3 — exécution | `/health` 200 en 392 ms, `/metrics` 200 en 6 ms | version 5, seuil 0,775 |
| 4 — test avant | batterie en CI | **131 tests verts**, 5 min 06 |
| 4 — test avant | chaîne entière en CI, runner vierge | **5 798 avis ingérés, modèle promu, f1 0,7982** |
| 4 — test avant | DAG quotidien en réel | 9 tâches, historique intact après incident |
| 5 — **test inverse** | campagne inverse en CI | **27 mutations sur 27, 0 survivante**, un seul passage |
| 6 — machine | `/metrics` après le verrou | p50 **1 ms** sur `/health`, maximum 113 s au premier chargement à froid (184 s avant) |
| 7 — non-régression | `justifications`, `briques`, `documentation` ; CI verte sur les **six derniers envois** | code 0 |

**Ce qui distingue cet état** : le dépôt est **public** (`github.com/KinSushi/reviewpulse-pipeline`),
le secret est posé et éprouvé sans être lu, et **toutes les preuves de niveau 4 et 5 viennent d'un
runner GitHub** — la réponse à « ça marche chez moi ».

**Six défauts trouvés en y arrivant, tous par la machine ou par un contrôle mécanique** :
1. Cinq mentions d'outil subsistaient dans trois documents, toutes « méta » — retirées, et une porte
   les refuse désormais, dans les fichiers comme dans les commits.
2. « 43 tests dbt » n'avait **aucune trace exécutée** ; les contrats en déclarent 30.
3. La diapositive finale annonçait l'essai de charge comme restant à faire ; il était fait depuis la veille.
4. `@lru_cache` ne dédoublonne pas les appels concurrents : dix appels, dix chargements. Verrou posé,
   mutation M27 tuée par son témoin.
5. Toute la pile est tombée à 18 h 55 (137 / 143 / 0) après un décrochage du disque externe sous le
   montage des DAG ; relevée, historique intact.
6. Le dossier jury n'avait **aucune** question sur la preuve elle-même ; sept ajoutées.

**Ce qui reste hors de cet état** : la vidéo (R03), la répétition chronométrée (R05), la suppression
de l'ancien dépôt (R02), la sixième présentation (R51). Aucun n'est un défaut du code.

**Comment y revenir** : `git checkout <ce commit>` ; la chaîne se rejoue sur GitHub par
`gh workflow run pipeline.yml`, sans dépendre du disque externe.
