# -*- coding: utf-8 -*-
"""Compile .po → .mo sans gettext (msgfmt minimal, suffisant pour des entrées simples)."""
import re
import struct
import sys


def parse_po(path):
    entries = {}
    msgid = msgstr = None
    state = None
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            if line.startswith('msgid '):
                if msgid is not None and msgstr:
                    entries[msgid] = msgstr
                msgid = eval(line[6:], {}, {})
                msgstr = None
                state = 'id'
            elif line.startswith('msgstr '):
                msgstr = eval(line[7:], {}, {})
                state = 'str'
            elif line.startswith('"'):
                value = eval(line, {}, {})
                if state == 'id':
                    msgid += value
                elif state == 'str':
                    msgstr += value
    if msgid is not None and msgstr:
        entries[msgid] = msgstr
    return entries


def write_mo(entries, path):
    keys = sorted(entries.keys())
    offsets = []
    ids = strs = b''
    for key in keys:
        id_b = key.encode('utf-8')
        str_b = entries[key].encode('utf-8')
        offsets.append((len(ids), len(id_b), len(strs), len(str_b)))
        ids += id_b + b'\x00'
        strs += str_b + b'\x00'
    n = len(keys)
    keystart = 7 * 4 + 16 * n
    valuestart = keystart + len(ids)
    koffsets = []
    voffsets = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    output = struct.pack('Iiiiiii', 0x950412de, 0, n, 7 * 4, 7 * 4 + n * 8, 0, 0)
    output += struct.pack(f'{len(koffsets)}i', *koffsets)
    output += struct.pack(f'{len(voffsets)}i', *voffsets)
    output += ids + strs
    with open(path, 'wb') as fh:
        fh.write(output)


if __name__ == '__main__':
    po, mo = sys.argv[1], sys.argv[2]
    entries = parse_po(po)
    # l'en-tête (msgid "") doit être présent dans le .mo
    entries.setdefault('', 'Content-Type: text/plain; charset=UTF-8\n')
    write_mo(entries, mo)
    print(f'{len(entries)} entrées → {mo}')
