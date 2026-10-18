import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest  # noqa: E402

from tetris.main import main, run  # noqa: E402
from tetris.settings import load_settings  # noqa: E402


def test_unknown_key_name_error_names_the_key(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text('{"keys": {"hold": ["nonsense"]}}')
    with pytest.raises(ValueError, match="nonsense"):
        run(settings=load_settings(p), max_frames=1)


def test_main_exits_with_a_message_on_bad_settings(tmp_path, monkeypatch):
    (tmp_path / "settings.json").write_text('{"das": -1}')
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as e:
        main()
    assert "das" in str(e.value)
