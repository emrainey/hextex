import os
import pathlib


class BinFile:
    path: str
    offset: int
    size: int
    data: bytearray

    def __init__(self, filepath: str):
        self.path = pathlib.Path(filepath).resolve().as_posix()
        # get the number of bytes in the file.
        self.offset = int(0)
        self.data = bytearray()
        self.size = os.path.getsize(filepath)

    def load_chunk(self, offset: int, count: int) -> bytes:
        """
        Loads a section of the file from an offset for the
        given number of bytes up to the limit of the file
        """
        # For now return random data
        # return random.randbytes(count)
        with open(self.path, "rb") as file:
            file.seek(offset)
            data = file.read(count)
            return data

    def save_chunk(self, offset: int, data: bytes) -> bool:
        with open(self.path, "w+b") as file:
            file.seek(offset)
            file.write(data)
            return True

    def load(self) -> None:
        with open(self.path, "rb") as file:
            # the whole thing, all at once!
            self.data = bytearray(file.read())

    def save(self) -> None:
        """Save the current data back to the file."""
        with open(self.path, "wb") as file:
            file.write(self.data)
