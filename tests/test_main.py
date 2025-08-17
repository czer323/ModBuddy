# pylint: disable=redefined-outer-name, unused-argument
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow
from pytestqt.qtbot import QtBot

from modbuddy.main import Modbuddy

if TYPE_CHECKING:
    from modbuddy.ui_protocols import ModBuddyUIProtocol


def has_display() -> bool:
    """
    Returns True if a display is available for GUI tests, False otherwise.
    Works for X11, Wayland, and Windows.
    """
    # Linux/Unix: X11 or Wayland
    if sys.platform.startswith("linux") or sys.platform == "darwin":
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    # Windows: Assume display unless running as a service
    if sys.platform.startswith("win"):
        # Optionally, add more checks for headless Windows environments
        return True
    # Fallback: Try to instantiate a QApplication (optional, can be slow)
    try:
        app = QApplication.instance() or QApplication([])
        app.quit()
    except (RuntimeError, ImportError):
        return False
    return True


@pytest.fixture
def modbuddy_app(qtbot: QtBot, tmp_path: Path, monkeypatch: MonkeyPatch) -> tuple[Modbuddy, QMainWindow]:
    """Initializes the Modbuddy application for testing."""
    monkeypatch.setattr("modbuddy.main.PROJECT_PATH", tmp_path)
    monkeypatch.setattr("modbuddy.main.INPUT_FOLDER", tmp_path / "input")
    monkeypatch.setattr("modbuddy.main.SETTINGS_NAME", tmp_path / "settings.json")
    monkeypatch.setattr("modbuddy.main.GAME_PRESET_FOLDER", tmp_path / "games")
    monkeypatch.setattr("modbuddy.main.MAIN_UI_PATH", tmp_path / "ui/modbuddy.ui")
    monkeypatch.setattr("modbuddy.main.FORM_PATH", tmp_path / "ui/edit_mod_form.ui")

    # Create a dummy UI file to load a real QMainWindow
    ui_file_path = tmp_path / "ui" / "modbuddy.ui"
    ui_file_path.parent.mkdir(exist_ok=True)
    ui_file_path.write_text('<ui version="4.0"><widget class="QMainWindow" name="MainWindow"></widget></ui>')

    loader = QUiLoader()
    window = loader.load(ui_file_path)

    # Add all expected widgets as MagicMocks to the real window
    widgets = [
        "move_up",
        "toggle_mod",
        "edit_mod",
        "move_down",
        "new_mod_button",
        "new_mod_archived_button",
        "clean_modfolder_button",
        "load_profile_button",
        "save_profile_button",
        "duplicate_profile_button",
        "new_game_button",
        "load_game_button",
        "initialize_mod",
        "source_add",
        "source_export",
        "source_check_updates",
        "source_download",
        "exit_button",
        "game_combobox",
        "profile_combobox",
        "file_view",
        "mod_list",
        "source_tableview",
    ]
    for widget_name in widgets:
        setattr(window, widget_name, MagicMock())

    app = Modbuddy(cast("ModBuddyUIProtocol", window))
    qtbot.addWidget(window)

    # Prevent QFileSystemModel from scanning the host filesystem during tests
    # (setRootPath can trigger recursive indexing on some platforms).
    def _stub_set_root_path(_self: object, _path: str) -> str:
        return _path

    monkeypatch.setattr("modbuddy.main.QFileSystemModel.setRootPath", _stub_set_root_path)
    return app, cast("QMainWindow", window)


@pytest.mark.skipif(not has_display(), reason="No display found for GUI tests")
def test_app_initialization(modbuddy_app: tuple[Modbuddy, QMainWindow]) -> None:
    """Tests that the Modbuddy application initializes without crashing."""
    app, window = modbuddy_app
    assert app is not None
    assert window is not None


@pytest.mark.skipif(not has_display(), reason="No display found for GUI tests")
def test_create_new_game(modbuddy_app: tuple[Modbuddy, QMainWindow], tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Tests the create_new_game functionality."""
    app, window = modbuddy_app

    # Avoid invoking heavy filesystem linking during unit tests which can
    # hang on some environments (Windows permission issues or long IO).
    # Replace ModPack.add_mod with a no-op for determinism.
    def _noop_add_mod(_self: object) -> None:
        return None

    monkeypatch.setattr("modbuddy.main.ModPack.add_mod", _noop_add_mod)

    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getExistingDirectory", lambda *_: str(tmp_path / "game_folder"))
    monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getText", lambda *_: ("Test Game", True))
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.information", MagicMock())

    app.create_new_game()

    game_preset_path = tmp_path / "games" / "Test Game.json"
    assert game_preset_path.exists()

    with open(game_preset_path, encoding="utf-8") as f:
        settings = json.load(f)
        assert settings["game_mod_folder"] == str(tmp_path / "game_folder")
        assert "default" in settings["profiles"]
        assert settings["profiles"]["default"][0]["name"] == "Base content"

    backup_folder = tmp_path / "game_folder" / ".mods"
    assert backup_folder.exists()
    assert (backup_folder / "base_content").exists()


@pytest.mark.skipif(not has_display(), reason="No display found for GUI tests")
def test_add_mod(modbuddy_app: tuple[Modbuddy, QMainWindow], tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Tests adding a new mod."""
    app, window = modbuddy_app

    # Setup initial game
    # Ensure ModPack.add_mod is stubbed to avoid heavy IO during game creation
    def _noop_add_mod(_self: object) -> None:
        return None

    monkeypatch.setattr("modbuddy.main.ModPack.add_mod", _noop_add_mod)
    test_create_new_game(modbuddy_app, tmp_path, monkeypatch)

    # Mock dialogs for adding a mod
    mod_path = tmp_path / "MyNewMod"
    mod_path.mkdir()
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getExistingDirectory", lambda *_: str(mod_path))
    monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getText", lambda *_: ("My New Mod", True))

    app.add_mod(mod_path)

    game_preset_path = tmp_path / "games" / "Test Game.json"
    with open(game_preset_path, encoding="utf-8") as f:
        settings = json.load(f)
        assert "My New Mod" in settings["mods"]
        assert settings["mods"]["My New Mod"] == str(mod_path)
        # Check that the new mod is in the default profile
        profile_mods = [mod["name"] for mod in settings["profiles"]["default"]]
        assert "My New Mod" in profile_mods
