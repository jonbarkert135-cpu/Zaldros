"""The Settings tree must stay navigable, honest and free of Windows-only rows."""

from zaldros_shell import settingspages


def _tree():
    return settingspages.to_variant(settingspages.build())


def test_every_link_points_at_a_real_page():
    tree = _tree()
    dangling = [(pid, entry["title"], entry["page"])
                for pid, page in tree.items()
                for entry in page["entries"]
                if entry["page"] and entry["page"] not in tree]
    assert not dangling, f"Settings rows lead nowhere: {dangling}"


def test_every_nested_page_is_reachable_from_the_rail():
    tree = _tree()
    seen, queue = set(), list(settingspages.RAIL)
    while queue:
        pid = queue.pop()
        if pid in seen:
            continue
        seen.add(pid)
        queue.extend(entry["page"] for entry in tree[pid]["entries"] if entry["page"])
    assert set(tree) == seen, f"unreachable Settings pages: {sorted(set(tree) - seen)}"


def test_windows_only_rows_are_absent():
    """Activation, OneDrive and Microsoft billing have no counterpart on Raven (2026-08-26)."""
    text = " ".join(entry["title"] + entry["subtitle"]
                    for page in _tree().values() for entry in page["entries"])
    for phrase in ("Активация", "OneDrive", "Подписки", "Варианты оплаты", "Журнал заказов",
                   "Windows"):
        assert phrase not in text, f"Windows-only row survived: {phrase}"


def test_help_points_at_the_project_tracker():
    assert settingspages.HELP_URL.startswith("https://github.com/")
