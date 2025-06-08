import time

from PySide6.QtCore import QThread, Signal, QObject


class ReadCanMsgWork(QObject):
    resultSignal = Signal(object)
    error_signal = Signal(str)
    finishedSignal = Signal()

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._is_running = False

    def start_work(self):
        # print("start work")
        self._is_running = True
        while self._is_running:
            try:
                result = self.func(*self.args, **self.kwargs)
                # print(result)
                self.resultSignal.emit(result)
            except Exception as e:
                self.error_signal.emit(str(e))
                self._is_running = False

            time.sleep(0.01)

    def stop_work(self):
        self._is_running = False