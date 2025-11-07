import struct
from typing import List

from textual.events import Event
from .bin import BinFile
from rich.text import Text
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, DataTable, Static, Label, Input
from textual.containers import Container, Grid
from textual.widgets.data_table import ColumnKey


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
        # ("ctrl+q", "quit", "Quit"),
        ("ctrl+l", "toggle_endianness", "Toggle Endianness"),
        ("ctrl+g", "goto_offset", "Go to Offset"),
        ("ctrl+w", "toggle_width", "Toggle Width"),
    ]

    cell_count: int
    columns: int = int(16)
    row_depth: int = int(16)
    rows: int = int(0)
    little_endian: bool = True  # Default to little-endian
    width: int = int(1)
    index: int = int(0)
    WIDTH_OPTIONS: List[int] = [1, 2, 4, 8]
    # The byte offset of the DataTable in the top level corner of the view
    offset: int = int(0)
    ignore_change: int = int(0)
    keys: List[ColumnKey] | None = None
    hex_table: DataTable
    ascii_table: DataTable

    def __init__(self, bf: BinFile, width: int) -> None:
        super().__init__()
        self.binfile = bf
        self.cell_count = len(self.binfile.data)
        self.width = self.WIDTH_OPTIONS[self.index]
        self.row_depth = self.columns * self.width
        self.rows = len(self.binfile.data) // self.columns
        print("Rows: ", self.rows, " Cell Count: ", self.cell_count)

    def compose(self) -> ComposeResult:
        """Layout the Textual UI elements"""
        yield Header(show_clock=True)
        yield Static(id="stats")
        with Container(id="main-view"):
            self.hex_table = DataTable(id="hex-view", zebra_stripes=True)
            yield self.hex_table
            self.ascii_table = DataTable(id="ascii-view", zebra_stripes=True)
            yield self.ascii_table
        yield Footer()

    def set_columns(self, hex_table: DataTable) -> None:
        hex_table.clear()
        if self.keys is not None:
            for key in self.keys:
                hex_table.remove_column(key)
        hex_table.cursor_type = "cell"
        column_headers = []
        if self.width == 1:
            self.columns = int(16)
            column_headers = [f"0x{i:02X}" for i in range(self.columns)]
        elif self.width == 2:
            self.columns = int(8)
            column_headers = [f"0x{i:04X}" for i in range(0, self.columns, 2)]
        elif self.width == 4:
            self.columns = int(4)
            column_headers = [f"0x{i:08X}" for i in range(0, self.columns, 4)]
        elif self.width == 8:
            self.columns = int(2)
            column_headers = [f"0x{i:016X}" for i in range(0, self.columns, 8)]
        self.keys = hex_table.add_columns(*column_headers)
        print("There are now ", len(self.keys), " columns.")

    def on_mount(self) -> None:
        """Set up the Textual UI elements"""
        self.set_columns(self.hex_table)
        self.ascii_table.cursor_type = "cell"
        self.ascii_table.add_columns("ASCII")
        self.refresh_display()

    def refresh_display(self):
        stats = self.query_one("#stats", Static)
        self.hex_table.clear()
        self.ascii_table.clear()
        endian_mode = "LE" if self.little_endian else "BE"
        for row in range(self.rows):
            row_offset = row * self.row_depth
            chunk = self.binfile.data[row_offset : row_offset + self.row_depth]
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
            self.hex_table.add_row(*hex_values, label=label)
            self.ascii_table.add_row("".join(ascii_values), label=label)
        row_to_show = self.offset // self.row_depth
        col_to_show = (self.offset % self.row_depth) // self.width
        self.hex_table.move_cursor(
            row=row_to_show, column=col_to_show, animate=False, scroll=True
        )
        stats.update(
            f"File {self.binfile.path} {self.binfile.size} bytes | {endian_mode} Width:{self.width}"
        )

    def action_toggle_endianness(self):
        """Toggle between little-endian and big-endian display."""
        self.little_endian = not self.little_endian
        self.refresh_display()

    def action_toggle_width(self):
        """Cycle between width options."""
        current_index = self.WIDTH_OPTIONS.index(self.width)
        new_index = (current_index + 1) % len(self.WIDTH_OPTIONS)
        self.width = self.WIDTH_OPTIONS[new_index]
        self.set_columns(self.hex_table)
        self.refresh_display()

    def action_goto_offset(self):
        """Prompt the user to enter an offset to go to."""

        def new_offset(offset_str: str | None) -> None:
            try:
                new_offset = int(offset_str, 16)
                if 0 <= new_offset < self.binfile.size:
                    self.offset = new_offset
                    rows = self.offset // self.row_depth
                    cols = (self.offset % self.row_depth) // self.width
                    self.hex_table.move_cursor(
                        row=rows, column=cols, animate=False, scroll=True
                    )
                    # the change callback will update both tables
            except ValueError:
                pass  # Ignore invalid input

        self.push_screen(GotoScreen(), new_offset)

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        """if the event is from the hex table, update the ascii table and vice versa"""
        if event.data_table.id == "hex-view":
            row = event.coordinate.row
            column = event.coordinate.column
            self.offset = (row * self.row_depth) + (column)
            self.ascii_table.move_cursor(
                row=row, column=column, animate=False, scroll=True
            )
        if event.data_table.id == "ascii-view":
            row = event.coordinate.row
            column = event.coordinate.column
            self.offset = (row * self.row_depth) + (column)
            self.hex_table.move_cursor(
                row=row, column=column, animate=False, scroll=True
            )
