import json
import warnings
from pathlib import Path
from typing import List, Type

class EveLine:

    #        C                     8
    #        8                     4
    #        4                     0
    #  E A 6 . 7 B F   ->   11 7 3 . 1 5 9 
    #        5                     2
    #        9                     6
    #        D                    10

    toMemonTail = {
        0xC :  8,
        0x8 :  4,
        0x4 :  0,
        0xE : 11,
        0xA :  7,
        0x6 :  3,
        0x7 :  1,
        0xB :  5,
        0xF :  9,
        0x5 :  2,
        0x9 :  6,
        0xD : 10,
    }

    type_order = ["MEASURE","HAKU","PLAY","LONG","TEMPO","END"]

    def __init__(self, tick, _type, val):
        self.tick = int(tick)
        self.type = str(_type).strip()
        self.val = int(val)
    
    def __str__(self):
        return f"{self.tick:>8},{self.type:<8},{self.val:>8}"

    @classmethod
    def fromFile(cls,file):
        with open(file,"r") as f:
            for line in f:
                yield cls.fromString(line)

    @classmethod
    def fromString(cls, line):
        split_line = line.strip().split(",")
        return cls(*split_line)
    
    @classmethod
    def cmp_key(cls, eveLine):
        return [eveLine.tick,cls.type_order.index(eveLine.type),eveLine.val]


