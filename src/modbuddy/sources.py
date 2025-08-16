import ast
import contextlib
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag


@dataclass
class SourceBase:
    """Something."""

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
    def from_url(cls, url: str, folders: list[str] | None = None) -> "SourceBase":
        raise NotImplementedError

    @classmethod
    def from_dict(cls, entry: dict[str, str]) -> "SourceBase":
        """Initialize from a dictionary."""
        raise NotImplementedError

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "filename": self.filename,
            "foldername": self.foldername,
            "folders": self.folders,
            "description": self.description,
            "installed": str(self.installed),
            "added": str(self.added),
            "updated": str(self.updated),
            "size": self.size,
            "checksum": self.checksum,
            "url": self.url,
            "download_url": self.download_url,
        }

    def update(self) -> None:
        raise NotImplementedError

    def check_if_file_exists(self, downloaded_file: Path) -> bool:
        if not self.checksum:
            return False

        if not downloaded_file.is_file():
            return False

        file_bytes = downloaded_file.read_bytes()
        readable_hash = hashlib.md5(file_bytes).hexdigest()

        return readable_hash == self.checksum

    def get_download_url(self) -> str:
        raise NotImplementedError

    def download_file(self, write_folder: Path) -> None:
        """Download a file."""
        write_path = write_folder / self.filename

        r = requests.get(self.get_download_url(), timeout=30)
        with open(write_path, "wb") as fp:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    fp.write(chunk)
        return


