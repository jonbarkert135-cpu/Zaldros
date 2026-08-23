# Visual similarity score vs Windows 11

Scores are 0–5 and are **a design metric only** — a high score never means the component works
(VISUAL FOUNDATION §15). Method: render the component (`docs/evidence/`), compare against the
reference screenshot in `assets/refs/win11_start_reference.png` on geometry, spacing, typography,
colour, iconography, shadow and motion.

| Component | Geometry | Spacing | Typography | Colour | Icons | Motion | Score | Functional status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop | 4 | 4 | 4 | 4 | 2 | 3 | **3.5** | PROTOTYPE — no icon interaction, no wallpaper engine |
| Taskbar | 5 | 4 | 4 | 4 | 3 | 4 | **4.0** | PROTOTYPE — real clock and process state, not a layer-shell panel |
| Start | 5 | 4 | 4 | 4 | 3 | 4 | **4.0** | PARTIAL — real app list and launching; no search results, no Recommended |
| Search | 3 | 3 | 4 | 4 | 3 | 1 | **3.0** | MISSING — field only, no index |
| System tray | 4 | 4 | 4 | 4 | 3 | 3 | **3.7** | PARTIAL — real presence detection, no per-icon backends |
| Quick settings | 4 | 4 | 4 | 4 | 3 | 3 | **3.7** | PARTIAL — real readouts, toggles not wired |
| Window decorations | 4 | 4 | 4 | 4 | 4 | 2 | **3.7** | PROTOTYPE — design only; KWin will draw the real ones |
| Context menus | 4 | 4 | 4 | 4 | 3 | 4 | **3.8** | PROTOTYPE — no actions behind the items |
| Explorer | 2 | 2 | 3 | 3 | 2 | 0 | **2.0** | MISSING — sidebar mock inside the window demo |
| Settings | 0 | 0 | 0 | 0 | 0 | 0 | **0.0** | MISSING |
| Notifications | 0 | 0 | 0 | 0 | 0 | 0 | **0.0** | MISSING |

**Weakest links:** iconography (own strokes; the licensed Fluent set is not vendered yet), motion
(no live blur, no window animations), and everything that needs a compositor.

**Deliberate deviations from Windows 11:**
1. The Start mark is three stacked slabs, not a four-pane logo — that shape is a Microsoft trademark.
2. Panels use a solid base under the acrylic tint; live blur arrives with KWin.
3. Empty regions state that a service is missing rather than showing sample content.
