---
name: manimgx
description: Create and inspect local ManimGX mathematical teaching animations when changing geometry, quantities or distributions clarify a lesson.
---

# ManimGX

Set a single learning objective, mathematical basis, quantity that changes, fixed conditions and audience. Check the host for an existing authorized ManimGX environment and inspect the installed module's help/examples for its renderer entry point. Use its documented invocation for that environment. Keep scene source and outputs in an intended project asset directory. Use another backend only if the user requests it; a storyboard or static figure can support the explanation when no renderer is available.

Write a short scene and readable specification with class, dimensions, fps, basis, units, time mapping and any random seed. Identify schematic versus computed data. Test important values independently of the animation. For a regression illustration recompute the residual sum of squares at displayed parameter values; distinguish the animated path from an optimizer's actual iterations. Verify output against the specification.

For a compatible installed environment, run its Python from the asset workspace. Replace the example file and class with the authored scene.

```console
python -m manimgx inspect scene.py Projection
python -m manimgx render scene.py Projection -o projection.mp4 -r 1280x720 --fps 30
```

Inspect reported layout issues before rendering. Keep render writes within the requested artifact directory and use a trusted scene. If the installed CLI differs, use its own help to choose the equivalent arguments.

Render and inspect the first frame, every conceptual transition and end frame. Check labels, crops, contrast, scales, equations and synchronized state. Fix visible or mathematical errors and re-render. Deliver the actual inspected movie and poster or frames using relative vault embeds, preserving the source, explicit backend and any limitation in project assets. If rendering fails, record the error and teach with a labelled static fallback. A delivered animation carries zero assessment credit.
