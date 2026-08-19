"""Which host the universal import means, and what it must never do on the way.

`host.resolve` is pure - the installed list and the environment variable's
value come in as arguments - so the decision matrix is tested with no host
packages and no prompt. The side-effect tests run in a subprocess, because
what they assert is a property of a *fresh* process: a bare import, a failed
attribute, and completion must all leave the host unchosen.
"""

import importlib.util
import subprocess
import sys

import pytest

from ocp_viewer_core.host import ENV_VAR, HOSTS, resolve

# --- the decision matrix, pure ---------------------------------------------


def test_env_var_wins_over_everything():
    assert resolve(["ocp_vscode", "ocp_viewer"], "ocp_viewer") == "ocp_viewer"


def test_env_var_naming_a_non_host_raises():
    with pytest.raises(ImportError, match="not a viewer host"):
        resolve(["ocp_vscode"], "flask")


def test_env_var_naming_an_uninstalled_host_raises():
    with pytest.raises(ImportError, match="not installed"):
        resolve(["ocp_vscode"], "jupyter_cadquery")


def test_no_host_installed_raises():
    with pytest.raises(ImportError, match="No viewer host is installed"):
        resolve([], None)


def test_exactly_one_installed_is_meant():
    assert resolve(["jupyter_cadquery"], None) == "jupyter_cadquery"


def test_several_installed_means_ask():
    # None is the one outcome the caller must take to `ask` - resolution
    # never picks among several by itself.
    assert resolve(["ocp_vscode", "ocp_viewer"], None) is None


def test_every_host_name_resolves_when_alone():
    for name in HOSTS:
        assert resolve([name], None) == name


# --- the properties a fresh process must have ------------------------------


def _fresh(code):
    """Run `code` in a fresh interpreter with no host named."""
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={"PATH": "", "PYTHONPATH": ":".join(sys.path)},
        check=False,
    )


def test_bare_import_chooses_nothing():
    result = _fresh(
        "import ocp_viewer_core, sys\n"
        "assert 'ocp_viewer_core.host' not in sys.modules\n"
    )
    assert result.returncode == 0, result.stderr


def test_unknown_attribute_raises_without_choosing():
    result = _fresh(
        "import ocp_viewer_core, sys\n"
        "try:\n"
        "    ocp_viewer_core.nonsense\n"
        "except AttributeError:\n"
        "    pass\n"
        "else:\n"
        "    raise SystemExit('AttributeError expected')\n"
        "assert 'ocp_viewer_core.host' not in sys.modules\n"
    )
    assert result.returncode == 0, result.stderr


def test_completion_chooses_nothing():
    result = _fresh(
        "import ocp_viewer_core, sys\n"
        "names = dir(ocp_viewer_core)\n"
        "assert 'show' in names and 'set_viewer_config' in names\n"
        "assert 'ocp_viewer_core.host' not in sys.modules\n"
    )
    assert result.returncode == 0, result.stderr


# --- end to end, when a host is actually present ---------------------------


@pytest.mark.skipif(
    importlib.util.find_spec("ocp_vscode") is None,
    reason="needs ocp_vscode installed",
)
def test_named_host_resolves_to_its_own_bound_methods():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from ocp_viewer_core import show, show_all as sa\n"
            "ns = {}\n"
            "exec('from ocp_viewer_core import *', ns)\n"
            "import ocp_vscode\n"
            "assert show is ocp_vscode.show\n"
            "assert sa is ocp_vscode.show_all\n"
            "assert ns['set_viewer_config'] is ocp_vscode.set_viewer_config\n",
        ],
        capture_output=True,
        text=True,
        env={"PATH": "", "PYTHONPATH": ":".join(sys.path), ENV_VAR: "ocp_vscode"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Using viewer ocp_vscode" in result.stdout
