# pylint: disable=redefined-outer-name, unused-argument
import pytest
from unittest.mock import MagicMock
from PySide6.QtUiTools import QUiLoader

from modbuddy.main import Modbuddy

@pytest.fixture
def modbuddy_app(qtbot, tmp_path, monkeypatch):
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
    WIDGETS = [
        "move_up", "toggle_mod", "edit_mod", "move_down", "new_mod_button",
        "new_mod_archived_button", "clean_modfolder_button", "load_profile_button",
        "save_profile_button", "duplicate_profile_button", "new_game_button",
        "load_game_button", "initialize_mod", "source_add", "source_export",
        "source_check_updates", "source_download", "exit_button", "game_combobox",
        "profile_combobox", "file_view", "mod_list", "source_tableview"
    ]
    for widget_name in WIDGETS:
        setattr(window, widget_name, MagicMock())

    app = Modbuddy(window)
    qtbot.addWidget(window)
    return app, window

def test_app_initialization(modbuddy_app):
    """Tests that the Modbuddy application initializes without crashing."""
    app, window = modbuddy_app
    assert app is not None
    assert window is not None

def test_create_new_game(modbuddy_app, tmp_path, monkeypatch):
    """Tests the create_new_game functionality."""
    app, window = modbuddy_app

    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getExistingDirectory", lambda *args, **kwargs: str(tmp_path / "game_folder"))
    monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getText", lambda *args, **kwargs: ("Test Game", True))
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.information", MagicMock())

    app.create_new_game()

    game_preset_path = tmp_path / "games" / "Test Game.json"
    assert game_preset_path.exists()

    with open(game_preset_path, "r") as f:
        settings = json.load(f)
        assert settings["game_mod_folder"] == str(tmp_path / "game_folder")
        assert "default" in settings["profiles"]
        assert settings["profiles"]["default"][0]["name"] == "Base content"

    backup_folder = tmp_path / "game_folder" / ".mods"
    assert backup_folder.exists()
    assert (backup_folder / "base_content").exists()

def test_add_mod(modbuddy_app, tmp_path, monkeypatch):
    """Tests adding a new mod."""
    app, window = modbuddy_app

    # Setup initial game
    test_create_new_game(modbuddy_app, tmp_path, monkeypatch)

    # Mock dialogs for adding a mod
    mod_path = tmp_path / "MyNewMod"
    mod_path.mkdir()
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getExistingDirectory", lambda *args, **kwargs: str(mod_path))
    monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getText", lambda *args, **kwargs: ("My New Mod", True))

    app.add_mod(mod_path)

    game_preset_path = tmp_path / "games" / "Test Game.json"
    with open(game_preset_path, "r") as f:
        settings = json.load(f)
        assert "My New Mod" in settings["mods"]
        assert settings["mods"]["My New Mod"] == str(mod_path)
        # Check that the new mod is in the default profile
        profile_mods = [mod["name"] for mod in settings["profiles"]["default"]]
        assert "My New Mod" in profile_mods
