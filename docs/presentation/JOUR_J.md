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

Répétition générale faite le 21/09/2026 à 19 h 10 : PRÊT, 12 contrôles sur 12.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*
