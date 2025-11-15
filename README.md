# HexTex

The Hex Viewer/Editor in Textual

![screenshot](docs/hextex.png "Prototype")

## Keys

* Use `Ctrl+w` to change the display width of the units
* Use `Ctrl+p` to change the display endianess of the units
* Use `Ctrl+g` to go to an offset in the file.

## Issues

* On occasion, the synchronization between the two data tables will cause a fast flickering between two locations as the highlight updates between two coordinates. Sometimes this can be resolved by using the `Ctrl+g` to go to a specific offset, like 0.
