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
        ("ctrl+l", "toggle_endianness", "Toggle Endianness"),
        ("ctrl+g", "goto_offset", "Go to Offset"),
        ("ctrl+w", "toggle_width", "Toggle Width"),
    ]

    cell_count: int
    FIXED_ROW_WIDTH: int = int(16)
    columns: int = FIXED_ROW_WIDTH
    row_depth: int = FIXED_ROW_WIDTH
    rows: int = int(0)
    little_endian: bool = True  # Default to little-endian
    width: int = int(1)
    index: int = int(0)
    WIDTH_OPTIONS: List[int] = [1, 2, 4, 8]
    # The byte offset of the DataTable in the top level corner of the view
    offset: int = int(0)
    ignore_change: int = int(0)
    hex_keys: List[ColumnKey] | None = None
    ascii_keys: List[ColumnKey] | None = None
    hex_table: DataTable
    ascii_table: DataTable

    def __init__(self, bf: BinFile, width: int) -> None:
        super().__init__()
        self.binfile = bf
        self.cell_count = len(self.binfile.data)
        self.width = width
        self.index = self.WIDTH_OPTIONS.index(width)
        self.columns = 16 // self.width
        self.row_depth = self.columns * self.width
        self.rows = len(self.binfile.data) // self.columns
        print("Rows: ", self.rows, " Cell Count: ", self.cell_count)

    def compose(self) -> ComposeResult:
        """Layout the Textual UI elements"""
        yield Header(show_clock=True)
        yield Static(id="stats")
        with Container(id="main-view"):
            self.hex_table = DataTable(
                name="Hex View", id="hex-view", zebra_stripes=True
            )
            yield self.hex_table
            self.ascii_table = DataTable(
                name="ASCII View", id="ascii-view", zebra_stripes=True, cell_padding=0
            )
            yield self.ascii_table
        yield Footer()

    def set_columns(self) -> None:
        """Sets up the DataTable columns based on the current width setting"""
        self.hex_table.clear()
        self.ascii_table.clear()
        if self.hex_keys is not None:
            for key in self.hex_keys:
                self.hex_table.remove_column(key)
        if self.ascii_keys is not None:
            for key in self.ascii_keys:
                self.ascii_table.remove_column(key)
        self.hex_table.cursor_type = "cell"
        self.ascii_table.cursor_type = "cell"
        hex_headers: List[str]
        ascii_headers: List[str]
        if self.width == 1:
            self.columns = int(16)
            hex_headers = [f"0x{i:02X}" for i in range(self.FIXED_ROW_WIDTH)]
        elif self.width == 2:
            self.columns = int(8)
            hex_headers = [f"0x{i:04X}" for i in range(0, self.FIXED_ROW_WIDTH, 2)]
        elif self.width == 4:
            self.columns = int(4)
            hex_headers = [f"0x{i:08X}" for i in range(0, self.FIXED_ROW_WIDTH, 4)]
        elif self.width == 8:
            self.columns = int(2)
            hex_headers = [f"0x{i:016X}" for i in range(0, self.FIXED_ROW_WIDTH, 8)]
        self.hex_keys = self.hex_table.add_columns(*hex_headers)
        ascii_headers = [f"{i:X}" for i in range(self.FIXED_ROW_WIDTH)]
        self.ascii_keys = self.ascii_table.add_columns(*ascii_headers)
        assert self.hex_keys is not None and self.ascii_keys is not None
        assert (
            len(hex_headers) == self.columns
        ), f"Hex column count mismatch! len={len(hex_headers)}, colums={self.columns}"

    def on_mount(self) -> None:
        """Set up the Textual UI elements"""
        self.ignore_change = True
        self.set_columns()
        self.refresh_display()
        self.ignore_change = False

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
                uint16_values = struct.unpack(f"{endian_prefix}{len(chunk)//2}H", chunk)
                hex_values = [f"{b:04X}" for b in uint16_values]
            elif self.width == 4:
                uint32_values = struct.unpack(f"{endian_prefix}{len(chunk)//4}I", chunk)
                hex_values = [f"{b:08X}" for b in uint32_values]
            elif self.width == 8:
                uint64_values = struct.unpack(f"{endian_prefix}{len(chunk)//8}Q", chunk)
                hex_values = [f"{b:016X}" for b in uint64_values]
            label = Text(f"{row_offset:08X}", style="#B0FC38 italic")
            ascii_values = [chr(b) if 32 <= b <= 126 else "." for b in chunk]
            self.hex_table.add_row(*hex_values, label=label)
            self.ascii_table.add_row(*ascii_values, label=label)
        row_to_show = self.offset // self.row_depth
        col_to_show = (self.offset % self.row_depth) // self.width
        self.hex_table.move_cursor(
            row=row_to_show, column=col_to_show, animate=False, scroll=True
        )
        self.ascii_table.move_cursor(
            row=row_to_show, column=col_to_show, animate=False, scroll=True
        )
        stats.update(
            f"File {self.binfile.path} {self.binfile.size} bytes | {endian_mode} Width:{self.width}"
        )

    def action_toggle_endianness(self):
        """Toggle between little-endian and big-endian display."""
        self.little_endian = not self.little_endian
        self.ignore_change = True
        self.set_columns()
        self.refresh_display()
        self.ignore_change = False

    def action_toggle_width(self):
        """Cycle between width options."""
        current_index = self.WIDTH_OPTIONS.index(self.width)
        new_index = (current_index + 1) % len(self.WIDTH_OPTIONS)
        self.width = self.WIDTH_OPTIONS[new_index]
        self.ignore_change = True
        self.set_columns()
        self.refresh_display()
        self.ignore_change = False

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
        if self.ignore_change:
            return
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
