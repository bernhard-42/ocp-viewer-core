# Roadmap

Things worth fixing across the viewer projects that are **not** part of the migration and should not be scheduled against it. Untracked, like `reviews/`.

Moved here from build123d-studio on 2026-08-16, with the memory: they were written during the migration and belong beside it rather than beside an editor.

## cad-viewer-widget:

- `Viewer.normal_len` returns `black_edges` and has no setter

  Found 2026-08-10 by the ocp_tessellate project architect while verifying something else during the item 4 sign-off, and confirmed here by reading the file. Outside item 4's scope, but **item 16 generates the widget's traitlet surface from exactly these properties**, so it is worth fixing before that rather than generating around it.

  `cad_viewer_widget/widget.py:1408-1414`. The `normal_len` property is a copy of the `black_edges` block immediately above it (`:1396-1406`) with the name changed and the body left alone: it returns `self.widget.black_edges`. Two consequences, and the second is the one that makes it worth a roadmap entry rather than a passing fix.

  **Reading `viewer.normal_len` returns the wrong traitlet** - a bool where a float is expected, and specifically whatever `black_edges` happens to be.

  **There is no setter at all**, though the docstring says "Get or set the CadViewerWidget traitlet `normal_len`". The `black_edges` block has its `@black_edges.setter` at `:1404-1406`; the `normal_len` block has nothing, and the next declaration at `:1416` is the `default_edgecolor` property. So `viewer.normal_len = 0.5` does not raise - Python assigns the instance attribute, shadowing the property - and the traitlet is never touched. A caller gets back what they set and sees no error, while the viewer ignores it entirely. That is the silent-failure shape this whole migration exists to reduce.

  Worth checking the neighbouring properties in the same block for the same copy-paste while fixing it; the two found so far were adjacent.

## ocp_tessellate: tessellating a shape invalidates its own cache id

- Fix cache id invalidation

  Measured 2026-08-10 by the ocp_tessellate project architect, while reading the sources for the migration. Independent of the migration: nothing in the ocp-viewer plan depends on it, and fixing it does not unblock anything there.

  **The mechanism.** `create_cache_id` hashes the shape's `BinTools` serialisation. `BRepMesh_IncrementalMesh` mutates the shape it meshes, so after tessellation the same shape serialises to different bytes — the same length, different content, even with `triangles=False, normals=False`. The cache is therefore keyed on something the act of tessellating changes.

  **The observable consequence, and it is backwards from what the design implies.** Showing the _same object_ twice re-tessellates it, because the second lookup hashes the post-mesh bytes and misses. Showing a _fresh identical copy_ hits the cache, because the copy still serialises to the pre-mesh bytes. So the cache helps exactly where it is least needed and misses exactly where a user would expect it to hit — a repeated `show()` of the object they are working on.

  **What a fix has to establish first.** Which bytes `BRepMesh_IncrementalMesh` changes, and whether the cache id can be computed over a representation that meshing does not touch, or must be captured before meshing and carried alongside. Nothing in the source or the CHANGELOG mentions the instability, so it is not known whether it was noticed and accepted or never seen; that is worth settling before choosing a fix, because "accepted deliberately" would point at a different answer than "never observed".

  **Open question carried from the measurement.** Whether the instability is intentional. The architect could not resolve it from the sources.

  See the ocp_tessellate project memory, `reference_caching_and_instancing.md`, for the measurements and the surrounding cache/instancing mechanism.
