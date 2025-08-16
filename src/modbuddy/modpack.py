"""
Mod management and hard-linking logic for ModBuddy.

This module provides the ModPack class and supporting functions to automate
mod application for games, using hard links to avoid data duplication and
supporting arbitrary mod folder structures. Mods are applied by creating
hard links from the source mod folder to the destination folder, preserving
space and enabling flexible mod management.

Typical usage example:

    mod_pack = ModPack(Path('mod_folder'), Path('game_folder'))
    mod_pack.add_mod()
"""

from pathlib import Path
from typing import Any


class ModPack:
    """
    Represents a mod pack and manages hard-linking mods to a destination folder.

    Attributes:
        modname: The name of the mod.
        mod_folder: The source folder containing the mod files.
        out_p: The destination folder for hard-linked mod files.
        case_sensitive: Whether file paths are treated as case-sensitive.

    """

    def __init__(self, mod_folder: Path, destination_folder: Path, case_sensitive: bool = False) -> None:
        """
        Initializes a ModPack instance.

        Args:
            mod_folder: The source folder containing the mod files.
            destination_folder: The destination folder for hard-linked mod files.
            case_sensitive: Whether file paths are treated as case-sensitive.

        """
        self.modname: str = mod_folder.name
        self.mod_folder: Path = mod_folder
        self.out_p: Path = destination_folder
        self.case_sensitive: bool = case_sensitive

    def convert_from_input_to_output(self, in_path: Path) -> Path:
        """
        Converts a source mod file/folder path to its destination path.

        Args:
            in_path: The input path within the mod folder.

        Returns:
            The corresponding output path in the destination folder.

        """
        try:
            rel_path = in_path.relative_to(self.mod_folder)
        except ValueError:
            # If not a subpath, fallback to basename
            rel_path = Path(in_path.name)
        if not self.case_sensitive:
            rel_path = Path(str(rel_path).lower())

        return self.out_p / rel_path

    def handle_symlinking(self, file_path: Path) -> None:
        """
        Creates a hard link for a mod file at the destination path.

        If the destination file already exists, it is deleted before linking.

        Args:
            file_path: The source file path to link from.

        """
        target_path: Path = self.convert_from_input_to_output(file_path)
        if target_path.exists():
            # print("DELETE {}".format(target_path))
            target_path.unlink()
        # print("{} --> {}".format(file_path.resolve(), target_path.resolve()))
        target_path.hardlink_to(file_path)

    def create_folder(self, folder_path: Path) -> None:
        """
        Creates the corresponding destination folder for a mod folder.

        Args:
            folder_path: The source folder path to create in the destination.

        """
        output_path: Path = self.convert_from_input_to_output(folder_path)
        output_path.mkdir(exist_ok=True)

    def add_mod(self) -> None:
        """
        Applies the mod by hard-linking all files and creating folders in the destination.

        Iterates through all files and folders in the mod folder, creating corresponding
        folders and hard links in the destination folder.
        """
        for input_path in self.mod_folder.glob("**/*"):
            if input_path.is_dir():
                self.create_folder(input_path)
                continue
            self.handle_symlinking(input_path)


def initialize_mod_configs(
    profile_payload: Any,
    mod_list: dict[str, Any],
    input_folder: Path,
    output_folder: Path,
) -> None:
    """
    Initializes and applies enabled mods from a profile payload.

    Iterates through the profile payload, applying enabled mods by creating
    ModPack instances and invoking their add_mod method. Handles both regular
    mods and fomod-type mods with options.

    Args:
        profile_payload: The profile configuration containing mod entries.
        mod_list: A mapping of mod names to their source folder paths.
        input_folder: The root folder containing all mod sources.
        output_folder: The destination folder for applied mods.

    """
    for single_mod in profile_payload:
        if not single_mod.get("enabled"):
            continue

        mod_name = single_mod.get("name")
        mod_path = mod_list.get(mod_name)
        if mod_path is None:
            continue

        if single_mod.get("type") == "fomod":
            for fomod_x in single_mod.get("options").values():
                fomod_source = fomod_x.get("source")
                fomod_dest = fomod_x.get("destination")
                if fomod_source is None or fomod_dest is None:
                    continue
                fomod_target: Path = input_folder / mod_path / fomod_source
                fomod_output_folder: Path = output_folder / fomod_dest
                fomod_output_folder.mkdir(exist_ok=True)
                if fomod_target.is_file():
                    # Hardlink the file directly into the output folder
                    out_file = fomod_output_folder / fomod_target.name
                    if out_file.exists():
                        out_file.unlink()
                    out_file.hardlink_to(fomod_target)
                else:
                    # If it's a folder, use ModPack logic
                    mod_pack = ModPack(fomod_target, fomod_output_folder)
                    mod_pack.add_mod()
        else:
            regular_target_folder: Path = input_folder / mod_path
            mod_pack = ModPack(regular_target_folder, output_folder)
            mod_pack.add_mod()
