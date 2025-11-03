import struct
from .bin import BinFile
from rich.text import Text
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, DataTable, Static, Label, Input, Button
from textual.containers import Container, Grid


class GotoScreen(ModalScreen[str]):
    """A simple screen to prompt for an offset to go to."""

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Go To Offset", id="goto-label"),
            Input(
                placeholder="Offset (hex)",
                type="text",
                id="offset-input",
                restrict=r"[0-9a-fA-F]+",
                validate_on=["submitted"],
            ),
            # Button("Go", id="go-button", variant="primary"),
            # Button("Cancel", id="cancel-button", variant="error"),
            id="dialog",
        )

    def on_key(self, event) -> None:
        if event.key == "enter":
            input = self.query_one("#offset-input", Input)
            self.dismiss(input.value)


class HexTex(App):
    CSS = """
    Screen {
        align: center middle;
    }
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 11;
        border: thick $background 80%;
        background: $surface;
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
        ("l", "toggle_endianness", "Toggle Endianness"),
        ("g", "goto_offset", "Go to Offset"),
    ]

    offset: int
    count: int
    columns: int = int(16)
    rows: int = int(20)
    little_endian: bool = True  # Default to little-endian

    def __init__(self, bf: BinFile, width: int) -> None:
        super().__init__()
        self.binfile = bf
        self.offset = int(0)
        self.count = self.columns * self.rows
        self.width = width

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="stats")
        with Container(id="main-view"):
            yield DataTable(id="hex-view", zebra_stripes=True)
            yield DataTable(id="ascii-view", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        hex_table = self.query_one("#hex-view", DataTable)
        hex_table.cursor_type = "cell"
        columns = []
        if self.width == 1:
            columns = [f"0x{i:02X}" for i in range(self.columns)]
        elif self.width == 2:
            columns = [f"0x{i:04X}" for i in range(0, self.columns, 2)]
        elif self.width == 4:
            columns = [f"0x{i:08X}" for i in range(0, self.columns, 4)]
        elif self.width == 8:
            columns = [f"0x{i:016X}" for i in range(0, self.columns, 8)]
        hex_table.add_columns(*columns)

        ascii_table = self.query_one("#ascii-view", DataTable)
        ascii_table.cursor_type = "cell"
        ascii_table.add_columns("ASCII")
        self.refresh_display()

    def refresh_display(self):
        stats = self.query_one("#stats", Static)
        main_view = self.query_one("#main-view", Container)
        hex_table = self.query_one("#hex-view", DataTable)
        ascii_table = self.query_one("#ascii-view", DataTable)

        hex_table.clear()
        ascii_table.clear()

        endian_mode = "LE" if self.little_endian else "BE"
        stats.update(
            f"File {self.binfile.path} | {self.columns}x{self.rows} "
            f"Offset: 0x{self.offset:08X} => {self.offset}/{self.binfile.size} bytes | "
            f"{endian_mode} | M:{main_view.size} H:{hex_table.size}"
        )

        for row in range(self.rows):
            row_offset = self.offset + (row * self.columns)
            if row_offset >= self.binfile.size:
                break
            chunk = self.binfile.load_chunk(row_offset, self.columns)
            hex_values = []
            # use struct to pack the bytes together correctly based on the width selected
            endian_prefix = "<" if self.little_endian else ">"
            if self.width == 1:
                hex_values = [f"{b:02X}" for b in chunk]
            elif self.width == 2:
                uint16_values = struct.unpack(
                    f"{endian_prefix}{len(chunk)//2}H", chunk[: len(chunk) // 2 * 2]
                )
                hex_values = [f"{b:04X}" for b in uint16_values]
            elif self.width == 4:
                uint32_values = struct.unpack(
                    f"{endian_prefix}{len(chunk)//4}I", chunk[: len(chunk) // 4 * 4]
                )
                hex_values = [f"{b:08X}" for b in uint32_values]
            elif self.width == 8:
                uint64_values = struct.unpack(
                    f"{endian_prefix}{len(chunk)//8}Q", chunk[: len(chunk) // 8 * 8]
                )
                hex_values = [f"{b:016X}" for b in uint64_values]
            label = Text(f"{row_offset:08X}", style="#B0FC38 italic")
            ascii_values = [chr(b) if 32 <= b <= 126 else "." for b in chunk]
            hex_table.add_row(*hex_values, label=label)
            ascii_table.add_row("".join(ascii_values), label=label)

    def action_toggle_endianness(self):
        """Toggle between little-endian and big-endian display."""
        self.little_endian = not self.little_endian
        self.refresh_display()

    def action_goto_offset(self):
        """Prompt the user to enter an offset to go to."""

        def new_offset(offset_str: str | None) -> None:
            try:
                new_offset = int(offset_str, 16)
                if 0 <= new_offset < self.binfile.size:
                    self.offset = new_offset & ~0xF
                    self.refresh_display()
            except ValueError:
                pass  # Ignore invalid input

        self.push_screen(GotoScreen(), new_offset)

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
