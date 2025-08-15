# pylint: disable=unnecessary-ellipsis
"""
Protocols for ModBuddy UI components and dialogs.

This module defines Protocols for the main ModBuddy UI and the Edit Mod dialog,
enabling type-safe access to Qt Designer widgets loaded via QUiLoader. Attribute
names match the .ui file and runtime widget names for compatibility with mypy and
PySide6.

Typical usage example:

    modbuddy_ui: ModBuddyUIProtocol = cast("ModBuddyUIProtocol", window)
    dialog: EditModDialogProtocol = cast("EditModDialogProtocol", dialog_raw)
"""

from typing import Protocol

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QTreeView,
)


class ModBuddyUIProtocol(Protocol):
    """
    Protocol for the main ModBuddy UI loaded via QUiLoader.

    Attributes:
        game_combobox: Game selection dropdown.
        profile_combobox: Profile selection dropdown.
        mod_list: Table view listing mods.
        file_view: Tree view for mod files.
        clean_modfolder_button: Button to clean mod folder.
        initialize_mod: Button to initialize a mod.
        exit_button: Button to exit the application.
        new_mod_archived_button: Button to add a new archived mod.
        new_mod_button: Button to add a new mod from folder.
        load_profile_button: Button to load a profile.
        duplicate_profile_button: Button to duplicate a profile.
        save_profile_button: Button to save a profile.
        load_game_button: Button to load a game.
        new_game_button: Button to create a new game.
        mod_dest: Label showing mod destination folder.
        source_add: Button to add a mod source.
        source_export: Button to export sources.
        source_check_updates: Button to check for source updates.
        source_download: Button to download sources.
        source_edit: Button to edit sources.
        source_tableview: Table view for sources.
    """

    game_combobox: QComboBox
    profile_combobox: QComboBox
    mod_list: QTableView
    file_view: QTreeView
    clean_modfolder_button: QPushButton
    initialize_mod: QPushButton
    exit_button: QPushButton
    new_mod_archived_button: QPushButton
    new_mod_button: QPushButton
    load_profile_button: QPushButton
    duplicate_profile_button: QPushButton
    save_profile_button: QPushButton
    load_game_button: QPushButton
    new_game_button: QPushButton
    mod_dest: QLabel
    source_add: QPushButton
    source_export: QPushButton
    source_check_updates: QPushButton
    source_download: QPushButton
    source_edit: QPushButton
    source_tableview: QTableView


class EditModDialogProtocol(Protocol):
    """
    Protocol for the edit mod dialog loaded via QUiLoader.

    Attributes:
        nameLineEdit: Line edit for mod name. (camelCase for Qt compatibility)
        enabledCheckBox: Checkbox for mod enabled state.
        pathLineEdit: Line edit for mod path.

    Methods:
        show(): Show the dialog window.
        exec_(): Execute the dialog and return result code.
    """

    nameLineEdit: QLineEdit  # noqa: N815
    enabledCheckBox: QCheckBox  # noqa: N815
    pathLineEdit: QLineEdit  # noqa: N815

    def show(self) -> None:
        """Show the dialog window."""
        ...

    def exec_(self) -> int:
        """Execute the dialog and return the result code.

        Returns:
            int: Dialog result code (e.g., QDialog.Accepted or QDialog.Rejected).
        """
        ...

    # Add more dialog widgets/methods as needed
