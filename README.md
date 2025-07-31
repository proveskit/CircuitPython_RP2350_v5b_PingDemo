# PROVES Kit RP2040 v5b CircuitPython Flight Software and Ground Station

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![CI](https://github.com/proveskit/CircuitPython_RP2350_v5b/actions/workflows/ci.yaml/badge.svg)

This is the template repository for v5b PROVES Kit Flight Controller boards. Head to our [docs site](https://proveskit.github.io/pysquared/) to get started.

To run code here as is, because it automatically dismounts during boot to become writable

1. storage.erase_filesystem
2. the board should reappear on your computer, you can run make
3. screen back into the guy and run microcontroller.reset()
