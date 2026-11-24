"""history.py: the plain-text history file for camera sets and press sessions."""
import history


def test_lines_round_trip():
    camera = history.CameraSet("2026-11-24 14:03", "Bicep curl", "right", 12, 2)
    press = history.PressSession("2026-11-24 14:05", "Chest press", 5, 32, "48213")
    assert history.format_entry(camera) == "2026-11-24 14:03 | Bicep curl | right arm | 12 reps | 2 flagged"
    assert history.format_entry(press) == "2026-11-24 14:05 | Chest press | 5 reps | max ROM 32 cm | session 48213"
    assert history.parse_line(history.format_entry(camera)) == camera
    assert history.parse_line(history.format_entry(press)) == press


def test_unknown_or_broken_lines_are_ignored(tmp_path):
    path = tmp_path / "history.txt"
    path.write_text("my own note\n"
                    "2026-11-24 14:03 | Bicep curl | right arm | lots of reps | 0 flagged\n"
                    "2026-11-24 14:04 | Tricep pushdown | left arm | 3 reps | 1 flagged\n")
    entries = history.load(path)
    assert [e.exercise for e in entries] == ["Tricep pushdown"]
    assert history.load(tmp_path / "missing.txt") == []


def test_sets_are_appended_and_loaded_newest_first(tmp_path):
    path = tmp_path / "data" / "history.txt"  # folder is created when needed
    history.save_set(path, "curl", "right", 10, 1)
    history.save_set(path, "pushdown", "left", 8, 0)
    entries = history.load(path)
    assert [(e.exercise, e.arm, e.reps, e.flagged) for e in entries] == [
        ("Tricep pushdown", "left", 8, 0), ("Bicep curl", "right", 10, 1)]


def test_press_session_line_is_updated_in_place(tmp_path):
    path = tmp_path / "history.txt"
    history.save_set(path, "curl", "right", 10, 1)
    history.save_press(path, "48213", "CHEST", 1, 20)
    history.save_press(path, "48213", "CHEST", 5, 32)  # same session: same line
    history.save_press(path, "48213", "SHOULDER", 2, 40)  # other exercise: new line
    history.save_press(path, "777", "CHEST", 3, 25)  # new power-on: new line
    lines = path.read_text().splitlines()
    assert len(lines) == 4
    assert "Bicep curl" in lines[0]  # other lines are left alone
    chest = [e for e in history.load(path) if isinstance(e, history.PressSession)
             and e.session == "48213" and e.exercise == "Chest press"]
    assert len(chest) == 1 and (chest[0].reps, chest[0].rom_cm) == (5, 32)
    assert not (tmp_path / "history.tmp").exists()
