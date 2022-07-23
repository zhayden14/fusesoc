# Copyright FuseSoC contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import configparser
import logging
import os
import sys
from configparser import ConfigParser as CP
from pathlib import Path
from typing import Optional

from fusesoc.librarymanager import Library

logger = logging.getLogger(__name__)


class Config:
    _path: Path
    # build_root: Path
    # cache_root: Path
    # systems_root: Path
    # library_root: Path
    # libraries: List[Path]

    def __init__(
        self, path: Optional[os.PathLike] = None, file: Optional[os.PathLike] = None
    ):
        self.build_root = None
        self.cache_root = None
        cores_root = []
        systems_root = []
        self.library_root = None
        self.libraries = []

        config = CP()
        if file is None:
            if path is None:
                xdg_config_home = os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")
                xdg_config_home = Path(xdg_config_home).expanduser().resolve()
                config_files = [
                    Path("/etc/fusesoc/fusesoc.conf"),
                    xdg_config_home / "fusesoc/fusesoc.conf",
                    Path("fusesoc.conf"),
                ]
            else:
                path = Path(path).resolve()
                logger.debug(f"Using config file '{path}'")
                if not path.is_file():
                    with open(path, "a"):
                        pass
                config_files = [path]

            logger.debug(
                "Looking for config files from "
                + ":".join([str(cf) for cf in config_files])
            )
            files_read = config.read(config_files)
            logger.debug("Found config files in " + ":".join(files_read))
            if files_read:
                self._path = Path(files_read[-1])
        else:
            logger.debug("Using supplied config file")
            file = Path(file)
            config.read(file)
            self._path = file

        for item in ["build_root", "cache_root", "systems_root", "library_root"]:
            try:
                setattr(
                    self, item, Path(config.get("main", item)).expanduser().resolve()
                )
                if item == "systems_root":
                    systems_root = [
                        Path(config.get("main", item)).expanduser().resolve()
                    ]
                    logger.warning(
                        "The systems_root option in fusesoc.conf is deprecated. Please migrate to libraries instead"
                    )
            except configparser.NoOptionError:
                pass
            except configparser.NoSectionError:
                pass

        try:
            cores_root = config.get("main", "cores_root")
            if cores_root:
                cores_root = [cores_root]
            logger.warning(
                "The cores_root option in fusesoc.conf is deprecated. Please migrate to libraries instead"
            )
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            pass

        # Set fallback values
        if self.build_root is None:
            self.build_root = Path("build").resolve()
        if self.cache_root is None:
            xdg_cache_home = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
            xdg_cache_home = Path(xdg_cache_home).expanduser().resolve()
            self.cache_root = xdg_cache_home / "fusesoc"
            self.cache_root.mkdir(exist_ok=True, parents=True)
        if not cores_root and Path("cores").exists():
            cores_root = [Path("cores").resolve()]
        if (not systems_root) and Path("systems").exists():
            systems_root = [Path("systems").resolve()]
        if self.library_root is None:
            xdg_data_home = (
                os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"
            )
            xdg_data_home = Path(xdg_data_home).expanduser().resolve()
            self.library_root = xdg_data_home / "fusesoc"

        # Parse library sections
        libraries = []
        library_sections = [x for x in config.sections() if x.startswith("library")]
        for section in library_sections:
            name = section.partition(".")[2]
            try:
                location = config.get(section, "location")
            except configparser.NoOptionError:
                location = self.library_root / name

            try:
                auto_sync = config.getboolean(section, "auto-sync")
            except configparser.NoOptionError:
                auto_sync = True
            except ValueError as e:
                _s = "Error parsing auto-sync '{}'. Ignoring library '{}'"
                logger.warning(_s.format(str(e), name))
                continue

            try:
                sync_uri = config.get(section, "sync-uri")
            except configparser.NoOptionError:
                # sync-uri is absent for local libraries
                sync_uri = None

            try:
                sync_type = config.get(section, "sync-type")
            except configparser.NoOptionError:
                # sync-uri is absent for local libraries
                sync_type = None
            libraries.append(Library(name, location, sync_type, sync_uri, auto_sync))
        # Get the environment variable for further cores
        env_cores_root = []
        if os.getenv("FUSESOC_CORES"):
            env_cores_root = os.getenv("FUSESOC_CORES").split(":")
            env_cores_root.reverse()
        env_cores_root = [Path(d) for d in env_cores_root]

        for root in cores_root + systems_root + env_cores_root:
            self.libraries.append(Library(root, root))

        self.libraries += libraries

        logger.debug(f"cache_root={self.cache_root}")
        logger.debug(f"library_root={self.library_root}")

    def add_library(self, library):
        from fusesoc.provider import get_provider

        if not hasattr(self, "_path"):
            raise RuntimeError("No FuseSoC config file found - can't add library")
        section_name = "library." + library.name

        config = CP()
        config.read(self._path)

        if section_name in config.sections():
            logger.warning(
                "Not adding library. {} already exists in configuration file".format(
                    library.name
                )
            )
            return

        config.add_section(section_name)

        config.set(section_name, "location", library.location)

        if library.sync_type:
            config.set(section_name, "sync-uri", library.sync_uri)
            config.set(section_name, "sync-type", library.sync_type)
            _auto_sync = "true" if library.auto_sync else "false"
            config.set(section_name, "auto-sync", _auto_sync)

        try:
            provider = get_provider(library.sync_type)
        except ImportError as e:
            raise RuntimeError("Invalid sync-type '{}'".format(library["sync-type"]))

        provider.init_library(library)

        with open(self._path, "w") as conf_file:
            config.write(conf_file)
