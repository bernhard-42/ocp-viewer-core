import os


class Comms:
    def __init__(self): ...

    def send_data(data, timeit=False):
        """Send data to the viewer"""

    def send_config(config, timeit=False):
        """Send config to the viewer"""

    def send_command(data, timeit=False):
        """Send command to the viewer"""

    def send_backend(data, timeit=False):
        """Send data to the viewer"""

    def send_response(data, timeit=False):
        """Send data to the viewer"""


class Session:
    def __init__(self, comms: Comms):
        self.comms = comms
        self._status = None
        self._workspace_config = None

    def status(self):
        if self._status is None:
            self._status = self.comms.send_command("status")
        return self._status

    def workspace_config(self):
        if self._workspace_config is None:
            self._workspace_config = self.comms.send_command("config")

    def set_viewer(self, config):
        data = {
            "type": "ui",
            "config": config,
        }

        try:
            self.comms.send_config(data)

        except Exception as ex:
            raise RuntimeError(
                "Cannot set viewer config. Is the viewer running?\n" + str(ex.args)
            ) from ex


def is_pytest():
    return "PYTEST_CURRENT_TEST" in os.environ