@dataclass
class SourceModdb(SourceBase):
    """Something."""

    BASE_URL = "https://www.moddb.com"

    @classmethod
    def from_url(cls, url: str, folders: list[str] | None = None) -> "SourceModdb":
        """Initialize from url."""
        site_content = requests.get(url, timeout=30).text
        site = BeautifulSoup(site_content, "html.parser")

        def safe_find_text(tag: str) -> str:
            node = site.find(string=tag)
            if node is None or node.parent is None:
                return ""

            parent = node.parent

            # For date/time, the value is in the 'datetime' attribute of the <time> tag
            if parent.name == "time" and "datetime" in parent.attrs:
                dt_val = parent["datetime"]
                if isinstance(dt_val, str):
                    return dt_val
                if isinstance(dt_val, list):
                    return dt_val[0] if dt_val else ""

            # For other tags, assume the value is in the next sibling span
            next_sibling_span = parent.find_next_sibling("span")
            if next_sibling_span:
                return next_sibling_span.text.strip()

            return ""

        def safe_head_title(site: BeautifulSoup) -> str:
            if site.head and hasattr(site.head, "title") and site.head.title and hasattr(site.head.title, "string"):
                return str(site.head.title.string)
            return ""

        def safe_description(site: BeautifulSoup) -> str:
            desc_tag = site.find(attrs={"name": "description"})

            if desc_tag and isinstance(desc_tag, Tag) and "content" in desc_tag.attrs:
                return str(desc_tag["content"])
            return ""

        def safe_download_url(site: BeautifulSoup) -> str:
            mirror_tag = site.find(id="downloadmirrorstoggle")

            if mirror_tag and isinstance(mirror_tag, Tag) and "href" in mirror_tag.attrs:
                return str(mirror_tag["href"]).strip()
            return ""

        title = safe_head_title(site)
        filename = safe_find_text("Filename")
        description = safe_description(site)
        added_str = safe_find_text("Added")
        try:
            added = (
                datetime.fromisoformat(added_str)
                if added_str
                else datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc)
            )
        except (ValueError, TypeError):
            added = datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc)

        installed = datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc)

        updated_str = safe_find_text("Updated")
        try:
            updated = datetime.fromisoformat(updated_str) if updated_str else added
        except (ValueError, TypeError):
            updated = added

        size = safe_find_text("Size")
        checksum = safe_find_text("MD5 Hash")
        download_url = safe_download_url(site)

        foldername = ""
        if hasattr(site, "get"):
            foldername_val = site.get("foldername")
            foldername = foldername_val if isinstance(foldername_val, str) else title.rsplit(".", 1)[0] if title else ""
        else:
            foldername = title.rsplit(".", 1)[0] if title else ""

        if folders is None:
            folders = []

        return cls(
            title=title,
            filename=filename,
            description=description,
            added=added,
            installed=installed,
            updated=updated,
            size=size,
            checksum=checksum,
            url=url,
            download_url=download_url,
            foldername=foldername,
            folders=folders,
        )

    @classmethod
    def from_dict(cls, entry: dict[str, str]) -> "SourceModdb":
        """Initialize from a dictionary."""
        updated_str = entry.get("updated")
        added_str = entry.get("added")
        try:
            updated = datetime.fromisoformat(
                updated_str
                if updated_str is not None
                else (added_str if added_str is not None else "1900-01-01 00:00:00+00:00")
            )
        except ValueError:
            updated = datetime.fromisoformat(added_str if added_str is not None else "1900-01-01 00:00:00+00:00")

        filename = entry.get("filename") or ""
        foldername = entry.get("foldername")
        if not foldername:
            foldername = filename.rsplit(".", 1)[0] if filename else ""

        # folders: try to parse as list[str], fallback to []
        folders_raw = entry.get("folders")
        if isinstance(folders_raw, str):
            try:
                folders = ast.literal_eval(folders_raw)
                if not isinstance(folders, list):
                    folders = []
            except (ValueError, SyntaxError):
                folders = []
        elif isinstance(folders_raw, list):
            folders = folders_raw
        else:
            folders = []

        def safe_str(val: object) -> str:
            return val if isinstance(val, str) and val is not None else ""

        title = safe_str(entry.get("title"))
        description = safe_str(entry.get("description"))
        size = safe_str(entry.get("size"))
        checksum = safe_str(entry.get("checksum"))
        url = safe_str(entry.get("url"))
        download_url = safe_str(entry.get("download_url"))

        installed_str = entry.get("installed", "1900-01-01 00:00:00+00:00")
        try:
            installed = datetime.fromisoformat(installed_str)
        except (ValueError, TypeError):
            installed = datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc)

        try:
            added = (
                datetime.fromisoformat(added_str)
                if added_str
                else datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc)
            )
        except (ValueError, TypeError):
            added = datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc)

        return cls(
            title=title,
            filename=filename,
            foldername=foldername,
            folders=folders,
            description=description,
            installed=installed,
            added=added,
            updated=updated,
            size=size,
            checksum=checksum,
            url=url,
            download_url=download_url,
        )

    def update(self) -> None:
        """Update object with information from source."""
        site_content = requests.get(self.url, timeout=30).text
        site = BeautifulSoup(site_content, "html.parser")

        # Defensive title extraction
        self.title = ""
        if site.head and hasattr(site.head, "title") and site.head.title and hasattr(site.head.title, "string"):
            self.title = str(site.head.title.string)

        # Defensive filename extraction
        filename_node = site.find(text="Filename")
        self.filename = ""
        if (
            filename_node
            and hasattr(filename_node, "parent")
            and filename_node.parent
            and hasattr(filename_node.parent, "parent")
            and filename_node.parent.parent
        ):
            parent = filename_node.parent.parent
            if hasattr(parent, "span") and parent.span and hasattr(parent.span, "text"):
                self.filename = parent.span.text.strip()

        if not self.foldername:
            self.foldername = self.filename.rsplit(".", 1)[0] if self.filename else ""

        # Defensive description extraction
        desc_tag = site.find(attrs={"name": "description"})

        self.description = ""
        if desc_tag and isinstance(desc_tag, Tag) and "content" in desc_tag.attrs:
            self.description = str(desc_tag["content"])

        # Defensive added extraction
        added_node = site.find(text="Added")
        self.added = datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc)
        if (
            added_node
            and hasattr(added_node, "parent")
            and added_node.parent
            and hasattr(added_node.parent, "parent")
            and added_node.parent.parent
        ):
            parent = added_node.parent.parent
            if hasattr(parent, "time") and parent.time and "datetime" in getattr(parent.time, "attrs", {}):
                dt_val = parent.time["datetime"]

                if isinstance(dt_val, str):
                    with contextlib.suppress(Exception):
                        self.added = datetime.fromisoformat(dt_val)
                elif isinstance(dt_val, list) and dt_val:
                    with contextlib.suppress(Exception):
                        self.added = datetime.fromisoformat(dt_val[0])

        # Defensive updated extraction
        updated_node = site.find(text="Updated")
        self.updated = self.added
        try:
            if (
                updated_node
                and hasattr(updated_node, "parent")
                and updated_node.parent
                and hasattr(updated_node.parent, "parent")
                and updated_node.parent.parent
            ):
                parent = updated_node.parent.parent
                if hasattr(parent, "time") and parent.time and "datetime" in getattr(parent.time, "attrs", {}):
                    dt_val = parent.time["datetime"]
                    if isinstance(dt_val, str):
                        self.updated = datetime.fromisoformat(dt_val)
                    elif isinstance(dt_val, list) and dt_val:
                        self.updated = datetime.fromisoformat(dt_val[0])
        except (ValueError, TypeError):
            self.updated = self.added

        # Defensive size extraction
        size_node = site.find(text="Size")
        self.size = ""
        if (
            size_node
            and hasattr(size_node, "parent")
            and size_node.parent
            and hasattr(size_node.parent, "parent")
            and size_node.parent.parent
        ):
            parent = size_node.parent.parent
            if hasattr(parent, "span") and parent.span and hasattr(parent.span, "text"):
                self.size = parent.span.text.strip()

        # Defensive checksum extraction
        checksum_node = site.find(text="MD5 Hash")
        self.checksum = ""
        if (
            checksum_node
            and hasattr(checksum_node, "parent")
            and checksum_node.parent
            and hasattr(checksum_node.parent, "parent")
            and checksum_node.parent.parent
        ):
            parent = checksum_node.parent.parent
            if hasattr(parent, "span") and parent.span and hasattr(parent.span, "text"):
                self.checksum = parent.span.text.strip()

        # Defensive download_url extraction
        mirror_tag = site.find(id="downloadmirrorstoggle")
        self.download_url = ""
        if mirror_tag and isinstance(mirror_tag, Tag) and "href" in mirror_tag.attrs:
            val = mirror_tag["href"]
            if isinstance(val, str):
                self.download_url = val.strip()

    def get_download_url(self) -> str:
        """Retrieve the actual download link."""
        download = self.BASE_URL + str(self.download_url)
        mirror_site = BeautifulSoup(requests.get(download, timeout=30).text, "html.parser")
        target_href = ""
        if mirror_site.body and hasattr(mirror_site.body, "p") and mirror_site.body.p:
            p_tag = mirror_site.body.p
            if hasattr(p_tag, "a") and p_tag.a:
                a_tag = p_tag.a
                if hasattr(a_tag, "__getitem__") and "href" in getattr(a_tag, "attrs", {}):
                    val = a_tag["href"]
                    if isinstance(val, str):
                        target_href = val
        target_url = self.BASE_URL + str(target_href)
        print(f"Got {target_url=}")
        return target_url


