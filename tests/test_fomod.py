# pylint: disable=redefined-outer-name
from pathlib import Path
from unittest.mock import MagicMock
from xml.etree import ElementTree

import pytest
from _pytest.monkeypatch import MonkeyPatch

from modbuddy.fomod import (
    Files,
    Folder,
    FomodParser,
    Group,
    InstallStep,
    OptionalFileGroups,
    Plugin,
    Plugins,
)


@pytest.fixture
def mock_fomod_xml_content() -> str:
    """Provides mock FOMOD XML content."""
    return """
<config>
    <moduleName>Test Fomod Mod</moduleName>
    <installSteps order="Explicit">
        <installStep name="Choose an option">
            <optionalFileGroups order="Explicit">
                <group name="Main Files" type="SelectExactlyOne">
                    <plugins>
                        <plugin name="Option 1">
                            <description>This is option 1.</description>
                            <image path="fomod/op1.png" />
                            <files>
                                <folder source="00_Option1" destination="." priority="0" />
                            </files>
                        </plugin>
                        <plugin name="Option 2">
                            <description>This is option 2.</description>
                            <files>
                                <folder source="01_Option2" destination="." priority="0" />
                            </files>
                        </plugin>
                    </plugins>
                </group>
            </optionalFileGroups>
        </installStep>
    </installSteps>
</config>
"""


@pytest.fixture
def fomod_parser(tmp_path: Path, mock_fomod_xml_content: str, monkeypatch: MonkeyPatch) -> FomodParser:
    """Creates a FomodParser instance with a mock UI."""
    mod_folder = tmp_path / "TestFomodMod"
    fomod_dir = mod_folder / "fomod"
    fomod_dir.mkdir(parents=True)
    (fomod_dir / "ModuleConfig.xml").write_text(mock_fomod_xml_content)

    # Mock PySide6 UI classes to avoid actual UI creation
    monkeypatch.setattr("modbuddy.fomod.QWizard", MagicMock())
    monkeypatch.setattr("modbuddy.fomod.QWizardPage", MagicMock())
    monkeypatch.setattr("modbuddy.fomod.QGridLayout", MagicMock())
    monkeypatch.setattr("modbuddy.fomod.QLabel", MagicMock())
    monkeypatch.setattr("modbuddy.fomod.QRadioButton", MagicMock())
    monkeypatch.setattr("modbuddy.fomod.QTextEdit", MagicMock())
    monkeypatch.setattr("modbuddy.fomod.QPixmap", MagicMock())

    return FomodParser(mod_folder)


def test_fomod_parser_init(fomod_parser: FomodParser) -> None:
    """Tests that the FomodParser is initialized correctly."""
    assert fomod_parser.module_name == "Test Fomod Mod"
    assert len(fomod_parser.install_steps) == 1
    install_step = fomod_parser.install_steps[0].install_steps[0]
    assert isinstance(install_step, InstallStep)
    assert install_step.name == "Choose an option"
    optional_file_group = install_step.optional_file_groups[0]
    assert isinstance(optional_file_group, OptionalFileGroups)
    group = optional_file_group.groups[0]
    assert isinstance(group, Group)
    assert group.name == "Main Files"
    plugins_collection = group.plugin_collection[0]
    assert isinstance(plugins_collection, Plugins)
    plugin1 = plugins_collection.plugins[0]
    assert isinstance(plugin1, Plugin)
    assert plugin1.name == "Option 1"
    assert plugin1.description == "This is option 1."
    assert plugin1.image == "fomod/op1.png"
    files = plugin1.files_collection[0]
    assert isinstance(files, Files)
    folder = files.folders[0]
    assert isinstance(folder, Folder)
    assert folder.source == "00_Option1"
    assert folder.destination == "."


def test_folder_to_dict() -> None:
    """Tests the Folder.to_dict() method."""
    xml_str = '<folder source="src" destination="dst" priority="1" />'
    xml_elem = ElementTree.fromstring(xml_str)
    folder = Folder(xml_elem)
    assert folder.to_dict() == {
        "source": "src",
        "destination": "dst",
        "priority": "1",
    }


def test_handle_results(fomod_parser: FomodParser) -> None:
    """Tests the handle_results method of FomodParser."""
    # Simulate a user selecting "Option 1"
    plugin1 = (
        fomod_parser.install_steps[0].install_steps[0].optional_file_groups[0].groups[0].plugin_collection[0].plugins[0]
    )
    plugin1.enabled = True

    results = fomod_parser.handle_results()
    expected = {
        "0Main Files": {
            "source": "00_Option1",
            "destination": ".",
            "priority": "0",
        }
    }
    assert results == expected
