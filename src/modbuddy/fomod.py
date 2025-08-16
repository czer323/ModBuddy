"""
Fomod module for parsing and displaying FOMOD installer configs.

This module provides classes to parse FOMOD XML files, build a Qt-based wizard UI
for mod installation, and handle user selections/results. It supports flexible mod
structures and integrates with PySide6 for cross-platform GUI.

Typical usage example:

    parser = FomodParser(Path(mod_folder))
    parser.ui.show()
    results = parser.handle_results()
"""

import sys
from pathlib import Path
from xml.etree import ElementTree

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QRadioButton,
    QTextEdit,
    QWizard,
    QWizardPage,
)


class FomodParser:
    """
    Parser for FOMOD installer XML and builder for Qt wizard UI.

    Attributes:
        mod_folder: Path to the mod's root directory.
        fomod_file: Path to the FOMOD XML config file.
        module_name: Name of the module parsed from XML.
        install_steps: List of InstallSteps objects.
        ui: QWizard instance for the installer UI.

    """

    def __init__(self, mod_folder: Path) -> None:
        """
        Initializes the parser and builds the UI.

        Args:
            mod_folder: Path to the mod's root directory.

        """
        self.mod_folder = mod_folder
        self.fomod_file = Path(mod_folder) / "fomod/ModuleConfig.xml"
        xml = ElementTree.parse(self.fomod_file).getroot()
        self.module_name = xml.findtext("./moduleName")
        self.install_steps = [InstallSteps(x) for x in xml.findall("./installSteps")]
        self.build_ui()

    def build_ui(self) -> None:
        """Builds the Qt wizard UI for the installer steps."""
        self.ui = QWizard()
        for install_steps_collection in self.install_steps:
            for install_step in install_steps_collection.install_steps:
                for optional_file_group in install_step.optional_file_groups:
                    for group in optional_file_group.groups:
                        new_page = QWizardPage()
                        new_layout = QGridLayout()
                        new_layout.addWidget(QLabel(group.name), 0, 0)
                        for plugin_collection in group.plugin_collection:
                            for i, plugin in enumerate(plugin_collection.plugins):
                                target_radio = QRadioButton(plugin.name)
                                new_layout.addWidget(target_radio, i + 1, 0)
                                target_radio.toggled.connect(plugin.update)
                                new_layout.addWidget(QTextEdit(plugin.description), i + 1, 1)
                                if plugin.image:
                                    parsed_img = self.mod_folder / plugin.image.replace("\\", "/")
                                    img = QPixmap(parsed_img)
                                    test = QLabel()
                                    test.setPixmap(img)
                                    new_layout.addWidget(test, i + 1, 2)
                        new_page.setTitle(install_step.name if install_step.name is not None else "")
                        new_page.setLayout(new_layout)
                        self.ui.addPage(new_page)
        final_page = QWizardPage()
        self.finished = self.ui.button(QWizard.WizardButton.FinishButton)
        final_page.setFinalPage(True)
        self.ui.addPage(final_page)

    def handle_results(self) -> dict[str, dict[str, str | None]]:
        """
        Collects enabled plugin results after user selection.

        Returns:
            A dictionary mapping install step/group keys to folder dicts.

        """
        tmp = {}
        print("handling results")
        for install_steps_collection in self.install_steps:
            for i, install_step in enumerate(install_steps_collection.install_steps):
                for optional_file_group in install_step.optional_file_groups:
                    for group in optional_file_group.groups:
                        for plugins_collection in group.plugin_collection:
                            for plugin in plugins_collection.plugins:
                                if plugin.enabled:
                                    for files in plugin.files_collection:
                                        print(plugin.enabled, group.name)
                                        for folder in files.folders:
                                            tmp[f"{i!s}{group.name}"] = folder.to_dict()
        return tmp


class InstallSteps:
    """
    Represents a collection of install steps from FOMOD XML.

    Attributes:
        order: The order attribute from XML.
        install_steps: List of InstallStep objects.

    """

    def __init__(self, xml: ElementTree.Element) -> None:
        """
        Initializes the install steps collection.

        Args:
            xml: XML element for installSteps.

        """
        self.order = xml.get("order")
        self.install_steps = [InstallStep(x) for x in xml.findall("./installStep")]


