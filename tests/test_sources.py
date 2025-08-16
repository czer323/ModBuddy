# pylint: disable=redefined-outer-name
from datetime import datetime, timezone
from pathlib import Path
import pytest
from modbuddy.sources import (
    SourceModdb,
    SourceGitHub,
    SourceBase,
    get_class_classifier,
)

@pytest.fixture
def mock_moddb_html():
    """Provides mock HTML content for a ModDB page."""
    return """
    <html>
    <head><title>Test Mod for ModDB</title></head>
    <body>
        <div><div><span>Filename</span><span>test_mod.zip</span></div></div>
        <div><div><time datetime="2023-01-01T12:00:00Z">Added</time></div></div>
        <div><div><time datetime="2023-01-02T12:00:00Z">Updated</time></div></div>
        <div><div><span>Size</span><span>123 MB</span></div></div>
        <div><div><span>MD5 Hash</span><span>abcdef1234567890</span></div></div>
        <meta name="description" content="A test mod from ModDB.">
        <a id="downloadmirrorstoggle" href="/downloads/start/12345"></a>
    </body>
    </html>
    """

@pytest.fixture
def mock_github_json():
    """Provides mock JSON content for a GitHub API response."""
    return {
        "name": "Test-Repo",
        "description": "A test repository for ModBuddy.",
        "created_at": "2023-01-01T00:00:00Z",
        "pushed_at": "2023-01-02T00:00:00Z",
        "size": 1234,
        "html_url": "https://github.com/test/Test-Repo",
        "url": "https://api.github.com/repos/test/Test-Repo",
    }

class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error {self.status_code}")

    def iter_content(self, chunk_size=1024):
        yield self.text.encode('utf-8')

def test_get_class_classifier_moddb():
    """Tests that a ModDB URL returns a SourceModdb class."""
    url = "https://www.moddb.com/mods/stalker-anomaly"
    classifier = get_class_classifier(url)
    assert isinstance(classifier, SourceModdb)

def test_get_class_classifier_github():
    """Tests that a GitHub URL returns a SourceGitHub class."""
    url = "https://github.com/someuser/someproject"
    classifier = get_class_classifier(url)
    assert isinstance(classifier, SourceGitHub)

def test_get_class_classifier_other():
    """Tests that an unknown URL returns a SourceBase class."""
    url = "https://www.someotherwebsite.com/mod"
    classifier = get_class_classifier(url)
    assert isinstance(classifier, SourceBase)
    assert not isinstance(classifier, SourceModdb)
    assert not isinstance(classifier, SourceGitHub)

def test_source_moddb_from_url(monkeypatch, mock_moddb_html):
    """Tests parsing of a ModDB URL with mocked HTML."""
    def mock_get(*args, **kwargs):
        return MockResponse(mock_moddb_html)
    monkeypatch.setattr("requests.get", mock_get)

    source = SourceModdb.from_url("https://www.moddb.com/mods/test-mod")
    assert source.title == "Test Mod for ModDB"
    assert source.filename == "test_mod.zip"
    assert source.description == "A test mod from ModDB."
    assert source.added == datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert source.updated == datetime(2023, 1, 2, 12, 0, tzinfo=timezone.utc)
    assert source.size == "123 MB"
    assert source.checksum == "abcdef1234567890"
    assert source.download_url == "/downloads/start/12345"

def test_source_github_from_url(monkeypatch, mock_github_json):
    """Tests parsing of a GitHub URL with mocked JSON."""
    def mock_get(*args, **kwargs):
        return MockResponse(str(mock_github_json).replace("'", '"'))
    monkeypatch.setattr("requests.get", mock_get)

    source = SourceGitHub.from_url("https://github.com/test/Test-Repo")
    assert source.title == "Test-Repo"
    assert source.description == "A test repository for ModBuddy."
    assert source.added == datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert source.updated == datetime(2023, 1, 2, 0, 0, tzinfo=timezone.utc)
    assert source.size == "1234kb"
    assert source.download_url == "https://api.github.com/repos/test/Test-Repo/zipball"

def test_source_base_check_if_file_exists(tmp_path: Path):
    """Tests the checksum verification for a downloaded file."""
    fixed_dt = datetime(2023, 1, 1, tzinfo=timezone.utc)
    source = SourceBase(
        title="Test", filename="test.zip", foldername="test", folders=[],
        description="", installed=fixed_dt, added=fixed_dt,
        updated=fixed_dt, checksum="27565f9a57c128674736aa644012ce67",
        size="1KB", url="", download_url=""
    )
    test_file = tmp_path / "test.zip"
    test_file.write_bytes(b"test_content")

    assert source.check_if_file_exists(test_file)
    assert not source.check_if_file_exists(tmp_path / "nonexistent.zip")

    source.checksum = "wrong_checksum"
    assert not source.check_if_file_exists(test_file)



def test_source_moddb_from_dict():
    """Tests creating a SourceModdb object from a dictionary."""
    data = {
        "title": "Test Mod", "filename": "test.zip", "foldername": "test",
        "folders": "['folder1', 'folder2']", "description": "A test mod.",
        "installed": "2023-01-01T00:00:00+00:00",
        "added": "2023-01-02T00:00:00+00:00",
        "updated": "2023-01-03T00:00:00+00:00", "size": "1 MB",
        "checksum": "12345", "url": "http://moddb.com/test", "download_url": "http://moddb.com/download"
    }
    source = SourceModdb.from_dict(data)
    assert source.title == "Test Mod"
    assert source.folders == ["folder1", "folder2"]
    assert source.updated == datetime(2023, 1, 3, 0, 0, tzinfo=timezone.utc)

def test_source_github_from_dict():
    """Tests creating a SourceGitHub object from a dictionary."""
    data = {
        "title": "Test Repo", "filename": "repo.zip", "foldername": "repo",
        "folders": "['src', 'docs']", "description": "A test repo.",
        "installed": "2023-01-01T00:00:00+00:00",
        "added": "2023-01-02T00:00:00+00:00",
        "updated": "2023-01-03T00:00:00+00:00", "size": "2 MB",
        "checksum": "", "url": "http://github.com/api/test",
        "html_url": "http://github.com/test", "download_url": "http://github.com/zipball"
    }
    source = SourceGitHub.from_dict(data)
    assert source.title == "Test Repo"
    assert source.folders == ["src", "docs"]
    assert source.html_url == "http://github.com/test"
