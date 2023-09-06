from abc import ABC


class JobBase(ABC):
    def __init__(self):
        pass

    def start(self):
        raise NotImplementedError("start has not been implemented yet.")

    def stop(self):
        raise NotImplementedError("stop has not been implemented yet.")
