FROM apache/airflow:2.10.3-python3.11

# L'utilisateur airflow est utilisé pour éviter d'exécuter les commandes en tant que root.
USER airflow

# Copie des fichiers de configuration (pyproject.toml) et de la liste des dépendances (requirements.txt)
# vers le répertoire d'installation. Le flag --chown=airflow:root garantit que le propriétaire
# des fichiers est l'utilisateur airflow, conforme aux bonnes pratiques de sécurité.
COPY --chown=airflow:root pyproject.toml requirements.txt /opt/reviewpulse/

# Copie du code source. Le projet utilise setuptools avec l'option
# [tool.setuptools.packages.find] where = ["src"], donc le répertoire src doit être placé
# dans /opt/reviewpulse/src/ pour que l'import fonctionne correctement.
COPY --chown=airflow:root src/ /opt/reviewpulse/src/

# Installation des dépendances listées dans requirements.txt (en excluant les lignes '-e .')
# puis installation du package local depuis /opt/reviewpulse. L'option --no-cache-dir évite
# d'encombrer l'image avec le cache pip.
RUN set -eux; \
    grep -v -e '^-e' /opt/reviewpulse/requirements.txt > /tmp/requirements-airflow.txt; \
    pip install --no-cache-dir -r /tmp/requirements-airflow.txt; \
    pip install --no-cache-dir /opt/reviewpulse
