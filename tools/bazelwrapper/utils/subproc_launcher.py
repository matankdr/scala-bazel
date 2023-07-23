import subprocess
import sys

from bazelwrapper.context import Context, WixFlags


class PySubprocessLauncher:
    def __init__(self, title: str, main_py_script_path: str):
        self.title = title
        self.main_py_script_path = main_py_script_path

    def launch(self, ctx: Context):
        ctx.logger.debug("Going to launch {title} worker...".format(title=self.title))

        python_interpreter = sys.executable
        script_path = self.main_py_script_path
        command = [python_interpreter, script_path] + _extract_wix_flags(ctx)

        return self._exe_safe(command, ctx)

    def _exe_safe(self, cmd, ctx: Context):
        try:
            ctx.logger.debug("Launching {title} process...".format(title=self.title))
            ctx.logger.debug("Reporter process command: '{command}'".format(command=" ".join(cmd)))

            p = subprocess.Popen(args=cmd, cwd=ctx.workspace_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ctx.logger.debug("{title} process ID is: '{pid}'".format(title=self.title, pid=p.pid))

            return p.pid
        except Exception as err:
            ctx.logger.debug("Failed to launch {title}: {err}".format(title=self.title, err=err), exec_info=True)

            return -1


def _extract_wix_flags(ctx: Context):
    return [flag for flag in ctx.user_args if flag.startswith(WixFlags.PREFIX)]