@dataclass
class SourceGitHub(SourceBase):
    """Class for handling mods from github."""

    BASE_URL = "https://www.github.com"
    BASE_API_URL = "https://api.github.com"
    html_url: str

    @classmethod
    def parse_api_url(cls, url: str) -> str:
        if cls.BASE_API_URL in url:
            return url
        user = url.split("/")[-2]
        project = url.split("/")[-1]
        return f"https://api.github.com/repos/{user}/{project}"

    @classmethod
    def from_url(cls, url: str, folders: list[str] | None = None) -> "SourceGitHub":
        """Initialize from url."""
        api_url = cls.parse_api_url(url)
        content = requests.get(api_url, timeout=30).text
        x = json.loads(content)

        installed_dt = datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc)
        if folders is None:
            folders = []

        return cls(
            title=x.get("name"),
            filename=f"{x.get('name')}_git.zip",
            description=x.get("description"),
            added=datetime.fromisoformat(x.get("created_at")),
            updated=datetime.fromisoformat(x.get("pushed_at")),
            size=f"{x.get('size')}kb",
            checksum="",
            html_url=x.get("html_url"),
            url=x.get("url"),
            download_url=f"{api_url}/zipball",
            foldername=x.get("name"),
            folders=folders,
            installed=installed_dt,
        )

    @classmethod
    def from_dict(cls, entry: dict[str, str]) -> "SourceGitHub":
        def safe_str(val: object) -> str:
            return val if isinstance(val, str) and val is not None else ""

        def safe_list(val: object) -> list[str]:
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                try:
                    result = ast.literal_eval(val)
                    if isinstance(result, list):
                        return result
                except (ValueError, SyntaxError):
                    pass
            return []

        def safe_datetime(val: object) -> datetime:
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val)
                except (ValueError, TypeError):
                    pass
            return datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc)

        title = safe_str(entry.get("title"))
        filename = safe_str(entry.get("filename"))
        foldername = safe_str(entry.get("foldername"))
        folders = safe_list(entry.get("folders"))
        description = safe_str(entry.get("description"))
        installed = safe_datetime(entry.get("installed"))
        added = safe_datetime(entry.get("added"))
        updated = safe_datetime(entry.get("updated")) if entry.get("updated") else added
        size = safe_str(entry.get("size"))
        checksum = safe_str(entry.get("checksum"))
        url = safe_str(entry.get("url"))
        html_url = safe_str(entry.get("html_url"))
        download_url = safe_str(entry.get("download_url"))

        return cls(
            title=title,
            filename=filename,
            foldername=foldername,
            folders=folders,
            description=description,
            installed=installed,
            added=added,
            updated=updated,
            size=size,
            checksum=checksum,
            url=url,
            html_url=html_url,
            download_url=download_url,
        )

    def update(self) -> None:
        """Update object with information from source."""
        content = requests.get(self.url, timeout=30).text
        x = json.loads(content)
        self.title = x.get("name") if x.get("name") is not None else ""
        if not self.foldername:
            self.foldername = self.filename.rsplit(".", 1)[0]
        self.description = x.get("description") if x.get("description") is not None else ""
        self.added = (
            datetime.fromisoformat(x.get("created_at"))
            if x.get("created_at") is not None
            else datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc)
        )

        try:
            self.updated = datetime.fromisoformat(x.get("pushed_at")) if x.get("pushed_at") is not None else self.added
        except (ValueError, TypeError):
            self.updated = self.added
        self.size = str(x.get("size")) if x.get("size") is not None else ""
        self.checksum = ""
        self.download_url = f"{x.get('url')}/zipball" if x.get("url") is not None else ""

    def get_download_url(self) -> str:
        """Retrieve the actual download link."""
        return self.download_url


def get_class_classifier(url: str) -> SourceBase:
    if "moddb.com" in url:
        # Return a minimal instance with required fields
        return SourceModdb(
            title="",
            filename="",
            foldername="",
            folders=[],
            description="",
            installed=datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc),
            added=datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc),
            updated=datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc),
            size="",
            checksum="",
            url=url,
            download_url="",
        )
    if "github.com" in url:
        return SourceGitHub(
            title="",
            filename="",
            foldername="",
            folders=[],
            description="",
            installed=datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc),
            added=datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc),
            updated=datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc),
            size="",
            checksum="",
            url=url,
            html_url="",
            download_url="",
        )
    # Fallback: return a minimal SourceBase instance
    return SourceBase(
        title="",
        filename="",
        foldername="",
        folders=[],
        description="",
        installed=datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc),
        added=datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc),
        updated=datetime(1900, 1, 1, tzinfo=__import__("datetime").timezone.utc),
        size="",
        checksum="",
        url=url,
        download_url="",
    )
