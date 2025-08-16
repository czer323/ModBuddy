"""
Qt table models for mod and source data in ModBuddy's UI.

This module provides:
    ModModel: Table model for game mods, supporting checkboxes and custom columns.
    SourceModel: Table model for mod sources, supporting custom columns.

Typical usage example:
    model = ModModel(settings, profile)
    source_model = SourceModel(sources)
"""

from typing import Any

from PySide6 import QtCore
from PySide6.QtCore import QModelIndex, QPersistentModelIndex, Qt


class ModModel(QtCore.QAbstractTableModel):
    """Table model for game mods in a Qt QTableView.

    Attributes:
        mod_order: List of mod dictionaries for the current profile.
        headers: Tuple of column header names.
        profile: The current profile name or identifier.
        game_setting: Dictionary of game settings and profiles.
    """

    mod_order: list[dict[str, Any]]
    headers: tuple[str, ...]
    profile: Any
    game_setting: dict[str, Any]

    def __init__(
        self, settings: dict[str, Any], profile: Any, parent: Any = None
    ) -> None:
        super().__init__(parent)
        self.profile = profile
        self.game_setting = settings
        self.mod_order = []
        self.headers = ("enabled", "name", "type", "path")
        self.parse_mods_from_settings()

    def parse_mods_from_settings(self) -> None:
        """Updates mod_order from game_setting for the current profile.

        Reads the game_setting dictionary and sets mod_order to the list of mods
        for the current profile.
        """
        if not self.game_setting:
            return
        try:
            profile = self.game_setting["profiles"]
            assert isinstance(profile, dict)

            mods = profile.get(self.profile)
            if mods is None:
                self.mod_order = []
            else:
                self.mod_order = mods
        except AttributeError:
            pass

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Returns header data for the table columns.

        Args:
            section: Column index.
            orientation: Qt orientation (horizontal/vertical).
            role: Data role (default: DisplayRole).

        Returns:
            Header name for the given section and orientation, or default.
        """
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.headers[section]
        return super().headerData(section, orientation, role)

    def parse_path(self, row: dict[str, Any]) -> Any:
        """Returns a display-friendly mod path.

        Args:
            row: Dictionary representing a mod.

        Returns:
            Relative mod path with default folder replaced, or None.
        """
        mod_settings = self.game_setting["mods"]
        if not isinstance(mod_settings, dict):
            return None
        relative_path = mod_settings.get(row.get("name"))
        default_mod_folder = self.game_setting.get("default_mod_folder")
        if isinstance(relative_path, str) and isinstance(default_mod_folder, str):
            return relative_path.replace(default_mod_folder, ".")
        return relative_path

    def data(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Returns data for a given cell in the table.

        Args:
            index: QModelIndex or QPersistentModelIndex for the cell.
            role: Data role (default: DisplayRole).

        Returns:
            Data for the cell, formatted for display or check state.
        """
        cur_profile = self.game_setting["profiles"][self.profile]

        row = cur_profile[index.row()]
        assert isinstance(row, dict)

        if (
            role == Qt.ItemDataRole.CheckStateRole
            and self.headers[index.column()] == "enabled"
        ):
            if row.get("enabled"):
                return Qt.CheckState.Checked
            else:
                return Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.DisplayRole:
            if self.headers[index.column()] == "type":
                return row.get("type", "basic")
            if self.headers[index.column()] == "path":
                return self.parse_path(row)
            else:
                return row.get(self.headers[index.column()])

    def setData(
        self,
        index: QModelIndex | QPersistentModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Sets data for a cell, supporting checkboxes for 'enabled'.

        Args:
            index: QModelIndex or QPersistentModelIndex for the cell.
            value: Value to set.
            role: Data role (default: EditRole).

        Returns:
            True if data was set, otherwise result of base setData.
        """
        cur_profile = self.game_setting["profiles"][self.profile]
        assert isinstance(cur_profile, list)
        if (
            role == Qt.ItemDataRole.CheckStateRole
            and self.headers[index.column()] == "enabled"
        ):
            cur_profile[index.row()]["enabled"] = value == Qt.CheckState.Checked
            self.layoutChanged.emit()
            return True
        # For other columns, fallback to default behavior
        return super().setData(index, value, role=role)

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        """Returns item flags for a cell, enabling checkboxes for 'enabled'.

        Args:
            index: QModelIndex or QPersistentModelIndex for the cell.

        Returns:
            Qt.ItemFlag for the cell.
        """
        if index.column() == 0:
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
        return super().flags(index)

    def rowCount(
        self, _index: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> int:
        """Returns the number of rows in the model.

        Args:
            _index: QModelIndex or QPersistentModelIndex (unused).

        Returns:
            Number of rows (mods) in the current profile.
        """
        return len(self.mod_order)

    def columnCount(
        self, _index: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> int:
        """Returns the number of columns in the model.

        Args:
            _index: QModelIndex or QPersistentModelIndex (unused).

        Returns:
            Number of columns in the table.
        """
        return len(self.headers)


class SourceModel(QtCore.QAbstractTableModel):
    """Table model for mod sources in a Qt QTableView.

    Attributes:
        sources: List of source dictionaries.
        headers: Tuple of column header names.
    """

    sources: list[dict[str, Any]]
    headers: tuple[str, ...]

    def __init__(self, sources: list[dict[str, Any]], parent: Any = None) -> None:
        super().__init__(parent)
        self.sources = sources
        self.headers = ("title", "installed", "added", "updated", "size", "url")

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Returns header data for the table columns.

        Args:
            section: Column index.
            orientation: Qt orientation (horizontal/vertical).
            role: Data role (default: DisplayRole).

        Returns:
            Header name for the given section and orientation, or default.
        """
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.headers[section]
        return super().headerData(section, orientation, role)

    def data(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Returns data for a given cell in the table.

        Args:
            index: QModelIndex or QPersistentModelIndex for the cell.
            role: Data role (default: DisplayRole).

        Returns:
            Data for the cell, formatted for display.
        """
        row = self.sources[index.row()]
        assert isinstance(row, dict)
        if role == Qt.ItemDataRole.DisplayRole:
            return row.get(self.headers[index.column()])

    def rowCount(
        self, _index: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> int:
        """Returns the number of rows in the model.

        Args:
            _index: QModelIndex or QPersistentModelIndex (unused).

        Returns:
            Number of rows (sources) in the model.
        """
        return len(self.sources)

    def columnCount(
        self, _index: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> int:
        """Returns the number of columns in the model.

        Args:
            _index: QModelIndex or QPersistentModelIndex (unused).

        Returns:
            Number of columns in the table.
        """
        return len(self.headers)
