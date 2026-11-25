"""Rebuild the Optima row in a sandbox copy of this particular workspace schema."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import struct
import sys

import olefile
import pythoncom

NAME = "Amti Optima OR6-7-OP-1K-STT 10409M"
NATIVE = "ForcePlateSettingsAmtiGen5"

def posval(blob, pos):
    return struct.unpack_from("<I", blob, pos)[0]

def pack(*values):
    return struct.pack("<" + "I" * len(values), *values)

def read_meta(blob):
    classes = {}
    cursor = 8
    for identifier in range(1, posval(blob, 0) + 1):
        start = cursor
        length = posval(blob, cursor)
        title = blob[cursor+4:cursor+3+length].decode("ascii")
        cursor += 4 + length
        cursor += 4 + posval(blob, cursor)
        cursor += 4
        classes[title] = (identifier, blob[start:cursor])
    definitions = {}
    end_classes = cursor
    cursor += 8
    for identifier in range(1,posval(blob,end_classes)+1):
        start = cursor
        length = posval(blob,cursor)
        title = blob[cursor+4:cursor+3+length].decode("ascii")
        description_at = cursor+4+length+5
        description_length = posval(blob,description_at)
        assert blob[description_at+4:description_at+4+description_length].decode("utf-16le").rstrip("\0") == title
        cursor = description_at+4+description_length+20
        definitions[title] = (identifier,blob[start:cursor])
    assert cursor == len(blob)
    return classes, end_classes, definitions

def plate(blob, name, base_field):
    encoded = name.encode("utf-16le")
    name_at = blob.index(pack(base_field, 6+len(encoded), len(name))+encoded)
    start = name_at-28
    header = struct.unpack_from("<7I", blob, start)
    assert header[3:5] == ({5:4,29:8}[base_field], 8)
    fields = {}
    cursor = name_at
    for unused in range(header[2]-1):
        field_id, size = struct.unpack_from("<II", blob, cursor)
        fields[field_id] = blob[cursor+8:cursor+8+size]
        cursor += 8+size
    assert blob[cursor:cursor+12] == bytes(12), (name,cursor)
    return start, cursor, header, fields

def rewrite_file(source, recording, candidate):
    assert source.resolve() != candidate.resolve() and not candidate.exists()
    with olefile.OleFileIO(source) as q, olefile.OleFileIO(recording) as rec:
        stream = "Workspace NBC/"
        meta = q.openstream(stream+"Metadata").read()
        data = q.openstream(stream+"Data Items").read()
        rec_meta = rec.openstream("Measurement NBC/Metadata").read()
        rec_data = rec.openstream("Measurement NBC/Data Items").read()
        classes, end_classes, props = read_meta(meta)
        measured_classes, _, measured_props = read_meta(rec_meta)
        assert posval(meta,0)==17 and posval(meta,end_classes)==166 and meta[-4:]==bytes(4)
        assert NATIVE not in classes and measured_classes[NATIVE][0] == 17

        extra = ("Model Number String", "Serial Number String", "Is Optima",
                 "Amplifier Serial Number String", "Plate rotation")
        extra_descriptions = []
        for identifier, name in enumerate(extra, 167):
            assert name not in props
            extra_descriptions.append(measured_props[name][1])
        new_meta = (pack(18)+meta[4:end_classes]+measured_classes[NATIVE][1]+
                    pack(171)+meta[end_classes+4:]+b"".join(extra_descriptions))

        a,b,workspace_header,placeholder = plate(data,NAME,5)
        # The recording has two names for the same device. The field ID
        # selects the device-settings item and excludes the force-series row.
        _,_,native_header,native = plate(rec_data,NAME,29)
        assert native_header[0]==17 and workspace_header[0]==5
        assert list(native)==[29,30,*range(48,59)]
        assert native[30]==b"\x01" and placeholder[6]==b"\x01"
        before,_,_,generic = plate(data,"Force-plate 1",5)
        assert before < a and generic[6] in (b"\x00", b"\x01")
        generic_start = before + 28 + 8 + len(generic[5])
        assert data[generic_start:generic_start+9] == pack(6,1)+generic[6]
        data = data[:generic_start+8] + b"\x00" + data[generic_start+9:]
        names = ("Plate Offset XYZ","Force Plate Width","Force Plate Length",
                 "Force Plate Corners XYZ","Use CoP Filter","CoP Level Z")
        field_map = {measured_props[name][0]: props[name][0] for name in names}
        assert field_map == dict(zip(range(48,54),range(24,30)))
        field_map.update({29:5,30:6,**dict(zip(range(54,59),range(167,172)))})
        record = b"".join(pack(field_map[key],len(value))+value for key,value in native.items())
        new_data = data[:a] + pack(18,workspace_header[1],native_header[2],*workspace_header[3:]) + record + data[b:]
        assert read_meta(new_meta)[0][NATIVE][0] == 18
        _,_,hdr,parsed = plate(new_data,NAME,5)
        assert hdr[0]==18 and parsed=={field_map[key]:value for key,value in native.items()}

    candidate.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,candidate)
    storage = pythoncom.StgOpenStorage(str(candidate),None,0x12)
    workspace = storage.OpenStorage("Workspace NBC",None,0x12)
    for name, value in (("Metadata",new_meta), ("Data Items",new_data)):
        stream = workspace.OpenStream(name,None,0x12)
        stream.SetSize(len(value))
        stream.Write(value)
        stream.Commit(0)
        del stream
    workspace.Commit(0)
    storage.Commit(0)
    del workspace,storage
    with olefile.OleFileIO(source) as old, olefile.OleFileIO(candidate) as new:
        assert old.listdir()==new.listdir()
        changed=[name for name in old.listdir() if old.openstream(name).read()!=new.openstream(name).read()]
        assert sorted(changed)==[["Workspace NBC","Data Items"],["Workspace NBC","Metadata"]]
        assert new.openstream("Workspace NBC/Data Items").read()==new_data
        assert new.openstream("Workspace NBC/Metadata").read()==new_meta
    print(json.dumps({"backup":str(source),"reference":str(recording),
                      "candidate":str(candidate),"candidate_sha256":hashlib.sha256(candidate.read_bytes()).hexdigest(),
                      "changed_OLE_streams":changed},indent=2))

if __name__ == "__main__":
    rewrite_file(*(Path(p) for p in sys.argv[1:]))
