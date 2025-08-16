"""Noesis Python Plugin

      File: tex_castlevania_cod_xbox.py
   Authors: Laurynas Zubavičius (Sparagas)
   Purpose: Castlevania: Curse of Darkness (Microsoft - Xbox)

  Category: Image
"""

from inc_noesis import *


def registerNoesisTypes():
    handle = noesis.register("Castlevania: Curse of Darkness (Xbox)", ".tex")
    noesis.setHandlerTypeCheck(handle, check_type)
    noesis.setHandlerLoadRGBA(handle, castlevania_textures)
    return 1


def check_type(data):
    return 1


def castlevania_textures(data, tex_list):

    class IdxHdr:
        def __init__(self):
            bs.seek(4, NOESEEK_REL)
            self.ofs_idx_dat = bs.readUInt()
            bs.seek(24, NOESEEK_REL)
            self.w = bs.readUInt()
            self.h = bs.readUInt()
            bs.seek(4, NOESEEK_REL)
            self.ofs_idx_dat = bs.readUInt()

    class PalHdr:
        def __init__(self):
            bs.seek(4, NOESEEK_REL)
            self.ofs_pal_dat = bs.readUInt()
            bs.seek(36, NOESEEK_REL)
            self.ofs_pal_dat = bs.readUInt()

    bs = NoeBitStream(data)
    name = rapi.getExtensionlessName(rapi.getInputName())
    
    bs.seek(64)
    idx_hdr = IdxHdr()
    pal_hdr = PalHdr()
    
    if idx_hdr.ofs_idx_dat != 0:
        bs.seek(idx_hdr.ofs_idx_dat + 64);
        idx_buf = bs.readBytes(idx_hdr.w * idx_hdr.h)

    bs.seek(pal_hdr.ofs_pal_dat + 64 + 48);
    pal_buf = bs.readBytes(4 * 256)

    if idx_hdr.ofs_idx_dat != 0:
        img_buf = rapi.imageDecodeRawPal(idx_buf, pal_buf, idx_hdr.w, idx_hdr.h, 8, 'b8g8r8a8')
        img_buf = rapi.imageFromMortonOrder(img_buf, idx_hdr.w, idx_hdr.h, 4)
        img_buf = NoeTexture(name, idx_hdr.w, idx_hdr.h, img_buf, noesis.NOESISTEX_RGBA32)
    else:
        img_buf = rapi.imageDecodeRaw(pal_buf, 16, 16, 'b8g8r8a8')
        img_buf = NoeTexture(name, 16, 16, img_buf, noesis.NOESISTEX_RGBA32)

    img_buf.setFlags(noesis.NTEXFLAG_FILTER_NEAREST)
    tex_list.append(img_buf)

    return 1
