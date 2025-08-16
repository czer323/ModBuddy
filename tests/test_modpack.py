# pylint: disable=redefined-outer-name

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from modbuddy.modpack import ModPack, initialize_mod_configs


@pytest.fixture
def temp_dirs() -> Generator[tuple[Path, Path], None, None]:
    """
    Creates temporary source and destination directories for use in tests.

    Yields:
        tuple[Path, Path]: Source and destination directory paths.

    """
    src = Path(tempfile.mkdtemp())
    dst = Path(tempfile.mkdtemp())
    yield src, dst
    shutil.rmtree(src)
    shutil.rmtree(dst)


def test_convert_from_input_to_output_basic(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that a file in the source root is correctly mapped to the output root."""
    src, dst = temp_dirs
    (src / "foo.txt").write_text("bar")
    pack = ModPack(src, dst)
    out_path = pack.convert_from_input_to_output(src / "foo.txt")
    assert out_path == dst / "foo.txt"


def test_convert_from_input_to_output_subdir(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that a file in a source subdirectory is mapped to the corresponding output subdirectory."""
    src, dst = temp_dirs
    subdir = src / "sub"
    subdir.mkdir()
    (subdir / "baz.txt").write_text("baz")
    pack = ModPack(src, dst)
    out_path = pack.convert_from_input_to_output(subdir / "baz.txt")
    assert out_path == dst / "sub" / "baz.txt"


def test_create_folder(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that a source subfolder is created in the output directory."""
    src, dst = temp_dirs
    subdir = src / "subfolder"
    subdir.mkdir()
    pack = ModPack(src, dst)
    pack.create_folder(subdir)
    assert (dst / "subfolder").exists()
    assert (dst / "subfolder").is_dir()


def test_handle_symlinking(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that a file is hardlinked from source to output and retains its content and inode."""
    src, dst = temp_dirs
    file = src / "file.txt"
    file.write_text("data")
    pack = ModPack(src, dst)
    pack.create_folder(src)
    pack.handle_symlinking(file)
    out_file = dst / "file.txt"
    assert out_file.exists()
    assert out_file.read_text() == "data"
    # Check hardlink (same inode on Unix)
    if hasattr(os, "stat") and hasattr(os, "link"):
        assert os.stat(str(file)).st_ino == os.stat(str(out_file)).st_ino


def test_add_mod(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that all files and subdirectories in the source are added to the output directory."""
    src, dst = temp_dirs
    (src / "a.txt").write_text("A")
    (src / "b.txt").write_text("B")
    sub = src / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("C")
    pack = ModPack(src, dst)
    pack.add_mod()
    assert (dst / "a.txt").exists()
    assert (dst / "b.txt").exists()
    assert (dst / "sub" / "c.txt").exists()
    assert (dst / "sub").is_dir()
    assert (dst / "sub" / "c.txt").read_text() == "C"


def test_initialize_configs_regular_and_fomod(temp_dirs: tuple[Path, Path]) -> None:
    """
    Tests initialization of regular and fomod mods, verifying correct file and option placement in output.

    Ensures both regular mod files and fomod option files are created in the expected output structure.

    """
    src, dst = temp_dirs
    # Regular mod
    mod1 = src / "mod1"
    mod1.mkdir()
    (mod1 / "file1.txt").write_text("mod1data")
    # Fomod mod
    mod2 = src / "mod2"
    mod2.mkdir()
    (mod2 / "optA.txt").write_text("optAdata")
    (mod2 / "optB.txt").write_text("optBdata")
    # Mod list
    mod_list = {"RegularMod": "mod1", "FomodMod": "mod2"}
    # Profile payload
    profile_payload = [
        {"name": "RegularMod", "enabled": True, "type": "regular"},
        {
            "name": "FomodMod",
            "enabled": True,
            "type": "fomod",
            "options": {
                "A": {"source": "optA.txt", "destination": "A"},
                "B": {"source": "optB.txt", "destination": "B"},
            },
        },
    ]
    initialize_mod_configs(profile_payload, mod_list, src, dst)

    # Check regular mod file
    assert (dst / "file1.txt").exists()
    assert (dst / "file1.txt").read_text() == "mod1data"
    # Check fomod options
    assert (dst / "A").exists()
    assert (dst / "A").is_dir()
    assert (dst / "A" / "optA.txt").exists()
    assert (dst / "A" / "optA.txt").read_text() == "optAdata"
    assert (dst / "B").exists()
    assert (dst / "B").is_dir()
    assert (dst / "B" / "optB.txt").exists()
    assert (dst / "B" / "optB.txt").read_text() == "optBdata"


def test_add_mod_empty_src(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that add_mod runs without error when the source directory is empty."""
    src, dst = temp_dirs
    pack = ModPack(src, dst)
    pack.add_mod()
    assert not any(dst.iterdir())


def test_add_mod_with_existing_files(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that add_mod correctly overwrites existing files in the destination directory."""
    src, dst = temp_dirs
    (src / "a.txt").write_text("new_A")
    (dst / "a.txt").write_text("old_A")
    pack = ModPack(src, dst)
    pack.add_mod()
    assert (dst / "a.txt").read_text() == "new_A"


def test_convert_from_input_to_output_case_insensitive(temp_dirs: tuple[Path, Path]) -> None:
    """Tests the case_sensitive=False option in convert_from_input_to_output."""
    src, dst = temp_dirs
    pack = ModPack(src, dst, case_sensitive=False)
    in_path = src / "Foo.txt"
    out_path = pack.convert_from_input_to_output(in_path)
    assert out_path == dst / "foo.txt"


def test_initialize_mod_configs_disabled_mod(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that disabled mods are not installed."""
    src, dst = temp_dirs
    mod1 = src / "mod1"
    mod1.mkdir()
    (mod1 / "file1.txt").write_text("mod1data")
    mod_list = {"DisabledMod": "mod1"}
    profile_payload = [{"name": "DisabledMod", "enabled": False, "type": "regular"}]
    initialize_mod_configs(profile_payload, mod_list, src, dst)
    assert not (dst / "file1.txt").exists()


def test_initialize_mod_configs_missing_mod_path(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that a mod is skipped if its path is not in the mod_list."""
    src, dst = temp_dirs
    profile_payload = [{"name": "MissingMod", "enabled": True, "type": "regular"}]
    initialize_mod_configs(profile_payload, {}, src, dst)
    assert not any(dst.iterdir())


def test_initialize_mod_configs_empty_fomod_options(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that initialize_mod_configs handles fomod mods with no options."""
    src, dst = temp_dirs
    mod1 = src / "mod1"
    mod1.mkdir()
    mod_list = {"FomodMod": "mod1"}
    profile_payload = [
        {"name": "FomodMod", "enabled": True, "type": "fomod", "options": {}}
    ]
    initialize_mod_configs(profile_payload, mod_list, src, dst)
    assert not any(dst.iterdir())


def test_handle_symlinking_existing_file(temp_dirs: tuple[Path, Path]) -> None:
    """Tests that handle_symlinking correctly replaces an existing file."""
    src, dst = temp_dirs
    file = src / "file.txt"
    file.write_text("new_data")
    out_file = dst / "file.txt"
    out_file.write_text("old_data")
    pack = ModPack(src, dst)
    pack.handle_symlinking(file)
    assert out_file.read_text() == "new_data"
