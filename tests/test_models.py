# pylint: disable=redefined-outer-name
from typing import Any

import pytest
from PySide6.QtCore import Qt

from modbuddy.models import ModModel, SourceModel


@pytest.fixture
def mock_mod_settings() -> dict[str, Any]:
    """Provides mock settings for the ModModel."""
    return {
        "profiles": {
            "default": [
                {"name": "Mod 1", "enabled": True, "type": "regular"},
                {"name": "Mod 2", "enabled": False, "type": "fomod"},
            ]
        },
        "mods": {
            "Mod 1": "/path/to/mod1",
            "Mod 2": "/path/to/mod2",
        },
        "default_mod_folder": "/path/to",
    }


@pytest.fixture
def mock_source_list() -> list[dict[str, Any]]:
    """Provides a mock list of sources for the SourceModel."""
    return [
        {"title": "Source 1", "url": "http://example.com/1", "size": "1MB"},
        {"title": "Source 2", "url": "http://example.com/2", "size": "2MB"},
    ]


def test_mod_model_init(mock_mod_settings: dict[str, Any]) -> None:
    """Tests the initialization of ModModel."""
    model = ModModel(settings=mock_mod_settings, profile="default")
    assert model.rowCount() == 2
    assert model.columnCount() == 4


def test_mod_model_header_data(mock_mod_settings: dict[str, Any]) -> None:
    """Tests the headerData method of ModModel."""
    model = ModModel(settings=mock_mod_settings, profile="default")
    assert model.headerData(0, Qt.Orientation.Horizontal) == "enabled"
    assert model.headerData(1, Qt.Orientation.Horizontal) == "name"
    assert model.headerData(2, Qt.Orientation.Horizontal) == "type"
    assert model.headerData(3, Qt.Orientation.Horizontal) == "path"


def test_mod_model_data(mock_mod_settings: dict[str, Any]) -> None:
    """Tests the data method of ModModel."""
    model = ModModel(settings=mock_mod_settings, profile="default")

    # Test row 0 (Mod 1)
    assert model.data(model.index(0, 1)) == "Mod 1"
    assert model.data(model.index(0, 0), Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked
    assert model.data(model.index(0, 2)) == "regular"
    assert model.data(model.index(0, 3)) == "./mod1"

    # Test row 1 (Mod 2)
    assert model.data(model.index(1, 1)) == "Mod 2"
    assert model.data(model.index(1, 0), Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Unchecked
    assert model.data(model.index(1, 2)) == "fomod"
    assert model.data(model.index(1, 3)) == "./mod2"


def test_mod_model_set_data(mock_mod_settings: dict[str, Any]) -> None:
    """Tests the setData method of ModModel."""
    model = ModModel(settings=mock_mod_settings, profile="default")

    # Toggle enabled state of Mod 1 to unchecked
    model.setData(model.index(0, 0), Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
    assert model.data(model.index(0, 0), Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Unchecked
    assert not mock_mod_settings["profiles"]["default"][0]["enabled"]

    # Toggle enabled state of Mod 2 to checked
    model.setData(model.index(1, 0), Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
    assert model.data(model.index(1, 0), Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked
    assert mock_mod_settings["profiles"]["default"][1]["enabled"]


def test_mod_model_flags(mock_mod_settings: dict[str, Any]) -> None:
    """Tests the flags method of ModModel."""
    model = ModModel(settings=mock_mod_settings, profile="default")
    # Enabled column should be checkable
    assert Qt.ItemFlag.ItemIsUserCheckable in model.flags(model.index(0, 0))
    # Other columns should not be checkable
    assert Qt.ItemFlag.ItemIsUserCheckable not in model.flags(model.index(0, 1))


def test_source_model_init(mock_source_list: list[dict[str, Any]]) -> None:
    """Tests the initialization of SourceModel."""
    model = SourceModel(sources=mock_source_list)
    assert model.rowCount() == 2
    assert model.columnCount() == 6


def test_source_model_header_data(mock_source_list: list[dict[str, Any]]) -> None:
    """Tests the headerData method of SourceModel."""
    model = SourceModel(sources=mock_source_list)
    assert model.headerData(0, Qt.Orientation.Horizontal) == "title"
    assert model.headerData(5, Qt.Orientation.Horizontal) == "url"


def test_source_model_data(mock_source_list: list[dict[str, Any]]) -> None:
    """Tests the data method of SourceModel."""
    model = SourceModel(sources=mock_source_list)
    assert model.data(model.index(0, 0)) == "Source 1"
    assert model.data(model.index(0, 5)) == "http://example.com/1"
    assert model.data(model.index(1, 0)) == "Source 2"
    assert model.data(model.index(1, 4)) == "2MB"
