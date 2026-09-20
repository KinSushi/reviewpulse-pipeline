# tests/test_rollback.py
"""Tests unitaires du module reviewpulse.rollback.

Les tests utilisent un faux client Mlflow afin de ne jamais toucher un serveur réel.
Chaque test remplace la fonction interne ``_client`` du module par une instance
de ``FakeClient`` grâce à ``monkeypatch``.
"""

import sys
import builtins

import pytest

from mlflow.exceptions import MlflowException

import reviewpulse.rollback as rollback


class FakeRun:
    def __init__(self, metrics):
        self.data = type("Data", (), {"metrics": metrics})


class FakeModelVersion:
    def __init__(self, version, creation_timestamp, run_id, aliases=None):
        self.version = version
        self.creation_timestamp = creation_timestamp
        self.run_id = run_id
        self.aliases = aliases or []


class FakeClient:
    """Client factice qui enregistre les appels effectués."""

    def __init__(self):
        self.versions = {}          # version_str -> FakeModelVersion
        self.runs = {}              # run_id -> FakeRun
        self.alias_map = {}         # alias -> FakeModelVersion
        self.calls = []             # liste des appels (nom, args…)

    # ------------------------------------------------------------------
    # Méthodes attendues par ``rollback``.
    # ------------------------------------------------------------------
    def search_model_versions(self, filter_string):
        self.calls.append(("search_model_versions", filter_string))
        return list(self.versions.values())

    def get_run(self, run_id):
        self.calls.append(("get_run", run_id))
        return self.runs[run_id]

    def get_model_version_by_alias(self, name, alias):
        self.calls.append(("get_model_version_by_alias", name, alias))
        if alias in self.alias_map:
            return self.alias_map[alias]
        raise MlflowException("Alias not found")

    def get_model_version(self, name, version):
        self.calls.append(("get_model_version", name, version))
        if version in self.versions:
            return self.versions[version]
        raise MlflowException("Version not found")

    def set_registered_model_alias(self, name, alias, version):
        self.calls.append(("set_registered_model_alias", name, alias, version))
        # Met à jour la map d'alias pour refléter le déplacement.
        self.alias_map[alias] = self.versions[version]


@pytest.fixture
def fake_client(monkeypatch):
    """Instancie un FakeClient et le branche dans ``rollback._client``."""
    client = FakeClient()

    # Deux versions de test, avec timestamps différents.
    v1 = FakeModelVersion(
        version="1",
        creation_timestamp=1_000_000,  # plus ancien
        run_id="run1",
        aliases=["old"],
    )
    v2 = FakeModelVersion(
        version="2",
        creation_timestamp=2_000_000,  # plus récent
        run_id="run2",
        aliases=["champion"],
    )
    client.versions["1"] = v1
    client.versions["2"] = v2

    # Runs associés contenant des métriques.
    client.runs["run1"] = FakeRun(metrics={"f1_macro": 0.6, "ecart_train_test": 0.1})
    client.runs["run2"] = FakeRun(metrics={"f1_macro": 0.8, "ecart_train_test": 0.05})

    # Alias « champion » pointe initialement sur la version 2.
    client.alias_map["champion"] = v2

    # Patch la fonction interne pour qu'elle renvoie notre client factice.
    monkeypatch.setattr(rollback, "_client", lambda tracking_uri=None: client)

    return client


def test_versions_disponibles_trie_par_timestamp_descendant(fake_client):
    """Vérifie que les versions sont retournées du plus récent au plus ancien."""
    versions = rollback.versions_disponibles()
    assert len(versions) == 2
    # La première doit être la version « 2 » (timestamp le plus grand).
    assert versions[0]["version"] == "2"
    assert versions[1]["version"] == "1"
    # Vérification des alias et métriques.
    assert "champion" in versions[0]["aliases"]
    assert versions[0]["f1_macro"] == 0.8
    assert versions[1]["f1_macro"] == 0.6


def test_champion_actuel_retourne_version_ou_none(fake_client):
    """Champion actuel renvoie la version associée à l'alias, ou None si absent."""
    # Cas où l'alias existe.
    assert rollback.champion_actuel() == "2"

    # Supprime l'alias pour tester le cas None.
    del fake_client.alias_map["champion"]
    assert rollback.champion_actuel() is None


def test_basculer_deplace_alias_et_renvoie_anciennes_nouvelles_versions(fake_client):
    """Basculer doit appeler le client et retourner les versions concernées."""
    # L'alias champion pointe actuellement sur la version « 2 ».
    result = rollback.basculer("1")
    assert result == {"ancienne": "2", "nouvelle": "1"}

    # Vérifier que le client a bien reçu l'appel de déplacement.
    assert ("set_registered_model_alias", rollback.config.MODEL_NAME, rollback.config.ALIAS_CHAMPION, "1") in fake_client.calls

    # Après le basculement, champion_actuel doit refléter la nouvelle version.
    assert rollback.champion_actuel() == "1"


def test_basculer_vers_version_inexistante_levre_ValueError(fake_client):
    """Une tentative de basculement vers une version absente doit lever ValueError."""
    with pytest.raises(ValueError) as excinfo:
        rollback.basculer("99")
    assert "n'existe pas" in str(excinfo.value)


def test_main_sans_argument_ne_fait_pas_de_bascule_et_retourne_0(fake_client, monkeypatch):
    """Le CLI sans « --vers » n'appelle pas set_registered_model_alias et renvoie 0."""
    # Simuler la ligne de commande « rollback » sans argument.
    monkeypatch.setattr(sys, "argv", ["prog"])
    # Intercepter les appels à print pour éviter du bruit dans les tests.
    monkeypatch.setattr(builtins, "print", lambda *args, **kwargs: None)

    ret = rollback.main()
    assert ret == 0
    # Aucun appel de bascule ne doit être présent.
    assert not any(call[0] == "set_registered_model_alias" for call in fake_client.calls)


def test_main_avec_version_inexistante_retourne_1(fake_client, monkeypatch):
    """Le CLI avec une version invalide doit renvoyer 1."""
    monkeypatch.setattr(sys, "argv", ["prog", "--vers", "42"])
    # Intercepter print comme précédemment.
    monkeypatch.setattr(builtins, "print", lambda *args, **kwargs: None)

    ret = rollback.main()
    assert ret == 1
    # Vérifier que la tentative d'appel a bien eu lieu (pour déclencher l'erreur).
    assert any(call[0] == "get_model_version" for call in fake_client.calls)
