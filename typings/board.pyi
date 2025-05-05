# SPDX-FileCopyrightText: 2024 Justin Myers
#
# SPDX-License-Identifier: MIT
"""
Board stub for PROVES Kit v5a
 - port: raspberrypi
 - board_id: proveskit_rp2040_v5a
 - NVM size: 4096
 - Included modules: _asyncio, _bleio, _pixelmap, adafruit_bus_device, adafruit_pixelbuf, aesio, alarm, analogbufio, analogio, array, atexit, audiobusio, audiocore, audiomixer, audiomp3, audiopwmio, binascii, bitbangio, bitmapfilter, bitmaptools, bitops, board, builtins, builtins.pow3, busdisplay, busio, busio.SPI, busio.UART, codeop, collections, countio, digitalio, displayio, epaperdisplay, errno, floppyio, fontio, fourwire, framebufferio, getpass, gifio, hashlib, i2cdisplaybus, i2ctarget, imagecapture, io, jpegio, json, keypad, keypad.KeyMatrix, keypad.Keys, keypad.ShiftRegisterKeys, keypad_demux, keypad_demux.DemuxKeyMatrix, locale, math, memorymap, microcontroller, msgpack, neopixel_write, nvm, onewireio, os, os.getenv, paralleldisplaybus, pulseio, pwmio, qrio, rainbowio, random, re, rgbmatrix, rotaryio, rp2pio, rtc, sdcardio, select, sharpdisplay, storage, struct, supervisor, synthio, sys, terminalio, tilepalettemapper, time, touchio, traceback, ulab, usb, usb_cdc, usb_hid, usb_host, usb_midi, usb_video, vectorio, warnings, watchdog, zlib
 - Frozen libraries:
---
proveskit: This typings file was assembled by hand and is temporary until we can integrate the 5a board into upstream CircuitPython
"""

# Imports
import busio
import microcontroller

# Board Info:
board_id: str

# Pins:
TX: microcontroller.Pin  # GPIO0
RX: microcontroller.Pin  # GPIO1
SDA1: microcontroller.Pin  # GPIO2
SCL1: microcontroller.Pin  # GPIO3
SDA0: microcontroller.Pin  # GPIO4
SCL0: microcontroller.Pin  # GPIO5
RF1_RST: microcontroller.Pin  # GPIO6
SPI1_CS0: microcontroller.Pin  # GPIO7
SPI0_MISO: microcontroller.Pin  # GPIO8
SPI0_SCK: microcontroller.Pin  # GPIO9
SPI0_MOSI: microcontroller.Pin  # GPIO10
SPI0_MOSI: microcontroller.Pin  # GPIO11
RF1_IO4: microcontroller.Pin  # GPIO12
RF1_IO0: microcontroller.Pin  # GPIO13
RF2_IO3: microcontroller.Pin  # GPIO14
RF2_RST: microcontroller.Pin  # GPIO17
SPI1_CS1: microcontroller.Pin  # GPIO15
SPI1_MISO: microcontroller.Pin  # GPIO16
SPI1_SCK: microcontroller.Pin  # GPIO18
SPI1_MOSI: microcontroller.Pin  # GPIO19
GPIO_EXPANDER_RESET: microcontroller.Pin  # GPIO20
RF2_RX_EN: microcontroller.Pin  # GPIO21
RF2_TX_EN: microcontroller.Pin  # GPIO22
RF2_IO0: microcontroller.Pin  # GPIO23
WDT_WDI: microcontroller.Pin  # GPIO24
WDT_ENABLE: microcontroller.Pin  # GPIO25
MUX_RESET: microcontroller.Pin  # GPIO26
RTC_INT: microcontroller.Pin  # GPIO27
FIRE_DEPLOY1_A: microcontroller.Pin  # GPIO28
FIRE_DEPLOY1_B: microcontroller.Pin  # GPIO29

# Members:
def I2C() -> busio.I2C:
    """Returns the `busio.I2C` object for the board's designated I2C bus(es).
    The object created is a singleton, and uses the default parameter values for `busio.I2C`.
    """

def SPI() -> busio.SPI:
    """Returns the `busio.SPI` object for the board's designated SPI bus(es).
    The object created is a singleton, and uses the default parameter values for `busio.SPI`.
    """

def UART() -> busio.UART:
    """Returns the `busio.UART` object for the board's designated UART bus(es).
    The object created is a singleton, and uses the default parameter values for `busio.UART`.
    """

# Unmapped:
#   none