def validTailPosition(n,p):

    assert n in range(16)
    assert p in range(12)
    
    x, y = n%4, n//4
    
    # Vertical
    if p%2 == 0: 
        dx = 0
        # Going up
        if (p//2)%2 == 0:
            dy = -(p//4 + 1)
        # Going down
        else:
           dy = p//4 + 1 
    # Horizontal 
    else:  
        dy = 0
        # Going right
        if (p//2)%2 == 0:
            dx = p//4 + 1       
        # Going left
        else:
            dx = -(p//4 + 1)
    
    return (0 <= x+dx <= 4) and (0 <= y+dy <= 4)


class MemonNote:

    #        8                    C
    #        4                    8
    #        0                    4
    # 11 7 3 . 1 5 9   ->   E A 6 . 7 B F
    #        2                    5
    #        6                    9
    #       10                    D

    toEveTail = {
        0   : 0x4,
        1   : 0x7,
        2   : 0x5,
        3   : 0x6,
        4   : 0x8,
        5   : 0xB,
        6   : 0x9,
        7   : 0xA,
        8   : 0xC,
        9   : 0xF,
        10  : 0xD,
        11  : 0xE,
    }

    def __init__(self):

        self._position = 0
        self._timing = 0
        self._length = 0
        self._tail = 0
    
    def __repr__(self):
        return f"Note<pos:{self.position},tim:{self.timing},len:{self.length},tail:{self.tail}>"
    
    @property
    def position(self):
        return self._position
    
    @position.setter
    def position(self, value):
        if value not in range(16):
            raise ValueError(f"Invalid note position : {value}")
        if self.length > 0 and not validTailPosition(value,self.tail):
            raise ValueError(f"Note position cannot be set to {value} considering tail position {self.tail}")
        else:
            self._position = value
        
    @property
    def timing(self):
        return self._timing
    
    @timing.setter
    def timing(self, value):
        if type(value) != int:
            raise TypeError(f"Incompatible type for note timing : {type(value)}, {value}")
        elif value < 0:
            raise ValueError(f"Invalid note timing : {value}")
        else:
            self._timing = value
    
    @property
    def length(self):
        return self._length
    
    @length.setter
    def length(self, value):
        if type(value) != int:
            raise TypeError(f"Incompatible type for note length : {type(value)}, {value}")
        if value < 0:
            raise ValueError(f"Invalid note length : {value}")
        else:
            self._length = value

    @property
    def tail(self):
        return self._tail
    
    @tail.setter
    def tail(self, value):
        if self.length == 0:
            self._tail = value
        elif value not in range(12):
            raise ValueError(f"Invalid note tail : {value}")
        elif not validTailPosition(self.position,value):
            raise ValueError(f"Tail position cannot be set to {value} considering note position {self.position}")
        else:
            self._tail = value
    
    @classmethod
    def fromDict(cls, _dict):
        
        note = cls()

        try:

            note.position = int(_dict["n"])
            note.timing = int(_dict["t"])
            note.length = int(_dict["l"])
            note.tail = int(_dict["p"])

        except KeyError:
            raise ValueError(f"Invalid note dict structure : {_dict}")
        
        return note
    
    @classmethod
    def fromEveLine(cls, noteLine, BPM, res):

        note = cls()

        note.timing = round((noteLine.tick * BPM * res) / (60 * 300))

        if noteLine.type == "PLAY":  

            note.position = noteLine.val

        else:
            
            note.position = noteLine.val % 0x10
            
            length_in_ticks = noteLine.val >> 8

            note.length = round((length_in_ticks * BPM * (res / (300 * 60))))

            eve_tail = (noteLine.val % 0x100) >> 4
            note.tail = EveLine.toMemonTail[eve_tail]
        
        return note
    
    @classmethod
    def fromEveLineIgnoringBPM(cls, noteLine):

        note = cls()

        note.timing = noteLine.tick

        if noteLine.type == "PLAY":  

            note.position = noteLine.val

        else:

            note.length = noteLine.val >> 8

            eve_tail = (noteLine.val % 0x100) >> 4
            note.tail = EveLine.toMemonTail[eve_tail]

            note.position = noteLine.val % 0x10
        
        return note
    
    @classmethod
    def new(cls, position, timing, length, tail):

        note = cls()

        note.position = position
        note.timing = timing
        note.length = length
        note.tail = tail

        return note


    
    def jsonify(self):
        return {
            "n":self.position,
            "t":self.timing,
            "l":self.length,
            "p":self.tail
            }
    
    def __hash__(self):
        return hash((self.position,self.timing))
    
    def __eq__(self, other):
        return self.position == other.position and self.timing == other.timing
    
    @classmethod
    def cmp_key(cls,note):
        return [note.timing,note.position]

class MemonChart:

    default_dif_names = ["BSC","ADV","EXT"]

    def __init__(self):

        self.dif_name = ""
        self.level = 0
        self._resolution = 240
        self.notes = set()
    
    @property
    def resolution(self):
        return self._resolution
    
    # TODO : check for _actually_ correct resolution values by looking at the notes and what evenly divides what etc
    @resolution.setter
    def resolution(self, value):
        if value <= 0:
            raise ValueError(f"Invalid resolution for chart : {value}")
        else:
            self._resolution = value
    
    @classmethod
    def fromDict(cls,_dict):

        memonChart = cls()

        try:

            memonChart.dif_name = _dict["dif_name"]
            memonChart.level = int(_dict["level"])
            memonChart.resolution = int(_dict["resolution"])
            memonChart.notes = set(MemonNote.fromDict(noteDict) for noteDict in _dict["notes"])
            
            if len(memonChart.notes) != _dict["notes"]:
                warnings.warn("Some duplicate notes were ignored")
        
        except KeyError:
            raise ValueError(f"Invalid chart structure : {_dict}")
        
        return memonChart
    
    def jsonify(self):

        d = dict()
        d["dif_name"] = self.dif_name
        d["level"] = self.level
        d["resolution"] = self.resolution
        d["notes"] = [note.jsonify() for note in sorted(self.notes,key=MemonNote.cmp_key)]
        
        return d
    
    def toEve(self, BPM):
            
        ordered_notes : List[MemonNote] = sorted(self.notes,key=MemonNote.cmp_key)

        lines = [EveLine(0,"TEMPO",(60*10**6)//BPM)]

        beat = 0

        while ordered_notes[-1].timing > beat*self.resolution:

            tick = (beat * 60 * 300 ) // BPM

            if beat%4 == 0:
                lines.append(EveLine(tick,"MEASURE",0))

            lines.append(EveLine(tick,"HAKU",0))

            beat += 1
        
        # Finish off with a first free measure
        while beat%4 != 0:
            tick = (beat * 60 * 300 ) // BPM
            lines.append(EveLine(tick,"HAKU",0))
            beat += 1
        
        # Add the special END tag
        tick = (beat * 60 * 300 ) // BPM
        lines.append(EveLine(tick,"END",0))
        lines.append(EveLine(tick,"MEASURE",0))
        lines.append(EveLine(tick,"HAKU",0))
        beat += 1

        # then add a second free measure
        while beat%4 != 0:
            tick = (beat * 60 * 300 ) // BPM
            lines.append(EveLine(tick,"HAKU",0))
            beat += 1
        
        for note in ordered_notes:
            
            tick = (note.timing * 60 * 300) // (self.resolution * BPM)

            if note.length == 0:

                lines.append(EveLine(tick,"PLAY",note.position))

            else:

                length = (note.length * 60 * 300) // (self.resolution * BPM)
                tail_val = MemonNote.toEveTail[note.tail]

                long_val = length * 0x100 + tail_val*0x10 + note.position

                lines.append(EveLine(tick,"LONG",long_val))
        
        return sorted(lines,key=EveLine.cmp_key)


    
    @classmethod
    def cmp_key(cls,chart):
        if chart.dif_name in MemonChart.default_dif_names:
            return [False,MemonChart.default_dif_names.index(chart.dif_name)]
        else:
            return [True,chart.dif_name]


class Memon:

    def __init__(self):

        self.song_title = ""
        self.artist = ""
        self.music_path = ""
        self.jacket_path = ""
        self._BPM = 120
        self._offset = 0
        self.charts = dict()
    
    @property
    def BPM(self):
        return self._BPM
    
    @BPM.setter
    def BPM(self, value):
        if (value <= 0):
            raise ValueError("BPM must be positive")
        else:
            self._BPM = value
    
    @property
    def offset(self):
        return self._offset
    
    @offset.setter
    def offset(self, value):
        if (type(value) not in [int,float]):
            raise ValueError("offset must be a number")
        else:
            self._offset = value
        
    @classmethod
    def fromDict(cls,_dict):

        memon = cls()

        try:
            meta = _dict["metadata"]

            memon.song_title = meta["song title"]
            memon.artist = meta["artist"]
            memon.music_path = meta["music path"]
            memon.jacket_path = meta["jacket path"]
            memon.BPM = meta["BPM"]
            memon.offset = meta["offset"]

            for chart in _dict["data"]:
                c = MemonChart.fromDict(chart)
                if c.dif_name in memon.charts:
                    raise ValueError(f"Difficulty names must be unique inside of a Memon file : {chart['dif_name']}")
                memon.charts[c.dif_name] = c

        except KeyError:
            raise ValueError("Invalid memon file structure")
        
        return memon
    
    def jsonify(self):

        meta = dict()
        meta["song title"] = self.song_title
        meta["artist"] = self.artist
        meta["music path"] = self.music_path
        meta["jacket path"] = self.jacket_path
        meta["BPM"] = self.BPM
        meta["offset"] = self.offset

        d = dict()
        d["metadata"] = meta
        d["data"] = [chart.jsonify() for chart in sorted(self.charts.values(),key=MemonChart.cmp_key)]

        return d

    @classmethod
    def fromEve(cls, eveLines: List[EveLine], difName="", ignoreBPM=False):
        
        memon : Memon = cls()

        chart = MemonChart()

        chart.dif_name = difName

        tempo_lines = list(filter(lambda x:x.type=="TEMPO",eveLines))

        if not tempo_lines:
            warnings.warn("The .eve file does not indicate any BPM, a default of 120 will be assumed")
        if len(tempo_lines) >= 1:
            warnings.warn("The .eve file indicates BPM changes, these cannot be reflected in the .memon file")
        
        if not ignoreBPM:
            memon.BPM = (60 * 10**6) / tempo_lines[0].val
        else:
            memon.BPM = 60
            chart.resolution = 300

        for noteLine in filter(lambda x:x.type in ["PLAY","LONG"],eveLines):

            if ignoreBPM:
                chart.notes.add(MemonNote.fromEveLineIgnoringBPM(noteLine))
            else:
                chart.notes.add(MemonNote.fromEveLine(noteLine,memon.BPM,chart.resolution))
        
        memon.charts[chart.dif_name] = chart

        return memon




if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(prog="memon2eve")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--reversed",dest="reversed",action="store_true",help="Convert eve to memon instead")
    parser.add_argument("--ignore-BPM", dest="ignoreBPM",action="store_true",help="Ignore BPM when converting from .eve")

    args = parser.parse_args()

    inputFile = Path(args.input)
    outputFile = Path(args.output)

    if args.reversed:

        eveLines = []

        with open(inputFile,"r") as eveFile:
            for line in eveFile:
                if line.strip():
                    eveLines.append(EveLine.fromString(line))

        memon = Memon.fromEve(eveLines,difName=inputFile.stem,ignoreBPM=args.ignoreBPM)

        with open(outputFile,"w") as memonFile:
            json.dump(memon.jsonify(),memonFile,indent=4)

    else:

        with open(inputFile,"r") as memonFile:
            memon = Memon.fromDict(json.load(memonFile))
        
        for _, chart in memon.charts:
            evePath = outputFile.parent/(outputFile.stem + f" [{chart.dif_name}]")
            with open(evePath,"w") as eveFile:
                for line in chart.toEve(memon.BPM):
                    eveFile.write(f"{line!s}\n")
        


