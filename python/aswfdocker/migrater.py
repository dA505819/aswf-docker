# SPDX-License-Identifier: Apache-2.0
"""
Migration of ASWF docker images between docker organisations
"""
import logging
import subprocess
import typing

from aswfdocker import constants, utils


logger = logging.getLogger(__name__)


class MigrateInfo:
    def __init__(self, image, version, source, destination):
        self.image = image
        self.version = version
        self.source = source
        self.destination = destination


class Migrater:
    def __init__(self, from_org: str, to_org: str):
        self.from_org = from_org
        self.to_org = to_org
        self.migration_list: typing.List[MigrateInfo] = []
        self.cmds: typing.List[str] = []

    def gather(self, package: str, version: str):
        for pkg, versions in constants.VERSIONS[constants.ImageType.PACKAGE].items():
            image = "ci-package-" + pkg
            if not package or package == pkg:
                for v in versions:
                    major_version = v.split(".")[0]
                    if not version or version == major_version:
                        self.migration_list.append(
                            MigrateInfo(
                                image,
                                v,
                                f"{constants.DOCKER_REGISTRY}/{self.from_org}/{image}:{v}",
                                f"{constants.DOCKER_REGISTRY}/{self.to_org}/{image}:{v}",
                            )
                        )

    def migrate(self, dry_run: bool):
        for minfo in self.migration_list:
            if dry_run:
                logger.info("Migrating %s -> %s", minfo.source, minfo.destination)
            else:
                logger.info("Would migrate %s -> %s", minfo.source, minfo.destination)

            self.cmds.append(f"docker pull {minfo.source}")
            self.cmds.append(f"docker tag {minfo.source} {minfo.destination}")

            major_version = utils.get_major_version(minfo.version)
            version_info = constants.VERSION_INFO[major_version]
            tags = version_info.get_tags(minfo.version, self.to_org, minfo.image)
            if len(tags) > 1:
                for tag in tags:
                    if tag != minfo.destination:
                        self.cmds.append(f"docker tag {minfo.destination} {tag}")

            self.cmds.append(f"docker push {minfo.destination}")

        if logger.isEnabledFor(logging.DEBUG):
            list(map(logger.debug, self.cmds))

        if not dry_run:
            for cmd in self.cmds:
                subprocess.run(cmd, shell=True, check=True)
