import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(sys.path[0])))

import signal
import inspect

from app.markets.quotes_service import QuotesService

from app.utils import logger
from app.config.configure import config


class Application:
    """Asynchronous event I/O driven quantitative trading framework.
        """

    def __init__(self) -> None:
        self.loop = None
        self.thread_pool = None
        self.event_center = None

    def _initialize(self, config_file):
        """Initialize."""
        self._load_settings(config_file)
        self._init_logger()
        return self

    def start(self, config_file=None, entrance_func=None) -> None:
        """Start the event loop."""

        def keyboard_interrupt(s, f):
            print("KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(s))
            self.stop()

        signal.signal(signal.SIGINT, keyboard_interrupt)

        self._initialize(config_file)
        if entrance_func:
            if inspect.iscoroutinefunction(entrance_func):
                self.loop.create_task(entrance_func())
            else:
                entrance_func()

    def stop(self) -> None:
        """Stop the event loop."""
        logger.info("stop io loop.", caller=self)

    def _load_settings(self, config_module) -> None:
        """Load config settings.

        Args:
            config_module: config file path, normally it's a json file.
        """
        config.loads(config_module)

    def _init_logger(self) -> None:
        """Initialize logger."""
        logger.initLogger(**config.log)


def entrance():
    service = QuotesService()
    service.start()


if __name__ == '__main__':
    config_file = sys.argv[1]

    app = Application()
    app.start(config_file, entrance)
