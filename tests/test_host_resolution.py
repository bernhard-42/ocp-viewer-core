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


def test_core_owned_names_are_all_exported():
    # __all__ repeats them literally (ruff refuses computed elements), so the
    # two blocks are held together here.
    import ocp_viewer_core

    missing = set(ocp_viewer_core._CORE_OWNED) - set(ocp_viewer_core.__all__)
    assert missing == set()


def test_core_owned_names_resolve_without_choosing():
    result = _fresh(
        "import sys\n"
        "from ocp_viewer_core import Camera, Collapse, ColorMap\n"
        "assert Camera.KEEP is not None and Collapse.LEAVES is not None\n"
        "from ocp_viewer_core.config import Camera as direct\n"
        "assert Camera is direct\n"
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
            "assert ns['set_viewer_config'] is ocp_vscode.set_viewer_config\n"
            "assert ns['Camera'] is ocp_vscode.Camera\n",
        ],
        capture_output=True,
        text=True,
        env={"PATH": "", "PYTHONPATH": ":".join(sys.path), ENV_VAR: "ocp_vscode"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Using viewer ocp_vscode" in result.stdout


# --- the stub, held equal to the runtime -------------------------------------
#
# `__init__.pyi` is what every checker and IDE reads instead of the PEP 562
# machinery; a signature that drifts from the runtime lies in every hover.
# The stub is parsed with ast (importing a .pyi is not a thing) and each
# function's parameters - names, order, kind, and which have defaults - must
# equal the runtime signature of what the name resolves to.

import ast
import inspect
import pathlib

STUB = pathlib.Path(__file__).parent.parent / "ocp_viewer_core" / "__init__.pyi"


def _stub_functions():
    tree = ast.parse(STUB.read_text())
    return {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }


def _stub_params(node):
    args = node.args
    params = [(a.arg, "pos") for a in args.posonlyargs + args.args]
    if args.vararg is not None:
        params.append((args.vararg.arg, "var"))
    params += [(a.arg, "kw") for a in args.kwonlyargs]
    if args.kwarg is not None:
        params.append((args.kwarg.arg, "kwvar"))
    return params


def _runtime_params(func, drop_self):
    kind_map = {
        inspect.Parameter.POSITIONAL_ONLY: "pos",
        inspect.Parameter.POSITIONAL_OR_KEYWORD: "pos",
        inspect.Parameter.VAR_POSITIONAL: "var",
        inspect.Parameter.KEYWORD_ONLY: "kw",
        inspect.Parameter.VAR_KEYWORD: "kwvar",
    }
    params = [
        (p.name, kind_map[p.kind])
        for p in inspect.signature(func).parameters.values()
    ]
    if drop_self and len(params) > 0 and params[0][0] == "self":
        return params[1:]
    return params


def test_stub_signatures_match_the_runtime():
    from ocp_viewer_core.config import Config
    from ocp_viewer_core.show import Viewer

    owners = {name: (Viewer, True) for name in (
        "show", "show_object", "show_objects", "show_all", "show_clear",
        "reset_show", "save_screenshot", "push_object", "remove_object",
    )}
    owners.update({name: (Config, True) for name in (
        "set_defaults", "get_defaults", "get_default", "reset_defaults",
        "set_viewer_config", "combined_config", "workspace_config", "status",
    )})

    stub = _stub_functions()
    mismatches = []
    for name, (owner, drop_self) in owners.items():
        if name not in stub:
            mismatches.append(f"{name}: missing from the stub")
            continue
        expected = _runtime_params(getattr(owner, name), drop_self)
        found = _stub_params(stub[name])
        if found != expected:
            mismatches.append(f"{name}: stub {found} != runtime {expected}")
    assert mismatches == [], "\n".join(mismatches)


def test_stub_covers_the_whole_vocabulary():
    import ocp_viewer_core

    tree = ast.parse(STUB.read_text())
    declared = set(_stub_functions())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            declared |= {alias.asname or alias.name for alias in node.names}
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            declared.add(node.target.id)
    vocabulary = set(ocp_viewer_core.__all__) | set(ocp_viewer_core._HOST_ONLY)
    assert vocabulary - declared == set()


@pytest.mark.skipif(
    importlib.util.find_spec("jupyter_cadquery") is None,
    reason="needs jupyter_cadquery installed",
)
def test_stub_host_only_signatures_match_their_owners():
    import jupyter_cadquery

    from ocp_vscode import comms as vscode_comms

    stub = _stub_functions()
    mismatches = []
    for module, names in (
        (vscode_comms, ("get_port", "set_port")),
        (jupyter_cadquery, (
            "close_viewer", "close_viewers", "get_default_viewer",
            "get_user_defaults", "get_viewer", "open_viewer",
            "save_user_defaults", "set_default_viewer",
        )),
    ):
        for name in names:
            expected = _runtime_params(getattr(module, name), drop_self=False)
            found = _stub_params(stub[name])
            if found != expected:
                mismatches.append(f"{name}: stub {found} != runtime {expected}")
    assert mismatches == [], "\n".join(mismatches)
