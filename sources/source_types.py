# pylint: disable=unnecessary-ellipsis
"""Source Protocol for Mod Sources"""

from datetime import datetime
from pathlib import Path
from typing import Protocol, TypedDict


class SourceDict(TypedDict, total=False):
    title: str
    filename: str
    foldername: str
    folders: str  # or list[str] if you want to keep it as a list
    description: str
    installed: str
    added: str
    updated: str
    size: str
    checksum: str
    url: str
    download_url: str


class SourceProtocol(Protocol):
    """
    Protocol for mod source objects, defining the required interface for all source types.

    Attributes:
        title (str): The display name of the mod source.
        filename (str): The filename of the mod archive or package.
        foldername (str): The main folder name for the mod source.
        folders (list[str]): List of subfolders or patch folders associated with the mod.
        description (str): A human-readable description of the mod source.
        installed (datetime): The datetime when the mod was last installed.
        added (datetime): The datetime when the mod source was added to the system.
        updated (datetime): The datetime when the mod source was last updated.
        checksum (str): The checksum (e.g., MD5) of the mod file for integrity verification.
        size (str): The size of the mod file (e.g., in KB or MB).
        url (str): The original URL of the mod source.
        download_url (str): The direct download URL for the mod file.
    """

    title: str
    filename: str
    foldername: str
    folders: list[str]
    description: str
    installed: datetime
    added: datetime
    updated: datetime
    checksum: str
    size: str
    url: str
    download_url: str

    @classmethod
    def from_url(cls, url: str, folders: list[str] | None = None) -> "SourceProtocol":
        """
        Create a source object from a URL and optional folders.

        Args:
            url (str): The URL to fetch and parse for source metadata.
            folders (list[str] | None): Optional list of subfolders or patches.

        Returns:
            SourceProtocol: An instance of the source type implementing this protocol.
        """
        ...

    @classmethod
    def from_dict(cls, entry: dict[str, str]) -> "SourceProtocol":
        """
        Create a source object from a dictionary of attributes.

        Args:
            entry (dict[str, str]): Dictionary containing source metadata fields.

        Returns:
            SourceProtocol: An instance of the source type implementing this protocol.
        """
        ...

    def update(self) -> None:
        """
        Update the source object with the latest metadata from its remote source.
        """
        ...

    def check_if_file_exists(self, downloaded_file: Path) -> bool:
        """
        Check if the downloaded file exists and matches the expected checksum.

        Args:
            downloaded_file (Path): Path to the downloaded mod file.

        Returns:
            bool: True if the file exists and matches the checksum, False otherwise.
        """
        ...

    def get_download_url(self) -> str:
        """
        Get the direct download URL for the mod file.

        Returns:
            str: The direct download URL.
        """
        ...

    def download_file(self, write_folder: Path) -> None:
        """
        Download the mod file to the specified folder.

        Args:
            write_folder (Path): The folder to write the downloaded file to.
        """
        ...


# You can add more types here as needed for modpack, presets, etc.
