# Jour J — 25/09/2026 : une seule commande, puis ne plus rien toucher

À lancer **quinze minutes avant de passer**, dans un PowerShell ouvert sur le dépôt
(`D:\ReviewPulse_work\ReviewPulse`) :

```powershell
sh tools/jour_j.sh
```

Ce qu'elle fait, dans l'ordre, et pourquoi :

1. lève la pile si elle ne tourne pas (`docker compose up -d`, **sans reconstruire** : l'écriture d'une
   image ne se termine jamais sur ce disque) ; Airflow compris ;
2. attend que l'API réponde — le premier appel après un démarrage charge le modèle : jusqu'à trois
   minutes sur ce disque, c'est normal, c'est mesuré ;
3. lance le contrôle avant vol `tools/prevol_demo.sh` : services, réchauffement, phrase du discours,
   champion en service, Airflow ;
4. affiche **PRÊT** ou **PAS PRÊT** avec la liste des manques.

Si c'est PRÊT : ne redémarre rien, ouvre `http://localhost:8501` (tableau de bord), `http://localhost:8000/docs`
(API) et `http://localhost:8080` (Airflow) dans le navigateur, et le support `ReviewPulse_DemoDay.pptx`.

## Condition préalable : les images doivent exister (R81)

Le 22/09 à 19 h 46, les images `reviewpulse-app` et `reviewpulse-airflow` ont été supprimées depuis
Docker Desktop ; les volumes du registre MLflow et d'Airflow sont intacts. La commande ci-dessus
ne reconstruit pas : sans images, elle rend PAS PRÊT. Avant vendredi, vérifier :

```powershell
docker images reviewpulse-app reviewpulse-airflow
```

Si l'une manque, la reconstruire **la veille au plus tard** (`docker compose --profile airflow build`),
puis relancer `sh tools/jour_j.sh` jusqu'à PRÊT. L'écriture d'une image a déjà bloqué sur ce disque
(R46) : ne pas découvrir ce blocage le jour J.

## Interface Airflow : fixer le mot de passe une fois, avant vendredi

Le mode `standalone` a créé le compte `admin` avec un mot de passe généré, qui n'est plus lisible
(journal recyclé, fichier absent) : sans cette étape, l'onglet Airflow de la démonstration resterait
sur la page de connexion. À faire **une fois**, dans un PowerShell, en choisissant le mot de passe
toi-même (il n'est écrit nulle part dans le dépôt) :

```powershell
docker exec -it reviewpulse-airflow-1 airflow users reset-password -u admin
```

La commande demande le mot de passe au clavier. Ensuite : `http://localhost:8080`, utilisateur `admin`.

Répétition générale faite le 21/09/2026 à 19 h 10 : PRÊT, 12 contrôles sur 12.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
