# Copyright FuseSoC contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import os.path
import tempfile
from pathlib import Path

import pytest
from test_common import cache_root, cores_root, library_root

from fusesoc.config import Config

build_root = "test_build_root"

EXAMPLE_CONFIG = """
[main]
build_root = {build_root}
cache_root = {cache_root}
cores_root = {cores_root}
library_root = {library_root}

[library.test_lib]
location = {library_root}/test_lib
auto-sync = false
sync-uri = https://github.com/fusesoc/fusesoc-cores
"""


def test_config():
    tcd = tempfile.TemporaryDirectory()
    tcf = Path(tcd.name) / "fusesoc.conf"
    tcf.write_text(
        EXAMPLE_CONFIG.format(
            build_root=build_root,
            cache_root=cache_root,
            cores_root=cores_root,
            library_root=library_root,
        )
    )

    conf = Config(tcf)

    assert conf.library_root == Path(library_root).expanduser().resolve()


def test_config_relative_path():
    with tempfile.TemporaryDirectory() as td:
        config_path = Path(td) / "fusesoc.conf"
        config_path = config_path.expanduser().resolve()
        with open(config_path, "w") as tcf:
            tcf.write(
                EXAMPLE_CONFIG.format(
                    build_root="build_root",
                    cache_root="cache_root",
                    cores_root="cores_root",
                    library_root="library_root",
                )
            )

        conf = Config(config_path)
        for name in ["build_root", "cache_root", "library_root"]:
            abs_td = Path(td).expanduser().resolve()
            assert getattr(conf, name) == abs_td / name


def test_config_libraries():
    tcd = tempfile.TemporaryDirectory()
    tcf = Path(tcd.name) / "fusesoc.conf"
    tcf.write_text(
        EXAMPLE_CONFIG.format(
            build_root=build_root,
            cache_root=cache_root,
            cores_root=cores_root,
            library_root=library_root,
        )
    )

    conf = Config(tcf)

    lib = None
    for library in conf.libraries:
        if library.name == "test_lib":
            lib = library
    assert lib

    assert Path(lib.location) == Path(library_root) / "test_lib"
    assert lib.sync_uri == "https://github.com/fusesoc/fusesoc-cores"
    assert not lib.auto_sync
