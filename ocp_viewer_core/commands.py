import os as _os

if (
    _os.environ.get("VSCODE_NONCE") is not None
    or _os.environ.get("VSCODE_CWD") is not None
):
    print("using ocp_vscode")
    from ocp_vscode import *  # pyright: ignore[reportMissingImports]

elif _os.environ.get("JUPYTER_CADQUERY_API_KEY") is not None:
    print("using jupyter_cadquery")
    from jupyter_cadquery import *  # pyright: ignore[reportMissingImports]

elif _os.environ.get("OCP_VIEWER_HOST") == "build123d_studio":
    print("using build123d_studio")
    from build123d_studio import *  # pyright: ignore[reportMissingImports] # ty:ignore[unresolved-import]

else:  # fall back to "ocp_viewer":
    print("using ocp_viewer")
    from ocp_viewer import *  # pyright: ignore[reportMissingImports]
