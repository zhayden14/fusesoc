# Copyright FuseSoC contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import logging
import os.path
import shutil
import subprocess
import tempfile
from argparse import Namespace
from pathlib import Path

from test_common import cache_root, cores_root, library_root

from fusesoc.config import Config

build_root = "test_build_root"

EXAMPLE_CONFIG = """
[main]
build_root = {build_root}
cache_root = {cache_root}
library_root = {library_root}

[library.test_lib]
location = {cores_root}
auto-sync = {auto_sync}
sync-uri = {sync_uri}
sync-type = {sync_type}
"""

sync_uri = "https://github.com/fusesoc/fusesoc-cores"


def test_library_location():
    from fusesoc.main import _get_core, init_coremanager

    with tempfile.NamedTemporaryFile(mode="w+") as tcf:
        tcf.write(
            EXAMPLE_CONFIG.format(
                build_root=build_root,
                cache_root=cache_root,
                cores_root=cores_root,
                library_root=library_root,
                auto_sync="false",
                sync_uri=sync_uri,
                sync_type="git",
            )
        )
        tcf.flush()

        conf = Config(tcf.name)

    cm = init_coremanager(conf, [])

    _get_core(cm, "mor1kx-generic")
    _get_core(cm, "atlys")


def test_library_add(caplog):
    import tempfile

    from fusesoc.coremanager import CoreManager
    from fusesoc.librarymanager import LibraryManager
    from fusesoc.main import add_library

    with tempfile.TemporaryDirectory() as tcd:
        tcf = Path(tcd) / "fusesoc.conf"
        clone_target = tempfile.mkdtemp(prefix="library_add_")
        library_root = tempfile.mkdtemp(prefix="library_add_")
        conf = Config(file=tcf)
        conf.library_root = library_root
        cm = CoreManager(conf)
        args = Namespace()

        args.name = "fusesoc-cores"
        args.location = clone_target
        args.config = tcf
        args.no_auto_sync = False
        vars(args)["sync-uri"] = sync_uri

        add_library(cm, args)

        expected = """[library.fusesoc-cores]
location = {}
sync-uri = https://github.com/fusesoc/fusesoc-cores
sync-type = git
auto-sync = true""".format(
            os.path.abspath(clone_target)
        )

        result = tcf.read_text().strip()

        assert expected == result

    # Will be changing working dir because we're about to clone a library
    cwd = os.getcwd()
    tcd = tempfile.TemporaryDirectory()
    os.chdir(tcd.name)
    tcf = Path(tcd.name) / "fusesoc.conf"

    args.config = tcf
    args.location = None
    vars(args)["sync-type"] = "git"

    expected = """[library.fusesoc-cores]
location = fusesoc_libraries/fusesoc-cores
sync-uri = https://github.com/fusesoc/fusesoc-cores
sync-type = git
auto-sync = true"""

    add_library(cm, args)

    result = tcf.read_text().strip()

    # FIXME: Temporary fix for windows tests
    assert expected == result.replace("\\", "/")
    os.chdir(cwd)

    with tempfile.TemporaryDirectory() as tcd:
        tcf = Path(tcd) / "fusesoc.conf"

        args.config = tcf
        vars(args)["sync-type"] = "local"
        vars(args)["sync-uri"] = "tests/capi2_cores"
        args.location = None

        with caplog.at_level(logging.INFO):
            add_library(cm, args)

        assert (
            "Interpreting sync-uri 'tests/capi2_cores' as location for local provider."
            in caplog.text
        )


def test_library_update(caplog):
    from fusesoc.main import init_coremanager, init_logging, update

    clone_target = Path(tempfile.mkdtemp())

    subprocess.call(["git", "clone", sync_uri, clone_target])

    with tempfile.NamedTemporaryFile(mode="w+") as tcf:
        tcf.write(
            EXAMPLE_CONFIG.format(
                build_root=build_root,
                cache_root=cache_root,
                cores_root=clone_target,
                library_root=library_root,
                auto_sync="false",
                sync_uri=sync_uri,
                sync_type="git",
            )
        )
        tcf.flush()

        conf = Config(tcf.name)

    args = Namespace()

    init_logging(False, False)
    cm = init_coremanager(conf, [])

    # TODO find a better way to set up these defaults
    args.libraries = []

    with caplog.at_level(logging.INFO):
        update(cm, args)

    assert "test_lib : auto-sync disabled. Ignoring update" in caplog.text

    caplog.clear()

    args.libraries = ["test_lib"]

    with caplog.at_level(logging.INFO):
        update(cm, args)

    assert "test_lib : Updating..." in caplog.text

    caplog.clear()

    args.libraries = []
    _library = cm._lm.get_library("test_lib")
    _library.auto_sync = True

    with caplog.at_level(logging.INFO):
        update(cm, args)

    assert "test_lib : Updating..." in caplog.text

    caplog.clear()

    tcf.close()

    _library.sync_type = "local"

    args.libraries = []

    with caplog.at_level(logging.INFO):
        update(cm, args)

    assert "test_lib : sync-type is local. Ignoring update" in caplog.text
