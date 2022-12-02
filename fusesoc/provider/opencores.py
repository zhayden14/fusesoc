# Copyright FuseSoC contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import logging
import sys

from fusesoc.provider.provider import Provider
from fusesoc.utils import Launcher, cygpath, is_mingw

logger = logging.getLogger(__name__)

REPO_PATH = "http://opencores.org/ocsvn/{}/{}/{}"


class Opencores(Provider):
    def _checkout(self, local_dir):
        repo_name = self.config.get("repo_name")
        repo_path = REPO_PATH.format(repo_name, repo_name, self.config.get("repo_root"))
        revision_number = self.config.get("revision")
        logger.info("Downloading " + repo_name + " from OpenCores")

        if is_mingw():
            logger.debug("Using cygpath translation")
            local_dir = cygpath(local_dir)

        # FIXME: Added --non-interactive --trust-server-cert so tests can pass on new machines.
        #        This is probably a bad move long-term. Need HowTo about authorizing repos.
        Launcher(
            "svn",
            [
                "co",
                "-q",
                "--no-auth-cache",
                "--non-interactive",
                "--trust-server-cert",
                "-r",
                revision_number,
                "--username",
                "orpsoc",
                "--password",
                "orpsoc",
                repo_path,
                local_dir,
            ],
        ).run()
