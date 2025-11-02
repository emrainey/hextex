import textual
from .bin import BinFile
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static
from textual.containers import Container


class HexTex(App):
    CSS = """
    Screen {
        align: center middle;
    }
    #stats {
        dock: top;
        width: 100%;
        height: 3;
        background: $primary;
        content-align: center middle;
    }
    #main-view {
        height: 100%;
        layout: horizontal;
    }
    #hex-view {
        background: $primary;
        width: 80%;
        height: 100%;
        margin: 1;
        padding: 1;
        border-right: solid $primary;
        min-height: 16;
    }
    #ascii-view {
        background: $secondary;
        width: 20%;
        margin: 1;
        padding: 1;
    }
    DataTable {
        height: 100%;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    offset: int
    count: int
    columns: int = int(16)
    rows: int = int(20)

    def __init__(self, bf: BinFile) -> None:
        super().__init__()
        self.binfile = bf
        self.offset = int(0)
        self.count = self.columns * self.rows

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="stats")
        with Container(id="main-view"):
            yield DataTable(id="hex-view", zebra_stripes=True)
            yield DataTable(id="ascii-view", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        stats = self.query_one("#stats", Static)
        stats.update(
            f"File {self.binfile.path} - Offset: {self.offset}/{self.binfile.size} bytes"
        )
        hex_table = self.query_one("#hex-view", DataTable)
        hex_table.clear()
        hex_table.cursor_type = "cell"
        columns = [f"0x{i:02X}" for i in range(self.columns)]
        hex_table.add_columns(*columns)
        # self.rows = max(4, hex_table.size.height - 1)

        ascii_table = self.query_one("#ascii-view", DataTable)
        ascii_table.clear()
        ascii_table.cursor_type = "cell"
        ascii_table.add_columns("ASCII")
        self.refresh_display()

    # def on_resize(self) -> None:
    #     """Recalculate when window is resized."""
    #     hex_table = self.query_one("#hex-view", DataTable)
    #     new_rows = max(1, hex_table.size.height - 3)  # Adjust for columns and borders
    #     # self.notify(f"on_resize -> {hex_table.size.width}x{hex_table.size.height}")
    #     if new_rows < self.rows:
    #         self.rows = new_rows
    #         self.refresh_display()

    def refresh_display(self):
        stats = self.query_one("#stats", Static)
        hex_table = self.query_one("#hex-view", DataTable)
        ascii_table = self.query_one("#ascii-view", DataTable)

        hex_table.clear()
        ascii_table.clear()

        stats.update(
            f"File {self.binfile.path} | {self.columns}x{self.rows} Offset: 0x{self.offset:08X} => {self.offset}/{self.binfile.size} bytes"
        )

        for row in range(self.rows):
            row_offset = self.offset + (row * self.columns)
            if row_offset >= self.binfile.size:
                break
            chunk = self.binfile.load_chunk(row_offset, self.columns)
            hex_values = [f"{b:02X}" for b in chunk]
            label = Text(f"{row_offset:08X}", style="#B0FC38 italic")
            # assert len(hex_values) == self.columns, "Hex values length mismatch"
            ascii_values = [chr(b) if 32 <= b <= 126 else "." for b in chunk]
            hex_table.add_row(*hex_values, label=label)
            ascii_table.add_row("".join(ascii_values), label=label)

    def on_key(self, event):
        if event.key == "q":
            self.exit()

        if event.key == "up":
            new_offset = max(
                0, min(self.offset - self.columns, self.binfile.size - self.columns)
            )
            if new_offset < self.binfile.size:
                self.offset = new_offset
                self.refresh_display()

        if event.key == "down":
            new_offset = min(self.offset + self.columns, self.binfile.size - self.count)
            if new_offset < self.binfile.size:
                self.offset = new_offset
                self.refresh_display()

        if event.key == "pageup":
            new_offset = max(
                0, min(self.offset - self.count, self.binfile.size - self.columns)
            )
            if new_offset < self.binfile.size:
                self.offset = new_offset
                self.refresh_display()

        if event.key == "pagedown":
            new_offset = min(self.offset + self.count, self.binfile.size - self.count)
            if new_offset < self.binfile.size:
                self.offset = new_offset
                self.refresh_display()

        if event.key == "home":
            self.offset = 0
            self.refresh_display()

        if event.key == "end":
            self.offset = max(0, self.binfile.size - self.count)
            self.refresh_display()
