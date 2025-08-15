#!/usr/bin/env python3  # pylint: disable=unused-import
import json
import sys
from datetime import UTC, datetime
from os import path as ospath
from pathlib import Path
from typing import Any, cast

import patoolib
from PySide6.QtCore import QCoreApplication, QFile, QIODevice, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFileSystemModel,
    QInputDialog,
    QLineEdit,
    QMainWindow,  # pylint: disable=unused-import
    QMessageBox,
    QWidget,  # pylint: disable=unused-import
)

import models
import modpack
import sources
from fomod import FomodParser
from ui_protocols import EditModDialogProtocol, ModBuddyUIProtocol

PROJECT_PATH = Path(ospath.dirname(sys.argv[0])).resolve()
INPUT_FOLDER = PROJECT_PATH / Path("input")
SETTINGS_NAME = PROJECT_PATH / "settings.json"
GAME_PRESET_FOLDER = PROJECT_PATH / "games"
PRESET_FILE_NAME = "game_setting.json"
MAIN_UI_PATH = PROJECT_PATH / "ui" / "modbuddy.ui"
FORM_PATH = PROJECT_PATH / "ui" / "edit_mod_form.ui"

ENABLED_COLUMN = 0
MODNAME_COLUMN = 1
PATH_COLUMN = 2


