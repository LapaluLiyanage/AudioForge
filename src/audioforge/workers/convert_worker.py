from PySide6.QtCore import QThread, Signal

from audioforge.core.converter import convert
from audioforge.core.models import ConversionOptions


class ConvertWorker(QThread):
    progress = Signal(int, float)
    finished_one = Signal(int, str)
    failed_one = Signal(int, str)

    def __init__(self, index: int, input_path: str, output_path: str, options: ConversionOptions):
        super().__init__()
        self.index = index
        self.input_path = input_path
        self.output_path = output_path
        self.options = options

    def run(self) -> None:
        try:
            result = convert(self.input_path, self.output_path, self.options)
            self.finished_one.emit(self.index, result.output_path)
        except Exception as exc:
            self.failed_one.emit(self.index, str(exc))
