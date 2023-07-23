#!/usr/bin/env python3

from virtualmonorepo.log import logger
from virtualmonorepo import ioutils


class VmrExtensions:

    def __init__(self):
        pass

    def notify_invalidation(self):
        pass


class FileBasedVmrExtensions(VmrExtensions):
    extensions_folder_path = "{vmr_config_folder}/{extensions_folder_name}"
    invalidation_marker_file_path = "{vmr_config_folder}/{extensions_folder_name}/{invalidation_marker_file_name}"

    def __init__(self):
        home_folder_path = ioutils.get_home_directory()
        self.config_folder_path = "{}/.config/wix/virtual-monorepo".format(
            home_folder_path)
        self.extensions_folder_name = "ext"

        self.named_params = {
            "vmr_config_folder": self.config_folder_path,
            "extensions_folder_name": self.extensions_folder_name,
            "invalidation_marker_file_name": "vmr-invalidation-marker",
        }

    def notify_invalidation(self):
        ext_folder_path = self.extensions_folder_path.format(
            **self.named_params)
        ioutils.create_directory(ext_folder_path)
        file_path = self.invalidation_marker_file_path.format(
            **self.named_params)
        ioutils.write_file(file_path, "")


class DryRunVmrExtensions(VmrExtensions):

    def notify_invalidation(self):
        logger.info("Skipping on notifying that an invalidation took place")
        pass
