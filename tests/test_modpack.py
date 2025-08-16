import os
import shutil
import tempfile
from pathlib import Path

import pytest

from modpack import ModPack


@pytest.fixture
def temp_dirs():
    src = Path(tempfile.mkdtemp())
    dst = Path(tempfile.mkdtemp())
    yield src, dst
    shutil.rmtree(src)
    shutil.rmtree(dst)


def test_convert_from_input_to_output_basic(temp_dirs):
    src, dst = temp_dirs
    (src / "foo.txt").write_text("bar")
    pack = ModPack(src, dst)
    out_path = pack.convert_from_input_to_output(src / "foo.txt")
    assert out_path == dst / "foo.txt"


def test_convert_from_input_to_output_subdir(temp_dirs):
    src, dst = temp_dirs
    subdir = src / "sub"
    subdir.mkdir()
    (subdir / "baz.txt").write_text("baz")
    pack = ModPack(src, dst)
    out_path = pack.convert_from_input_to_output(subdir / "baz.txt")
    assert out_path == dst / "sub" / "baz.txt"


def test_create_folder(temp_dirs):
    src, dst = temp_dirs
    subdir = src / "subfolder"
    subdir.mkdir()
    pack = ModPack(src, dst)
    pack.create_folder(subdir)
    assert (dst / "subfolder").exists()
    assert (dst / "subfolder").is_dir()


def test_handle_symlinking(temp_dirs):
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


def test_add_mod(temp_dirs):
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


def test_initialize_configs_regular_and_fomod(temp_dirs):
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
    from modpack import initialize_configs

    initialize_configs(profile_payload, mod_list, src, dst)
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
