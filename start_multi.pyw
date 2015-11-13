# -*- coding: utf-8 -*-

from multiprocessing import Queue, Process, Value, Lock
from tabgui import TabInterface, executor


class Counter(object):
    def __init__(self, initialVal=0):
        self.val = Value('i', initialVal)
        self.lock = Lock()

    def __iadd__(self, val):
        with self.lock:
            self.val.value += val
        return self

    def __isub__(self, val):
        with self.lock:
            self.val.value -= val
        return self

    def __int__(self):
        return self.val.value

    def __eq__(self, other):
        try:
            selfVal = int(self)
            otherVal = int(other)
            return selfVal == otherVal
        except:
            return False

    def __str__(self):
        return str(self.val.value)



class MultiProcessInterface(TabInterface):

    def _process_request_dict(self, requestDic):
        """ In an one-process version, this is the main executor.

        """
        self.tasks.put(requestDic)
        self.awaited += 1


    def run(self):
        self.awaited = Counter()
        self.calls = Counter()
        self.tasks = Queue(2000)
        self.results = Queue(2000)

        worker = Process(target=executor, args = (self.tasks, self.awaited, self.results, self.calls))
        self.root.processBound = [worker]

        worker.start()
        self.root.after(200, self.message_publisher)
        self.root.mainloop()


if __name__ == '__main__':
    ti = MultiProcessInterface()
    ti.run()
