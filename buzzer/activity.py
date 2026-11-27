from contextlib import contextmanager
from threading import Condition
from time import time_ns


class EventOrder:
    def __init__(self, clock=time_ns, initial=0):
        self.clock = clock
        self.condition = Condition()
        self.received = initial
        self.next = initial + 1

    @contextmanager
    def receive(self):
        with self.condition:
            self.received += 1
            sequence = self.received
            timestamp = self.clock()
            self.condition.wait_for(lambda: sequence == self.next)
        try:
            yield timestamp, sequence
        finally:
            with self.condition:
                self.next += 1
                self.condition.notify_all()
