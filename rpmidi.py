from machine import Pin, PWM
from math import log2, pow
import utime
import io

"""
RPMidi
A PWM-based MIDI player for the Raspberry Pi Pico. Uses GPIO 6-9 for 4 voices.

Created by MikeDEV for use in https://github.com/MikeDev101/oops-all-picos-computer
========================================================================================================

MIDIS must be converted using https://github.com/LenShustek/miditones.

Recommended defaults:
.\miditones.exe -t=4 .\your-midi-here.mid

Copy-paste your-midi-here.c's array data into a list.
MIDI files must not contain more than 4 voices, as any other channel will be ignored by the converter.

========================================================================================================

THE MEOW LICENSE ("MEOW") 1.3 - Last revised Jan 7, 2022.

COPYRIGHT (C) 2022 MikeDEV.

Under this license:

* You are free to change, remove, or modify the above copyright notice.
* You are free to use the software in private or commercial forms.
* You are free to use, copy, modify, and/or distribute the software for any purpose.
* You are free to distribute this software with or without fee.
* Absolutely no patent use is permitted.

With the above conditions, the author(s) of this software do NOT gurantee warranty. As part of this license,
under no circumstance shall the author(s) and/or copyright holder(s) be held liable for any and all forms of
damages.

NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY THIS LICENSE. THE SOFTWARE IS
PROVIDED "AS IS" AND THE AUTHOR(S) DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY
SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR
IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
========================================================================================================
"""

import utime

led = Pin(25, Pin.OUT)

class RPMidi:
    def __init__(self):
        # Initialize Attributes
        self.is_file = False
        self.is_mem = False
        self.is_debug = False
        
        self.length = 0
        
        # Configure Channels
        self.channels = {
            0x90: PWM(Pin(0)),
            0x91: PWM(Pin(3)),
            0x92: PWM(Pin(15)),
            0x93: PWM(Pin(11)),
            0x94: PWM(Pin(23)),
            0x95: PWM(Pin(21)),
            0x96: PWM(Pin(22))
        }
        self.stop_all()
        
    def _pitch(self, freq):
        return (2**((freq-69)/12))*440

    def _duty_cycle(self, percent):
        return round((percent/100)*65535)

    def play_note(self, note, channel, duty):
        led.toggle()
        self.channels[channel].freq(round(self._pitch(note)))
        self.channels[channel].duty_u16(self._duty_cycle(duty))
            
    def stop_channel(self, channel):
        self.debug("stopping channel %s" % (hex(channel)))
        #TODO: Add Check
        # Grab Channel By Equivalent Play Opcode
        self.channels[channel + 0x10].duty_u16(0)

    def stop_all(self):
        self.debug("stopping all")
        for channel in self.channels.values():
            channel.duty_u16(0)

    def _opcodes(self):
        return [0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0xf0, 0xe0]
    
    def _play_note_opcodes(self):
        return [0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96]

    def _stop_note_opcodes(self):
        return [0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86]
    
    def _end_song_opcodes(self):
        return [0xf0, 0xe0]
    
    
    def read_byte(self, music, index):
        if self.is_file:
            return int.from_bytes(music.read(1), "big")
        elif self.is_mem:
            return music[index]
        
    def check_oo_range(self, music, index):
        if self.is_file:
            return index >= self.length # We probably shouldn't be relying on this for a bad for loop array
        elif self.is_mem:
            index >= len(music)

    def adjust_index(self, music, index):
        if self.is_file:
            music.seek(-1, 1)
        #elif self.is_mem:
           # print
            # for now do nothing.
    def debug(self, statement):
        if self.is_debug:
            print(statement)
            
    def print_pointer(self, music, index):
        if self.is_file:
            self.debug("File pointer was at: %s" % (music.tell()))
        elif self.is_mem:
            self.debug("Index was at: %d" % (index))

    def seek_size(self, f):
        pos = f.tell()
        f.seek(0, 2) # 2 means relative to file's end
        size = f.tell()
        f.seek(pos) # back to where we were
        return size
    
    def delay(self, milliseconds):
        now = utime.time_ns() / 1000000
        start = now
        end = start + milliseconds
        while now < end:
            now = utime.time_ns() / 1000000

    def play_song(self, music):

        done = False
        tmp = []
        index = 0
        isReading = False
        opcode = 0x00
        
        self.stop_all() # Silence any existing music
        utime.sleep(1)
            
        if type(music) == io.FileIO:
            self.is_file = True
            self.length = self.seek_size(music)
            
        elif type(music) == list:
            self.is_mem = True
        
        print("what is going on?!")
        while not done:
            if self.check_oo_range(music, index):
                self.debug("out of range while reading opcode")
                done = True
                break
            else:
                # Read opcode
                opcode_byte = self.read_byte(music, index)
                self.debug(opcode_byte)
                if opcode_byte in self._opcodes():
                    opcode = opcode_byte
                    
                    # Scan for timing data
                    isReading = True
                    tmp = []
                    tmp_index = 1
                    
                    # Read next bytes for timing info
                    while isReading: 
                        if self.check_oo_range(music, (index + tmp_index)):
                            self.debug("We are done!")
                            done = True
                            break
                        else:
                            tmp_byte = self.read_byte(music, index + tmp_index)
                            if not tmp_byte in self._opcodes():
                                tmp.append(tmp_byte)
                                tmp_index += 1
                                self.debug("reading...got num %s" % hex(tmp_byte))
                            else:
                                self.debug("Last Read was opcode %s Going back..." % hex(tmp_byte))
                                self.adjust_index(music, index)
                                isReading = False
                    
                    # Execute instruction
                    self.debug("About to execute %s" % opcode);
                    if opcode in self._play_note_opcodes():
                        # Play voice and goto next instruction or play and wait for x milliseconds
                        if len(tmp) > 0:
                            
                            if opcode >= 0x90 and opcode <= 0x96:
                                self.play_note(tmp[0], opcode, 50)
                            
                            if len(tmp) == 3:
                                delay = ((tmp[1]*256)+(tmp[2]))
                                print("sleeping for %d ms" % (delay))
                                #self.delay(delay)
                                utime.sleep_ms(delay)
                        else:
                            self.debug("expecting at least one entry in tmp, got nothing")
                            self.debug("Next byte would have been %s" % (hex(self.read_byte(music, index + 1))))
                            self.print_pointer(music, index)
                            done = True
                            self.stop_all()
                            break
                        index += 1
                        
                    elif opcode in self._stop_note_opcodes():
                        # Mute voice or mute and wait for x milliseconds
                        if opcode >= 0x80 and opcode <= 0x8E:
                            self.stop_channel(opcode) 
                        if len(tmp) >= 2:
                            delay = ((tmp[0]*256)+(tmp[1]))
                            self.debug("sleeping for %d ms" % (delay))
                            utime.sleep_ms(delay)
                        index += 1
                        
                    elif opcode in self._end_song_opcodes():
                        # End or loop the song
                        if opcode == 0xf0: # Song is over, stop playing.
                            print("song is over")
                            done = True
                            break
                        else:
                            print("Loop Song!")
                            done = False
                            index = 0 # Song is looping, go back to beginning of song.
                else:
                    index += 1