class InstallStep:
    """
    Represents a single install step in the FOMOD installer.

    Attributes:
        name: Name of the install step.
        optional_file_groups: List of OptionalFileGroups objects.

    """

    def __init__(self, xml: ElementTree.Element) -> None:
        """
        Initializes the install step.

        Args:
            xml: XML element for installStep.

        """
        self.name = xml.get("name")
        self.optional_file_groups = [OptionalFileGroups(x) for x in xml.findall("./optionalFileGroups")]


class OptionalFileGroups:
    """
    Represents a collection of optional file groups in an install step.

    Attributes:
        order: The order attribute from XML.
        groups: List of Group objects.

    """

    def __init__(self, xml: ElementTree.Element) -> None:
        """
        Initializes the optional file groups.

        Args:
            xml: XML element for optionalFileGroups.

        """
        self.order = xml.get("order")
        self.groups = [Group(x) for x in xml.findall("./group")]


class Group:
    """
    Represents a group of plugins in an optional file group.

    Attributes:
        name: Name of the group.
        type: Type of the group.
        plugin_collection: List of Plugins objects.

    """

    def __init__(self, xml: ElementTree.Element) -> None:
        """
        Initializes the group.

        Args:
            xml: XML element for group.

        """
        self.name = xml.get("name")
        self.type = xml.get("type")
        self.plugin_collection = [Plugins(x) for x in xml.findall("./plugins")]


class Plugins:
    """
    Represents a collection of plugins in a group.

    Attributes:
        name: Name of the plugins collection.
        description: Description of the plugins collection.
        plugins: List of Plugin objects.

    """

    def __init__(self, xml: ElementTree.Element) -> None:
        """
        Initializes the plugins collection.

        Args:
            xml: XML element for plugins.

        """
        self.name = xml.get("name")
        self.description = xml.findtext("description")
        self.plugins = [Plugin(x) for x in xml.findall("./plugin")]


class Plugin:
    """
    Represents a single plugin option in a group.

    Attributes:
        name: Name of the plugin.
        description: Description of the plugin.
        flags: List of condition flag names.
        enabled: Whether the plugin is enabled by user selection.
        image: Path to the plugin image, if any.
        files_collection: List of Files objects.

    """

    def __init__(self, xml: ElementTree.Element) -> None:
        """
        Initializes the plugin.

        Args:
            xml: XML element for plugin.

        """
        self.name = xml.get("name")
        self.description = xml.findtext("description")
        self.flags = [x.get("name") for x in xml.findall("./conditionFlags/flag")]
        self.enabled = False
        try:
            image_elem = xml.find("./image")
            self.image = image_elem.get("path") if image_elem is not None else None
        except AttributeError:
            self.image = None
        self.files_collection = [Files(x) for x in xml.findall("./files")]

    def update(self, arg: bool) -> None:
        """
        Updates the enabled state of the plugin.

        Args:
            arg: Boolean indicating if the plugin is enabled.

        """
        self.enabled = arg


class Files:
    """
    Represents a collection of folders for a plugin's files.

    Attributes:
        folders: List of Folder objects.

    """

    def __init__(self, xml: ElementTree.Element) -> None:
        """
        Initializes the files collection.

        Args:
            xml: XML element for files.

        """
        self.folders = [Folder(x) for x in xml.findall("./folder")]


class Folder:
    """
    Represents a folder mapping for mod files.

    Attributes:
        source: Source folder path.
        destination: Destination folder path.
        priority: Priority of the folder.

    """

    def __init__(self, xml: ElementTree.Element) -> None:
        """
        Initializes the folder mapping.

        Args:
            xml: XML element for folder.

        """
        self.source = xml.get("source")
        self.destination = xml.get("destination")
        self.priority = xml.get("priority")

    def to_dict(self) -> dict[str, str | None]:
        """
        Converts the folder mapping to a dictionary.

        Returns:
            A dict with keys 'source', 'destination', and 'priority'.

        """
        return {
            "source": self.source,
            "destination": self.destination,
            "priority": self.priority,
        }


if __name__ == "__main__":
    # Entry point for running the FOMOD installer UI as a standalone app.

    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    payload = sys.argv[1]
    parser = FomodParser(Path(payload))
    parser.ui.show()
    app.exec()
    parser.handle_results()
