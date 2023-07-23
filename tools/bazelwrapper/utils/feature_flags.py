import os
from typing import Optional

from bazelwrapper.context import Context


class Flag:
    """
    Flag implements a cascading flag that can be specified by any of the following combined:
    - CLI argument
    - Marker file in the config dir that's in context
    - An environment variable

    The flag is considered on if any of the above is present, regardless of their value.
    """

    def __init__(self,
                 full_cli_flag: Optional[str]=None,
                 marker_file_name: Optional[str]=None,
                 env_var_name: Optional[str]=None,
                 env_var_required_value: Optional[str]=None,
                 default_value: bool = False):
        self.full_cli_flag = full_cli_flag
        self.env_var_name = env_var_name
        self.env_var_required_value = env_var_required_value
        self.marker_file_name = marker_file_name
        self.default_value = default_value

    def on(self, ctx: Context) -> bool:
        return \
            (self.full_cli_flag is not None and self.full_cli_flag in ctx.user_args) or \
            self._on_by_env_var() or \
            self._marker_file_exists(ctx) or \
            self.default_value

    def off(self, ctx: Context):
        return not self.on(ctx)

    def _on_by_env_var(self) -> bool:
        if self.env_var_name is not None and self.env_var_name in os.environ:
            if self.env_var_required_value is not None:
                return os.getenv(self.env_var_name, False) == self.env_var_required_value
            else:
                return True

        return False

    def _marker_file_exists(self, ctx: Context) -> bool:
        return self.marker_file_name is not None and \
               os.path.exists(os.path.join(ctx.config_dir, self.marker_file_name))
