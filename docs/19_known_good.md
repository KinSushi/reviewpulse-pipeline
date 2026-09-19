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


## Comment se servir de ce fichier

1. Après une compaction, un changement de modèle ou une interruption : lire **ce fichier
   d'abord**, puis `16_registre_suivi.md`, puis le plan unique.
2. Avant une opération risquée : identifier le dernier `KNOWN_GOOD` et vérifier qu'il est
   réellement restaurable.
3. Ne jamais écraser une entrée : en ajouter une. L'historique des états sert au diagnostic.
