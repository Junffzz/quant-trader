import sys
import os
sys.path.append(os.path.dirname(sys.path[0]))

import signal

from app.entrypoint.worker import WorkerService


def main():
    service = WorkerService()
    service.start()

    service.wait()
    # listen signal
    # signal.signal(signal.SIGKILL, service.stop())


if __name__ == '__main__':
    main()
