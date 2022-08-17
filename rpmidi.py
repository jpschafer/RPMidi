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

led = Pin(25, Pin.OUT)

class RPMidi:
    def __init__(self):
        # Initialize Attributes
        self.is_file = False
        self.is_mem = False
        self.is_debug = False
        
        # Configure Channels
        self.ch_a_0 = PWM(Pin(16))
        self.ch_a_1 = PWM(Pin(17))
        self.ch_b_0 = PWM(Pin(18))
        self.ch_b_1 = PWM(Pin(19))
        self.ch_c_0 = PWM(Pin(20))
        self.stop_all()
        
    def _pitch(self, freq):
        return (2**((freq-69)/12))*440

    def _duty_cycle(self, percent):
        return round((percent/100)*65535)

    def play_note(self, note, channel, duty):
        led.toggle()
        if channel == "a0":
            self.ch_a_0.freq(round(self._pitch(note)))
            self.ch_a_0.duty_u16(self._duty_cycle(duty))
        elif channel == "a1":
            self.ch_a_1.freq(round(self._pitch(note)))
            self.ch_a_1.duty_u16(self._duty_cycle(duty))
        elif channel == "b0":
            self.ch_b_0.freq(round(self._pitch(note)))
            self.ch_b_0.duty_u16(self._duty_cycle(duty))
        elif channel == "b1":
            self.ch_b_1.freq(round(self._pitch(note)))
            self.ch_b_1.duty_u16(self._duty_cycle(duty))
        elif channel == "c0":
            self.ch_c_0.freq(round(self._pitch(note)))
            self.ch_c_0.duty_u16(self._duty_cycle(duty))
            
    def stop_channel(self, channel):
        self.debug("stopping channel %s" % (channel))
        if channel == "a0":
            self.ch_a_0.duty_u16(0)
        elif channel == "a1":
            self.ch_a_1.duty_u16(0)
        elif channel == "b0":
            self.ch_b_0.duty_u16(0)
        elif channel == "b1":
            self.ch_b_1.duty_u16(0)
        elif channel == "c0":
            self.ch_c_0.duty_u16(0)
    def stop_all(self):
        self.debug("stopping all")
        self.ch_a_0.duty_u16(0)
        self.ch_a_1.duty_u16(0)
        self.ch_b_0.duty_u16(0)
        self.ch_b_1.duty_u16(0)
        self.ch_c_0.duty_u16(0)
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
            return False # Fix this eventually obviously
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
        elif type(music) == list:
            self.is_mem = True
        
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
                            done = True
                            break
                        else:
                            tmp_byte = self.read_byte(music, index + tmp_index)
                            if not tmp_byte in self._opcodes():
                                tmp.append(tmp_byte)
                                tmp_index += 1
                                self.debug("reading...got num %d" % tmp_byte)
                            else:
                                self.adjust_index(music, index)
                                isReading = False
                    
                    # Execute instruction
                    if opcode in self._play_note_opcodes():
                        # Play voice and goto next instruction or play and wait for x milliseconds
                        if len(tmp) > 0:
                            if opcode == 0x90:
                                self.play_note(tmp[0], "a0", 50)
                            elif opcode == 0x91:
                                self.play_note(tmp[0], "b0", 50)
                            elif opcode == 0x92:
                                self.play_note(tmp[0], "a1", 50)
                            elif opcode == 0x93:
                                self.play_note(tmp[0], "b1", 50)
                            elif opcode == 0x94:
                                self.play_note(tmp[0], "c0", 50)
                            
                            if len(tmp) == 3:
                                delay = ((tmp[1]*256)+(tmp[2]))
                                self.debug("sleeping for %d ms" % (delay))
                                utime.sleep_ms(delay)
                        else:
                            self.debug("expecting at least one entry in tmp, got nothing")
                            done = True
                            break
                        index += 1
                        
                    elif opcode in self._stop_note_opcodes():
                        # Mute voice or mute and wait for x milliseconds
                        if opcode == 0x80:
                            self.stop_channel("a0")
                        elif opcode == 0x81:
                            self.stop_channel("b0")
                        elif opcode == 0x82:
                            self.stop_channel("a1")
                        elif opcode == 0x83:
                            self.stop_channel("b1")
                        elif opcode == 0x84:
                            self.stop_channel("c0")  
                        if len(tmp) >= 2:
                            delay = ((tmp[0]*256)+(tmp[1]))
                            self.debug("sleeping for %d ms" % (delay))
                            utime.sleep_ms(delay)
                        index += 1
                        
                    elif opcode in self._end_song_opcodes():
                        # End or loop the song
                        if opcode == 0xf0: # Song is over, stop playing.
                            done = True
                            break
                        else:
                            done = False
                            index = 0 # Song is looping, go back to beginning of song.
                else:
                    index += 1