class Modbuddy:
    game_setting: dict[str, Any]
    current_profile: dict[str, Any]
    settings: dict[str, Any]
    is_dirty: bool
    target_preset_path: Path
    modmodel: models.ModModel | None
    sourcemodel: models.SourceModel | None
    # The UI is typed as ModBuddyUIProtocol to inform mypy of all expected attributes
    ui: ModBuddyUIProtocol

    def __init__(self, ui: ModBuddyUIProtocol) -> None:
        self.ui = ui
        self.fomod: FomodParser | None = None
        self.sources = None

        self.init_settings()
        # Initialize some components
        self.fs_mod = QFileSystemModel()
        # Connect buttons with error handling for missing UI attributes
        button_map = [
            ("move_up", self.move_row_up),
            ("toggle_mod", self.toggle_targeted_mod),
            ("edit_mod", self.edit_targeted_mod),
            ("move_down", self.move_row_down),
            ("new_mod_button", self.install_new_mod),
            ("new_mod_archived_button", self.install_new_archived_mod),
            ("clean_modfolder_button", self.clean_target_modfolder),
            ("load_profile_button", self.load_current_profile),
            ("save_profile_button", self.write_preset_to_config),
            ("duplicate_profile_button", self.create_new_mod_table_config),
            ("new_game_button", self.create_new_game),
            ("load_game_button", self.load_targeted_game),
            ("initialize_mod", self.letsgo_mydudes),
            ("source_add", self.add_source),
            ("source_export", self.export_source),
            ("source_check_updates", self.update_sources),
            ("source_download", self.download_sources),
            ("exit_button", self.exit_app),
        ]
        for attr, handler in button_map:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(handler)
            else:
                print(f"Warning: UI missing attribute '{attr}'")

        self.update_game_combobox()
        self.init_tablewidget()
        self.retrieve_last_activity()
        self.init_sourcewidget()  # No argument, matches method signature
        self.update_fileview()

    def init_settings(self) -> None:
        """Initial setup for mod buddy."""
        GAME_PRESET_FOLDER.mkdir(exist_ok=True)
        try:
            self.settings = json.loads(Path(SETTINGS_NAME).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {}
        self.game_setting = {}

    @staticmethod
    def recursive_rmdir(delpath: Path) -> None:
        for subpath in sorted(delpath.glob("**/*"), reverse=True):
            if subpath.is_dir():
                subpath.rmdir()
            else:
                subpath.unlink()

    def exit_app(self) -> None:
        """Exit the application."""
        QApplication.quit()

    def get_current_game(self) -> str:
        """Retrieve what game is currently active."""
        return self.ui.game_combobox.currentText()

    def get_current_profile(self) -> str:
        """Retrieve what profile is currently active."""
        return self.ui.profile_combobox.currentText()

    def update_game_combobox(self) -> None:
        """Update information inside the game combobox."""
        self.ui.game_combobox.clear()
        current_game = self.settings.get("lastactivity", {}).get("game")
        index = None
        for i, x in enumerate(GAME_PRESET_FOLDER.glob("*.json")):
            self.ui.game_combobox.addItem(x.stem)
            if current_game == x.stem:
                index = i
        if index:
            self.ui.game_combobox.setCurrentIndex(index)

    def update_profile_combobox(self) -> None:
        """Update information inside the preset combobox."""
        self.ui.profile_combobox.clear()
        current_game = self.settings.get("lastactivity", {}).get("profile")
        index = None
        profiles = self.game_setting.get("profiles", {})
        for i, x in enumerate(profiles):
            self.ui.profile_combobox.addItem(x)
            if current_game == x:
                index = i
        if index:
            self.ui.profile_combobox.setCurrentIndex(index)

    def update_last_activity(self, game: str = "", profile: str = "") -> None:
        """Update the current last_activity and store it.

        :param game: Current game, defaults to ""
        :type game: str, optional
        :param profile: Current preset inside game, defaults to ""
        :type profile: str, optional
        """
        last_activity = {
            "game": game or self.get_current_game(),
            "profile": profile or self.get_current_profile(),
        }
        self.settings["lastactivity"] = last_activity
        # print(last_activity)
        Path(SETTINGS_NAME).write_text(
            json.dumps(self.settings, indent=4), encoding="utf-8"
        )

    def retrieve_last_activity(self) -> None:
        """Update the UI with contents from lastactivity."""
        last = self.settings.get("lastactivity")
        if last:
            game = last.get("game")
            profile = last.get("profile")
            self.load_game(game)
            self.load_profile(profile)

    def create_new_mod_table_config(self) -> None:
        """Create a new mod table configuration.

        Take the current mod setup presented,
        create a new mod preset and save it to the settings
        """
        preset_name, ok = QInputDialog.getText(
            cast("QMainWindow", self.ui),
            "",
            "Preset name:",
            QLineEdit.EchoMode.Normal,
            self.get_current_profile(),
        )
        if not ok:
            return

        config = self.game_setting["profiles"].get(self.get_current_profile())
        self.game_setting["profiles"][preset_name] = config

        self.write_preset_to_config()
        self.update_last_activity(profile=preset_name)
        self.load_profile(preset_name)
        self.update_profile_combobox()

    def write_preset_to_config(self) -> None:
        """Update the current mod setup to its respective profile."""
        Path(self.target_preset_path).write_text(
            json.dumps(self.game_setting, indent=4), encoding="utf-8"
        )

    def load_profile(self, target_profile: str) -> None:
        """Initialize a chosen preset to the mod table.

        :param target_profile: A profile that exists inside profiles in 'game_setting.json'
        :type target_profile: str
        """
        self.current_profile = self.game_setting["profiles"].get(target_profile)
        self.init_tablewidget(target_profile)
        self.init_sourcewidget()  # No argument, matches method signature

    def load_current_profile(self) -> None:
        """Initialize the current preset (Chosen in GUI)."""
        preset = self.get_current_profile()
        self.load_profile(preset)
        self.update_last_activity()

    def update_fileview(self) -> None:
        """Update the file explorer with current game settings."""
        mod_path = self.game_setting.get("game_mod_folder")
        if not mod_path:
            return
        path = str(Path(mod_path).parent)

        self.fs_mod.setRootPath(path)
        self.ui.file_view.setModel(self.fs_mod)
        self.ui.file_view.setRootIndex(self.fs_mod.index(path))
        self.ui.file_view.expand(self.fs_mod.index(mod_path))

    def set_dirty_status(self, dirty: bool) -> None:
        """Update functionality on buttons with regards to modified contents."""
        self.is_dirty = dirty
        self.ui.initialize_mod.setEnabled(self.is_dirty)
        self.ui.save_profile_button.setEnabled(self.is_dirty)

    def create_new_game(self) -> None:
        """Start a wizard to create a new game."""
        game_mod_folder_str = QFileDialog.getExistingDirectory(
            cast("QMainWindow", self.ui), "Get mod folder"
        )
        if not game_mod_folder_str:
            return
        game_mod_folder = Path(game_mod_folder_str)
        game_preset_name, ok = QInputDialog.getText(
            cast("QMainWindow", self.ui),
            "",
            "Game preset name:",
            QLineEdit.EchoMode.Normal,
            game_mod_folder.parent.stem,
        )
        if ok:
            QMessageBox.information(
                cast("QMainWindow", self.ui), "Done", "Game is set up and ready to go!"
            )

        game_folder = game_mod_folder.parent
        backup_mod_folder = game_folder / ".mods"
        import contextlib

        with contextlib.suppress(FileExistsError):
            backup_mod_folder.mkdir()

        # Create a backup of the original files, will be used for modding
        initial_mod_content_folder = backup_mod_folder / "base_content"
        initial_mod_content_folder.mkdir()

        x = modpack.ModPack(
            game_mod_folder, initial_mod_content_folder, case_sensitive=True
        )
        x.add_mod()

        base_content_name = "Base content"
        preset = {
            "default_mod_folder": str(backup_mod_folder.resolve()),
            "game_mod_folder": str(game_mod_folder.resolve()),
            "profiles": {"default": [{"enabled": True, "name": base_content_name}]},
            "sources": [],
            "mods": {base_content_name: str(initial_mod_content_folder.resolve())},
        }
        Path(GAME_PRESET_FOLDER / f"{game_preset_name}.json").write_text(
            json.dumps(preset, indent=4), encoding="utf-8"
        )
        self.update_last_activity(game_preset_name, "default")
        self.update_game_combobox()
        self.load_game(game_preset_name)

    def load_game(self, target_preset: str) -> None:
        """Load a new game and its presets.

        :Param target_preset: Name of game (set when creating a new game)
        :type target_preset: str
        """

    def load_targeted_game(self) -> None:
        """Load the game selected in GUI."""
        target_game = self.get_current_game()
        self.load_game(target_game)
        self.update_last_activity()

    def install_new_mod(self) -> None:
        """Install a new mod already extracted somewhere."""
        self.add_mod(Path(self.game_setting.get("default_mod_folder") or "."))

    def install_new_archived_mod(self) -> None:
        """Install a new mod from an archive."""
        archives = QFileDialog.getOpenFileNames(
            cast("QMainWindow", self.ui),
            "Select archives to be installed",
            str(Path.home()),
            "Supported archives (*.7z *.cb7 *.bz2 *.cab *.Z *.cpio *.deb *.dms *.flac *.gz *.iso *.lrz *.lha *.lzh *.lz *.lzma *.lzo *.rpm *.rar *.cbr *.rz *.shn *.tar *.cbt *.xz *.zip *.jar *.cbz *.zoo)",
        )
        if not archives:
            return
        default_mod_folder = self.game_setting.get("default_mod_folder")
        if not default_mod_folder:
            QMessageBox.warning(
                cast("QMainWindow", self.ui),
                "",
                (
                    "Sorry, but your settings doesn't have "
                    "a default destination for mods. Is it an old config?"
                ),
            )

        assert type(default_mod_folder) is str
        for archive in archives[0]:
            try:
                folder_name = Path(archive).stem
                target_folder = Path(default_mod_folder) / folder_name
                patoolib.extract_archive(
                    archive, outdir=str(target_folder), interactive=False
                )
            except OSError as e:
                QMessageBox.warning(
                    cast("QMainWindow", self.ui),
                    "",
                    f"An unexpected error orrured, {e}",
                )
            else:
                if Path.exists(target_folder / "fomod"):
                    x = QMessageBox.question(
                        cast("QMainWindow", self.ui),
                        "",
                        (
                            "Fomod folder detected. Do you want to parse it as a fomod-mod?"
                        ),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if x == QMessageBox.StandardButton.Yes:
                        self.begin_fomod_parsing(target_folder)
                        return
                self.add_mod(target_folder)

    def add_mod(self, folder_path: Path) -> None:
        """Import a mod to the current game.

        :param folder_path: A path representing the 'root' of the mod folder
        :type folder_path: Path
        """
        folder_choice = QFileDialog.getExistingDirectory(
            cast("QMainWindow", self.ui),
            "Choose subfolder",
            str(folder_path),
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not folder_choice:
            return

        folder = Path(folder_choice)
        if Path.exists(folder / "fomod"):
            x = QMessageBox.question(
                cast("QMainWindow", self.ui),
                "",
                ("Fomod folder detected. Do you want to parse it as a fomod-mod?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if x == QMessageBox.StandardButton.Yes:
                self.begin_fomod_parsing(folder)
        else:
            folder_name = Path(folder_path).stem
            text, ok = QInputDialog.getText(
                cast("QMainWindow", self.ui),
                "Get mod name",
                "Name input of mod:",
                QLineEdit.EchoMode.Normal,
                folder_name,
            )
            if ok:
                self.add_row_to_mods(name=text, path=Path(folder))

    def add_row_to_mods(self, name: str, path: Path, modtype: str = "basic") -> None:
        """Add a given mod to the current game.

        :param name: unique name of the mod
        :type name: str
        :param path: A path representing the root of the folder, defaults to Path
        :type path: Path, optional
        :param modtype: How is this mod installed?
        :type modtype: str
        """
        self.game_setting["mods"][name] = str(path)
        for mod_profile in self.game_setting["profiles"].values():
            mod_profile.append({"name": name, "enabled": True, "type": modtype})
        # Emit layoutChanged only once after all profiles are updated
        if self.modmodel is not None and hasattr(self.modmodel, "layoutChanged"):
            self.modmodel.layoutChanged.emit()
        self.set_dirty_status(True)

    def add_row_to_mods_fomod_style(
        self, name: str, path: Path, fomod_results: dict
    ) -> None:
        """Add a given mod to the current game with fomod-related presets.

        :param name: unique name of the mod
        :type name: str
        :param path: A path representing the root of the folder, defaults to Path
        :type path: Path, optional
        """
        self.game_setting["mods"][name] = str(path)
        for mod_profile in self.game_setting["profiles"].values():
            mod_profile.append(
                {
                    "name": name,
                    "enabled": True,
                    "type": "fomod",
                    "options": fomod_results,
                }
            )
        # Emit layoutChanged only once after all profiles are updated
        if self.modmodel is not None and hasattr(self.modmodel, "layoutChanged"):
            self.modmodel.layoutChanged.emit()
        self.set_dirty_status(True)

    def get_mod_list_row(self) -> int:
        return self.ui.mod_list.selectionModel().selectedRows()[0].row()

    def move_row_up(self) -> None:
        row = self.get_mod_list_row()
        if row > 0:
            self._move_row(row, row - 1)

    def move_row_down(self) -> None:
        import contextlib

        row = self.get_mod_list_row()
        with contextlib.suppress(IndexError):
            self._move_row(row, row + 1)

    def _move_row(self, index_a: int, index_b: int) -> None:
        """Switch an entry between two rows in the mod list."""
        game_profile = self.game_setting["profiles"].get(self.get_current_profile())
        game_profile[index_a], game_profile[index_b] = (
            game_profile[index_b],
            game_profile[index_a],
        )
        if self.modmodel is not None and hasattr(self.modmodel, "layoutChanged"):
            self.modmodel.layoutChanged.emit()
        self.set_dirty_status(True)

    def edit_targeted_mod(self) -> None:
        """Edit selected mod."""
        row = self.get_mod_list_row()
        try:
            game_profile = self.game_setting["profiles"].get(self.get_current_profile())
            mod_settings = self.game_setting["mods"]
            # targeted_mod = mod_settings.get(game_profile[row]["name"])  # Unused variable removed

            old_path = mod_settings.get(game_profile[row]["name"])
            old_name = game_profile[row]["name"]
            loader = QUiLoader()
            dialog_raw = loader.load(FORM_PATH, cast("QMainWindow", self.ui))

            dialog: EditModDialogProtocol = cast("EditModDialogProtocol", dialog_raw)
            dialog.nameLineEdit.insert(game_profile[row]["name"])
            dialog.enabledCheckBox.setChecked(game_profile[row]["enabled"])
            dialog.pathLineEdit.insert(old_path)
            dialog.show()
            if dialog.exec_():
                self.set_dirty_status(True)
                new_path = dialog.pathLineEdit.text()
                new_name = dialog.nameLineEdit.text()
                if new_name != old_name:
                    # Update all profiles with new name
                    mod_settings[new_name] = mod_settings.pop(old_name)
                    for x in self.game_setting["profiles"].values():
                        for y in x:
                            if y.get("name") == old_name:
                                y["name"] = new_name

                if new_path != old_path:
                    mod_settings[new_name] = new_path

                game_profile[row]["enabled"] = bool(dialog.enabledCheckBox.checkState())
        except IndexError:
            pass

    def toggle_targeted_mod(self) -> None:
        """Toggle selected mod."""
        row = self.get_mod_list_row()
        try:
            game_profile = self.game_setting["profiles"].get(self.get_current_profile())
            game_profile[row]["enabled"] = not game_profile[row]["enabled"]
            if self.modmodel is not None and hasattr(self.modmodel, "layoutChanged"):
                self.modmodel.layoutChanged.emit()
            self.set_dirty_status(True)
        except IndexError:
            pass

    def init_tablewidget(self, profile: str = "") -> None:
        """Initialize the table with mods.

        :param profile: Profile name, defaults to ""
        :type profile: str, optional
        """
        if not profile:
            profile = self.get_current_profile()
        self.modmodel = models.ModModel(settings=self.game_setting, profile=profile)
        self.ui.mod_list.setModel(self.modmodel)
        self.ui.mod_list.resizeColumnToContents(MODNAME_COLUMN)

    def init_sourcewidget(self) -> None:
        """Initialize the table with sources."""
        sources_list = self.game_setting.get("sources")
        if sources_list is None:
            sources_list = []
        self.sourcemodel = models.SourceModel(sources=sources_list)
        self.ui.source_tableview.setModel(self.sourcemodel)

    def update_sources(self) -> None:
        """Update sources."""
        # Pull requests are welcome
        x = QMessageBox.question(
            cast("QMainWindow", self.ui),
            "",
            ("Mod buddy can freeze a bit while this runs. Do you want to proceed?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if x != QMessageBox.StandardButton.Yes:
            return
        sources_list = self.game_setting.get("sources") or []
        total_length = len(sources_list)
        for i, source in enumerate(sources_list):
            sourceclass = sources.get_class_classifier(source["url"])
            test = sourceclass.from_dict(source)
            test.update()
            source.update(test.to_dict())
            print(f"{i + 1}/{total_length} - Updated metadata for {test.title}")
        if self.sourcemodel is not None and hasattr(self.sourcemodel, "layoutChanged"):
            self.sourcemodel.layoutChanged.emit()
        self.write_preset_to_config()
        QMessageBox.information(
            cast("QMainWindow", self.ui), "Done", "Mod table are up to date"
        )

    def _assert_mods_is_added_from_source(self, mod: "sources.SourceModdb") -> None:
        """Assert that the subfolders from a mod exists. If they do not exist, create them as new mods."""
        default_mod_folder = Path(self.game_setting.get("default_mod_folder") or "mods")
        mod_settings = self.game_setting["mods"]
        all_mods = mod_settings.values()
        for subfolder in mod.folders:
            potentialmod = f"{default_mod_folder / mod.foldername / subfolder}"
            print(f"{potentialmod=}")
            if potentialmod not in all_mods:
                print("thisSomeGOODshit.mpeg")
                self.add_row_to_mods(
                    name=f"{mod.foldername}/{subfolder}",
                    path=Path(potentialmod),
                    modtype="source",
                )
            else:
                print("imgoodthx.jpeg")

    def download_sources(self) -> None:
        """Download outdated sources."""
        downloaded_something = False
        sources_list = self.game_setting.get("sources") or []
        total_length = len(sources_list)
        default_mod_folder = self.game_setting.get("default_mod_folder") or "mods"
        downloaded_something = False
        for i, source in enumerate(sources_list):
            source_object = sources.get_class_classifier(source["url"]).from_dict(
                source
            )
            print(
                f"{source_object.title} {source_object.installed} - {source_object.updated}"
            )
            if source_object.updated:
                last_updated = max(source_object.added, source_object.updated)
            else:
                last_updated = source_object.added
            if source_object.installed.timestamp() <= last_updated.timestamp():
                dl_path = Path(default_mod_folder) / source_object.foldername
                dl_path.mkdir(exist_ok=True)
                downloaded_file = dl_path / source_object.filename
                if not source_object.check_if_file_exists(downloaded_file):
                    print(f"Downloading {source_object.download_url=} to {dl_path=}")
                    source_object.download_file(dl_path)
                try:
                    print(f"{i + 1}/{total_length} - {downloaded_file=}")
                    patoolib.extract_archive(
                        str(downloaded_file), outdir=str(dl_path), interactive=False
                    )
                    if isinstance(source_object, sources.SourceGitHub):
                        git_downloaded_root = [
                            p for p in dl_path.iterdir() if p.is_dir()
                        ]
                        if len(git_downloaded_root) == 1:
                            git_folder = git_downloaded_root[0]
                            git_folder.rename(dl_path / source_object.foldername)
                    source_object.installed = datetime.now(UTC)
                    if isinstance(source_object, sources.SourceModdb):
                        self._assert_mods_is_added_from_source(source_object)
                    source.update(source_object.to_dict())
                    print(f"{i + 1}/{total_length} - finished")
                    downloaded_something = True
                except (FileNotFoundError, ValueError, TypeError) as e:
                    print(f"Error extracting or processing source {source}: {e}")
            else:
                print(f"{i + 1}/{total_length} - No need to download")
        if downloaded_something:
            QMessageBox.information(
                cast("QMainWindow", self.ui), "Done", "Sources are downloaded"
            )
        else:
            QMessageBox.warning(
                cast("QMainWindow", self.ui),
                "Nothing done",
                "No mods were considered outdated.\nHave you checked for sources lately?",
            )
        self.write_preset_to_config()

    def add_source(self) -> None:
        content, ok = QInputDialog.getMultiLineText(
            cast("QMainWindow", self.ui),
            "Gibe urls pls",
            "separate urls by newline, and subfolders by semicolon",
            "URL;folder1;folder2",
        )
        if not ok:
            return
        sources_list = self.game_setting.get("sources")
        if sources_list is None:
            sources_list = []
            self.game_setting["sources"] = sources_list
        added_count = 0
        errors = []
        for urlgroup in content.splitlines():
            urlgroup = urlgroup.strip()
            if not urlgroup:
                continue
            try:
                if ";" in urlgroup:
                    url, folders = urlgroup.split(";", 1)
                    sourceclass = sources.get_class_classifier(url)
                    tmp_source = sourceclass.from_url(url, folders.split(";"))
                else:
                    sourceclass = sources.get_class_classifier(urlgroup)
                    tmp_source = sourceclass.from_url(urlgroup)
                sources_list.append(tmp_source.to_dict())
                print(f"Added {tmp_source.title}")
                added_count += 1
            except ValueError as e:
                print(f"ValueError adding source from '{urlgroup}': {e}")
                errors.append(urlgroup)
            except AttributeError as e:
                print(f"AttributeError adding source from '{urlgroup}': {e}")
                errors.append(urlgroup)
        if added_count > 0:
            if self.sourcemodel is not None:
                self.sourcemodel.layoutChanged.emit()
            self.write_preset_to_config()
        else:
            print("No sources were added.")
        if errors:
            print(f"Errors occurred for: {errors}")

    def export_source(self) -> None:
        """Export current configuration as a text file"""
        lines = []
        for src in self.game_setting.get("sources") or []:
            folder_part = ""
            if src.get("folders"):
                folder_part = ";" + ";".join(src["folders"])
            lines.append(f"{src['url']}{folder_part}")
        export_box = QMessageBox(cast("QWidget", self.ui))
        export_box.setText("Exported sources")
        export_box.setDetailedText("\n".join(lines))
        export_box.exec()

    def clean_target_modfolder(self) -> None:
        target_modfolder = Path(self.game_setting["game_mod_folder"])
        if not target_modfolder:
            QMessageBox.warning(
                cast("QMainWindow", self.ui), "", "No target modfolder found"
            )
        else:
            del_path_target = target_modfolder.resolve()
            messagebox_answer = QMessageBox.question(
                cast("QMainWindow", self.ui),
                "DELETING FOLDER",
                f"Are you sure you want to delete \
everything inside this folder?\n{del_path_target}",
            )

            if messagebox_answer == QMessageBox.StandardButton.Yes:
                self.recursive_rmdir(del_path_target)
                QMessageBox.information(
                    cast("QMainWindow", self.ui), "Done", "Mods are cleaned!"
                )

    def letsgo_mydudes(self) -> None:
        """Commit the current setup and fire the modifications."""
        profile = self.game_setting["profiles"].get(self.get_current_profile())
        mod_list = self.game_setting["mods"]
        enabled_mods = ",\n".join([x.get("name") for x in profile if x.get("enabled")])
        target_mod_folder = Path(self.game_setting["game_mod_folder"])

        msg_box = QMessageBox()
        msg_box.setText("Apply mods")
        msg_box.setInformativeText(
            "This will delete all content inside:\n"
            f"{target_mod_folder.resolve()}\n"
            "and start to apply mods:\n\n"
            "Do you want to proceed?"
        )
        msg_box.setDetailedText(enabled_mods)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        ret = msg_box.exec()
        if ret == QMessageBox.StandardButton.Yes:
            self.write_preset_to_config()
            try:
                self.recursive_rmdir(target_mod_folder.resolve())
                modpack.initialize_configs(
                    profile,
                    mod_list,
                    INPUT_FOLDER,
                    Path(self.game_setting["game_mod_folder"]),
                )
            except (OSError, ValueError, TypeError) as e:
                QMessageBox.warning(
                    cast("QMainWindow", self.ui), "", f"Something went wrong\n{e}"
                )
            else:
                QMessageBox.information(
                    cast("QMainWindow", self.ui), "Done", "Mods are loaded!"
                )
                self.set_dirty_status(False)

    def begin_fomod_parsing(self, base_folder: Path) -> None:
        """Begin parsing of FOMOD-modpacks."""
        if self.fomod is not None:
            return

        self.fomod = FomodParser(base_folder)
        assert isinstance(self.fomod, FomodParser)
        if hasattr(self.fomod, "ui"):
            self.fomod.ui.show()
        if hasattr(self.fomod, "finished"):
            self.fomod.finished.clicked.connect(self.handle_fomod_results)

    def handle_fomod_results(self) -> None:
        """Handle results from parsing a fomod-folder."""
        assert isinstance(self.fomod, FomodParser)
        results = self.fomod.handle_results()

        self.add_row_to_mods_fomod_style(
            str(self.fomod.module_name), self.fomod.mod_folder, results
        )
        self.fomod = None
        print(results)


if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)

    ui_file_name = MAIN_UI_PATH
    ui_file = QFile(ui_file_name)
    if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)
    ui_loader = QUiLoader()
    window = ui_loader.load(ui_file)
    ui_file.close()
    if not window:
        print(ui_loader.errorString())
        sys.exit(-1)
    # Cast window to Protocol for type safety
    # This cast is necessary because QUiLoader dynamically attaches widgets from the .ui file,
    # but mypy cannot see these attributes on QMainWindow. The Protocol defines the expected
    # interface, making the code mypy-compliant and maintainable.
    modbuddy_ui: ModBuddyUIProtocol = cast("ModBuddyUIProtocol", window)
    modbuddy = Modbuddy(modbuddy_ui)
    window.show()

    sys.exit(app.exec())
