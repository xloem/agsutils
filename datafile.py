import dissect.cstruct

# You can implement your own types by subclassing BaseType or RawType, and
# adding them to your cstruct instance with addtype(name, type)

TRUE = 0xffffffffffffffff
FALSE = 0
def break0():
    import pdb; pdb.set_trace()
    return 0
dissect.cstruct.expression.Expression.operators.extend([
    ['andsumright', lambda x, y: x & sum(y)], # operate on lists of 1s or 0s to calculate an entry for each item with a value of 1
    ['<',  lambda x, y: TRUE if x <  y else FALSE],
    ['<=', lambda x, y: TRUE if x <= y else FALSE],
    ['==', lambda x, y: TRUE if x == y else FALSE],
    ['>=', lambda x, y: TRUE if x >= y else FALSE],
    ['>',  lambda x, y: TRUE if x >  y else FALSE],
])

class ZeroTerminated(dissect.cstruct.RawType):
    def __init__(self, cstruct, type):
        self.subtype = cstruct.typedefs[type]
        super().__init__(cstruct, self.subtype.name, 0, self.subtype.alignment)
    def __getattr__(self, name):
        return getattr(self.subtype, name)
    def _read(self, stream, context = None):
        return self.subtype._read_0(stream, context)
    def _write(self, stream, data):
        return self.subtype._write_0(stream, data)
    def default(self):
        return self.subtype.default

class ConditionalType(dissect.cstruct.RawType):
    def __init__(self, cstruct, subtype, default_value):
        self.subtype = cstruct.typedefs[subtype]
        self.default_value = default_value
        super().__init__(cstruct, self.subtype.name, 0, self.subtype.alignment)
    def __getattr__(self, name):
        return getattr(self.subtype, name)
    def _read_array(self, stream, count, context = None):
        assert count == TRUE or count == 0
        if count:
            return self.subtype._read(stream, context)
        else:
            return self.default_value
    def _write_array(self, stream, data):
        if data is not None and data != self.default_value:
            return self.subtype._write(stream, data) 
        else:
            return 0
    def default_array(self):
        return self.default_value

#class ConstantType(dissect.cstruct.BaseType):
#    def __init__(self, cstruct, type, value):
#        self.subtype = cstruct.typedefs[type]
#        self.value = value
#    def __getattr__(self, name):
#        return getattr(self.subtype, name)
#    def _read(self, stream, context = None):
#        data = self.subtype._read(stream, context)
#        assert data == self.value
#        return data
#    def _read_array(self, stream, count, context = None):
#        if self.value == b'SCOM':
#            import pdb; pdb.set_trace()
#        data = self.subtype._read_array(stream, count, context)
#        assert data == self.value
#        return data
#    def _write(self, stream, data):
#        assert data == self.value
#        return self.subtype._write(stream, data)
#    def default(self):
#        return self.value
#    def default_array(self):
#        return self.value

class LengthPrefixedArray(dissect.cstruct.RawType):
    def __init__(self, cstruct, prefixtype, itemtype):
        self.prefixtype = cstruct.typedefs[prefixtype]
        self.itemtype = cstruct.typedefs[itemtype]
        self.brk = itemtype == 'cstr'
        super().__init__(cstruct, self.itemtype.name, 0, max(self.itemtype.alignment, self.prefixtype.alignment))
    def __getattr__(self, name):
        return getattr(self.itemtype, name)
    def _read(self, stream, context = None):
        #if self.brk:
        #    import pdb; pdb.set_trace()
        count = self.prefixtype._read(stream, context)
        return self.itemtype._read_array(stream, count, context)
    def _write(self, stream, data):
        return self.prefixtype._write(stream, len(data)) + self.itemtype._write_array(stream, data)
    def default(self):
        return self.itemtype.default_array()

class AdditionEncryptedString(LengthPrefixedArray):
    def __init__(self, cstruct, prefixtype, key):
        super().__init__(cstruct, prefixtype, 'uint8')
        self.key = key
    def _read(self, stream, context = None):
        encrypted = super()._read(stream, context)
        decrypted = bytes([
            (encrypted[idx] - self.key[idx % len(self.key)]) & 0xff
            for idx in range(len(encrypted))
        ]).decode()
        assert decrypted[-1] == '\0'
        return decrypted[:-1]
    def _write(self, stream, decrypted):
        decrypted = (decrypted + '\0').encode()
        encrypted = bytes([
            (decrypted[idx] + self.key[idx % len(self.key)]) & 0xff
            for idx in range(len(decrypted))
        ])
        return super()._write(encrypted)

#class MaskItems(dissect.cstruct.BaseType):
#    def __init__(self, cstruct, itemtype, setval = 1, unsetval = 0):
#        self.itemtype = cstruct.typedefs[itemtype]
#        self.setval = setval
#        self.unsetval = unsetval
#        super().__init__(cstruct)
#    def __getattr__(self, name):
#        return getattr(self.itemtype, name)
#    def _read_array(self, stream, count, context = None):
#        result = []
#        for item in count:
#            assert item in [self.setval, self.unsetval]
#            if item == self.setval:
#                item = self.subtype._read(stream, context)
#            else:
#                item = None
#            result.append(item)
#        return result
#    def _write_array(self, stream, data):
#        result = 0
#        for item in data:
#            if item is not None:
#                result += self.subtype._write(stream, item)
#        return result

cstructs = dissect.cstruct.cstruct()
cstructs.addtype('cstr', ZeroTerminated(cstructs, 'char'))
#cstructs.addtype('SCOMchars', Constant(cstructs, 'char', b'SCOM'))
cstructs.addtype('uint32_cond_or_0', ConditionalType(cstructs, 'uint32', 0))
cstructs.addtype('uint32_cond_or_6000', ConditionalType(cstructs, 'uint32', 6000))
cstructs.addtype('uint32_chars', LengthPrefixedArray(cstructs, 'uint32', 'char'))
cstructs.addtype('uint32_uint32_chars', LengthPrefixedArray(cstructs, 'uint32', 'uint32_chars'))
cstructs.addtype('uint32_cstrs', LengthPrefixedArray(cstructs, 'uint32', 'cstr'))
cstructs.addtype('uint32_uint8s', LengthPrefixedArray(cstructs, 'uint32', 'uint8'))
cstructs.addtype('uint32_uint32s', LengthPrefixedArray(cstructs, 'uint32', 'uint32'))
cstructs.addtype('uint32_int32s', LengthPrefixedArray(cstructs, 'uint32', 'int32'))
cstructs.addtype('encrypted', AdditionEncryptedString(cstructs, 'uint32', b'Avis Durgan'))
#cstructs.addtype('cstr_for', MaskItems(cstructs, 'cstr', 1, 0)
#cstructs.addtype('encrypted_for', MaskItems(cstructs, 'encrypted', 1, 0)
#cstructs.load('typedef cstr_for[f_g_msgs] cstr_for_f_g_msgs;')
#cstructs.load('typedef encrypted_for[f_g_msgs] encrypted_for_f_g_msgs;')
#cstructs.addtype('cstr_for_f_g_msgs_cond_or_[]', ConditionalType(cstructs, 'cstr_for_f_g_msgs', []))
#cstructs.addtype('encrypted_for_f_g_msgs_cond_or_[]', ConditionalType(cstructs, 'encrypted_for_f_g_msgs', []))

cdef = '''
union Col4x8 {
  struct {
    uint8 r;
    uint8 g;
    uint8 b;
    uint8 a;
  };
  uint8 chans[4];
};
union Coord2x32 {
  struct {
     int32 x;
     int32 y;
  };
  uint32 coords[2];
};
union Coord2x16 {
  struct {
     int16 x;
     int16 y;
  };
  uint16 coords[2];
};
struct Font00 {
  uint8 flags;
  uint8 outline;
};
struct Font48 {
  uint32 yoffset;
};
struct Font49 {
  uint32 yoffset;
  uint32 linespacing;
};
struct Font50 {
  uint32 flags;
  uint32 sizemultiplier;
   int32 outline;
   int32 yoffset;
   int32 linespacing;
};
struct Item {
  char name[24];
  uint8 padding_head[4];
  uint32 image;
  uint32 cursor;
  Coord2x32 hotspot;
  uint8 padding_tail[5*4];
  uint32 f_start_with;
};
struct Cursor {
  uint32 image;
  Coord2x16 hotspot;
  int16 anim;
  char name[10];
  uint32 flags;
};
struct CommandList00 {
  uint8 flag;
  uint32_cond_or_0 n_cmds[flag == 1];
  uint32 types[n_cmds];
   int32 f_resps[n_cmds];
  uint8 unimplemntedted[unimplemented use MaskItems to implement];
};
struct CommandList33 {
  uint32_cstrs cmds;
};
struct Word {
  encrypted word;
  uint16 group;
};
struct View00 {
  uint8 notimp[not implemented];
};
struct Frame33 {
  uint32 pic;
  Coord2x16 offs;
  uint16 speed;
  uint8 speed_padding[2];
  uint32 flags;
   int32 sound;
  uint8 padding[8];
};
struct Loop33 {
  uint16 n_frames;
  uint32 flags;
  Frame33 frames[n_frames];
};
struct View33 {
  uint16 n_loops;
  Loop33 loops[n_loops];
};
struct Placement {
  cstr name;
  int32 offset;
};
struct Script {
  char SCOM[4];
  uint32 ver;
  uint32 g_datasize;
  uint32 codesize;
  uint32 strsize;
  uint8 g_data[g_datasize];
  int32 code[codesize];
  uint8 strs[strsize];
  uint32 n_fixups;
  uint8 fixup_types[n_fixups];
  int32 fixups[n_fixups];
  uint32_cstrs imports;
  uint32 n_exports;
  Placement exports[n_exports];
  uint32_cond_or_0 n_sections[ver >= 83];
  Placement sections[n_sections];
  uint8 BEEFCAFE[4];
};
struct Character {
  uint32 def_view;
  uint32 talk_view;
  uint32 view;
  uint32 room;
  uint32 prev_room;
  Coord2x32 pos;
  uint32 wait;
  uint32 flags;
  uint16 following;
  uint16 follow_info;
  uint32 idle_view;
  uint16 idle_time;
  uint16 idle_left;
  uint16 transparency;
  uint16 baseline;
  uint32 active_inv;
  Col4x8 talk_col;
  uint32 think_view;
  uint16 blink_view;
  uint16 blink_interval;
  uint16 blink_timer;
  uint16 blink_frame;
  uint16 walkspeed_y;
  uint16 pic_yoffs;
  uint32 pos_z;
  uint32 walk_wait;
  uint16 talk_speed;
  uint16 idle_speed;
  Coord2x16 blocking;
  uint32 index_id;
  uint16 pic_xoffs;
  uint16 walkwaitcounter;
  uint16 loop;
  uint16 frame;
  uint16 walking;
  uint16 animating;
  uint16 walkspeed;
  uint16 animspeed;
  uint16 f_items[301];
  Coord2x16 act;
  char name[40];
  char script[20];
  uint8 on;
  uint8 padding;
};
struct DataFile {
  char SIG[30];
  uint32 data_version;
  uint32_cond_or_0 editor_version_len[data_version >= 12];
  char editor_version[editor_version_len];
  uint32_cond_or_0 n_caps[data_version >= 48];
  uint32_uint8s caps[n_caps];
  char game_name[50];
  uint8 padding_base_name[2];
  int32 options[100];
  uint8 pal_class[256];
  Col4x8 palette[256];
  uint32 n_views;
  uint32 n_chars;
  uint32 player_id;
  uint32 max_score;
  uint32 n_items:16;
  uint32 n_dlgs;
  uint32 n_msgs;
  uint32 n_fonts;
  uint32 col_depth;
  uint32 target_win;
  uint32 dlg_bullet;
  uint16 hotspot_dot;
  uint16 hotspot_cross;
  uint32 unique_id;
  uint32 n_guis;
  uint32 n_cursors;
  uint32 res_id;
  uint32 res_custom[data_version >= 43 & res_id == 8 & 2]; // note: (((data_version >= 43) & res_id) == 8) & 2
  uint32 lipsync_frame;
  uint32 inv_hotspot;
  uint8 padding_reserved[17*4];
  uint32 f_g_msgs[500];
  uint32 f_dict;
  uint32 f_g_script;
  uint32 f_chars;
  uint32 f_scom;
  char guid[data_version > 32 & 40];
  char save_ext[data_version > 32 & 20];
  char save_dir[data_version > 32 & 50];
  Font00 fonts00[data_version < 50 & n_fonts];
  Font48 fonts48[data_version == 48 & n_fonts];
  Font49 fonts48[data_version == 49 & n_fonts];
  Font50 fonts50[data_version >= 50 & n_fonts];
  uint32_cond_or_6000 n_sprites[data_version > 23];
  uint8 sprite_flags[n_sprites];
  uint8 padding_item[68];
  Item items[n_items-1];
  Cursor cursors[n_cursors];
  CommandList00 char_evts00[data_version <  33 & n_chars];
  CommandList33 char_evts33[data_version >= 33 & n_chars];
  CommandList00 item_evts00[data_version <  33 & n_items-1];
  CommandList33 item_evts33[data_version >= 33 & n_items-1];
  uint32_cond_or_0 n_g_vars[data_version < 33];
  uint8 g_vars[n_g_vars][28];
  uint32_cond_or_0 n_words[f_dict == 1];
  Word dict[n_words];
  Script g_scripts[data_version >= 38 & 1 + 1];
  uint32_cond_or_0 n_scripts[data_version >= 31];
  Script scripts[n_scripts];
  View00 views[data_version <  33 & n_views];
  View33 views[data_version >= 33 & n_views];
  uint8 unknown[data_version < 20 & 0x204];
  Character chars[n_chars];
  uint32_uint8s lipsyncframes[data_version >= 20 & 50];
  cstr g_msgs00[data_version < 26 andsumright f_g_msgs];
  encrypted g_msgs26[data_version >= 26 andsumright f_g_msgs];
};
'''
cstructs.load(cdef, compiled=False)
class DataFile:
    @classmethod
    def from_stream(self, stream):
        #import pdb; pdb.set_trace()
        datafile = cstructs.DataFile(stream)
        return datafile
#from typing import Annotated  # use typing_extensions on Python <3.9
#import dataclasses_struct as dcs
#
#class BytesConst(dcs.BytesField):
#    def __init__(self, value):
#        super().__init__(len(value))
#        self.value = value
#    def validate(self, val: bytes):
#        if val != self.value:
#            raise ValueError(f'{val} should be {self.value}')
#
#class Versioned(dcs.Field):
#    def __init__(
#
#
#@dcs.dataclass(dcs.LITTLE_ENDIAN)
#class DataFile:
#    SIG : BytesConst(b'Adventure Creator Game File v2')
#    data_version : dcs.U32
#    editor_version

import builtins

class OldDataFile:
    @classmethod
    def from_stream(cls, file):
        def bytes(ct=None):
            if ct is None:
                ct = uint()
            data = file.read(ct)
            assert len(data) == ct
            return data
        def uchar():
            return int.from_bytes(bytes(1), 'little', signed=False)
        def sshort():
            return int.from_bytes(bytes(2), 'little', signed=True)
        def ushort():
            return int.from_bytes(bytes(2), 'little', signed=False)
        def sint():
            return int.from_bytes(bytes(4), 'little', signed=True)
        def uint():
            return int.from_bytes(bytes(4), 'little', signed=False)
        def bool(size=1):
            v = int.from_bytes(bytes(size), 'little', signed=False)
            assert v & 1 == v
            return v == 1
        def str(len=None):
            return bytes(len).decode().rstrip('\0')
        def cstr():
            # could maybe simplify by enforcing file is io.BufferedReader, maybe using TextWrapper or something
            data = b''
            str = ' '
            while str[-1] != '\0':
                data += bytes(1)
                str = data.decode()
            return str[:-1]
        def vec(typ, params=[], kwparams={}, ct=None):
            if ct is None:
                ct = uint()
            return [typ(*params, **kwparams) for x in range(ct)]
        def decrypt(data):
            decrypted = builtins.bytes([
                (data[idx] + 0x100 - cls.PWD[idx % len(cls.PWD)]) & 0xff
                for idx in range(len(data))
            ]).decode()
            assert decrypted[-1] == '\0'
            return decrypted[:-1]
        def interactions(ct):
            interactions = []
            if data_version > 32:
                for idx in range(ct):
                    interactions.append(vec(cstr))
            else:
                assert not "command lists in old versions"
                for idx in range(ct):
                    if bool():
                        evt_types = vec(uint)
                        resps = vec(sint, ct=len(evt_types))
                        for evt_idx in range(len(evt_types)):
                            if resps[evt_idx]:
                                n_childs = uint()
                                timesrun = uint()
                                for child_idx in range(n_childs):
                                    assert uint() == 0
                                    type = uint()
                                    for idx2 in range(5):
                                        valtype = uchar()
                                        assert bytes(3) == 0
                                        val = uint()
                                        extra = uint()
                                    children = uint()
                                    parent = uint()
                                # then there is another command list for each child with children
            return interactions
        def name_off():
            return [cstr(), sint()]
        def scom():
            assert str(4) == 'SCOM'
            ver = uint()
            g_datasize = uint()
            codesize = uint()
            strsize = uint()
            g_data = bytes(g_datasize)
            code = vec(sint, ct=codesize)
            strs = bytes(strsize)
            n_fixups = uint()
            fixup_types = vec(uchar, ct=n_fixups)
            fixups = vec(sint, ct=n_fixups)
            imports = vec(cstr)
            exports = vec(name_off)
            sections = vec(name_off) if ver >= 83 else []
            assert uint() == 0xbeefcafe
            return [ver, g_data, code, strs, fixup_types, fixups, imports, exports, sections]

        assert len(cls.SIG) == 30
        file_sig = bytes(30)
        assert file_sig == cls.SIG
        data_version = uint()
        editor_version = str() if data_version >= 12 else ''
        if data_version >= 48:
            caps = vec(str)
        else:
            caps = []
        game_name = str(50)
        assert bytes(2) == b'\0\0' # base name padding
        # NativeConstants.GameOptions
        options = vec(sint, ct=100)
        pal_class = vec(bytes, [1], ct=256)
        palette = vec(vec, [uchar], {'ct':4}, ct=256)
        n_views = uint()
        n_chars = uint()
        player_id = uint()
        max_score = uint()
        n_items = ushort() - 1
        assert bytes(2) == b'\0\0'
        n_dialogs = uint()
        n_msgs = uint()
        n_fonts = uint()
        col_depth = uint()
        target_win = uint()
        dialog_bullet = uint()
        hotspot_dot = ushort()
        hotspot_cross = ushort()
        unique_id = uint()
        n_guis = uint()
        n_cursors = uint()
        res = uint()
        if data_version >= 43 and res == 8:
            res = vec(uint, ct=2)
        lipsync_frame = uint()
        inv_hotspot = uint()
        assert not any(vec(uint, ct=17))
        g_msg_mask = vec(bool, [4], ct=500)
        n_g_msgs = sum(g_msg_mask)
        has_dict = bool(4)
        has_globalscript = bool(4)
        has_chars = bool(4)
        has_compiled_script = bool(4)
        if data_version > 32:
            guid = str(40)
            save_ext = str(20)
            save_dir = str(50)
        else:
            guid = None
            save_ext = None
            save_dir = None
        # NativeConstants.FFLG_*
        if data_version < 50:
            # flags, outline
            font_ints = vec(vec, [uchar], {'ct':2}, ct=n_fonts)
            if data_version == 48:
                # yoffset
                font_ints_2 = vec(vec, [uint], {'ct':1}, ct=n_fonts)
            elif data_version == 49:
                # yoffset, linespqcing
                font_ints_2 = vec(vec, [uint], {'ct':2}, ct=n_fonts)
            else:
                font_ints_2 = vec(list, ct=n_fonts)
            font_ints = [font_ints[x] + font_ints_2[x] for x in range(n_fonts)]
        else:
            assert data_version == 50
            # flags, sizemultiplier, outline, verticaloffset, linespacing
            font_ints = vec(vec, [uint], {'ct':5}, ct=n_fonts)

        if data_version < 24:
            n_sprites = 6000
        else:
            n_sprites = uint()
        sprite_flags = vec(bytes, [1], ct=n_sprites)
        assert not bool(68)
        items = []
        for idx in range(n_items):
            descr = str(24)
            assert uint() == 0
            image = uint()
            cursor = uint()
            hotspot_x = uint()
            hotspot_y = uint()
            assert not bool(5*4)
            startwith = bool(4)
            items.append([descr, image, cursor, hotspot_x, hotspot_y])
        cursors = []
        for idx in range(n_cursors):
            image = uint()
            hotspot_x = ushort()
            hotspot_y = ushort()
            anim = sshort()
            name = str(9)
            assert uchar() == 0
            flags = uchar()
            assert not bool(3)
            cursors.append([image, hotspot_x, hotspot_y, anim, name, flags])
        char_evts = interactions(n_chars)
        item_evts = interactions(n_items)
        if data_version <= 32:
            n_globalvars = uint()
            globalvars = vec(bytes, [28], ct=n_globalvars)
        if has_dict:
            n_words = uint()
            # word, word group
            words = [[decrypt(bytes()), ushort()] for word_idx in range(n_words)]
        else:
            words = None
        g_script = scom()
        if data_version > 37:
            dialog_script = scom()
        else:
            dialog_script = None
        if data_version >= 31:
            scripts = vec(scom)
        else:
            scripts = []
        if data_version > 32:
            views = []
            for view_idx in range(n_views):
                n_loops = ushort()
                loops = []
                for loop_idx in range(n_loops):
                    n_frames = ushort()
                    loop_flags = uint() # probably 3 bytes padding
                    frames = []
                    for frame_idx in range(n_frames):
                        pic = uint()
                        xoffs = ushort()
                        yoffs = ushort()
                        speed = ushort()
                        assert ushort() == 0
                        flags = uint() # probably 3 bytes padding
                        sound = sint()
                        assert not any(bytes(8))
                        frames.append([pic, xoffs, yoffs, speed, flags, sound])
                    loops.append([loop_flags, frames])
                views.append(loops)
        else:
            assert not "implemented older views"
            
        if data_version <= 19:
            bytes(uint()*0x204) # unknown

        # NativeConstants.CHF_*
        chars = []
        for char_idx in range(n_chars):
            def_view, talk_view, view, room, prev_room, x, y, wait, flags = vec(uint, ct=9)
            following, follow_info = ushort(), ushort()
            idle_view = uint()
            idle_time, idle_left, transparency, baseline = vec(ushort, ct=4)
            active_inv, talk_col, think_view = uint(), uint(), uint()
            blink_view, blink_interval, blink_timer, blink_frane, walkspeed_y, pic_yoffs = vec(ushort, ct=6)
            z, walk_wait = uint(), uint()
            talk_speed, idle_speed = ushort(), ushort()
            blocking_width, blocking_height = ushort(), ushort()
            idx_id = uint()
            pic_xoffs, walkwaitcounter, loop, frame = vec(ushort, ct=4)
            walking, animating, walkspeed, animspeed = vec(ushort, ct=4)
            items = vec(ushort, ct=301)
            assert all([item < 2 for item in items])
            actx, acty = ushort(), ushort()
            name = str(40)
            script = str(20)
            on = uchar()
            assert uchar() == 0
            chars.append([
                def_view, talk_view, view, room, prev_room, x, y, wait, flags,
                following, follow_info, idle_view,
                idle_time, idle_left, transparency, baseline,
                active_inv, talk_col, think_view,
                blink_view, blink_interval, blink_timer, blink_frane, walkspeed_y, pic_yoffs,
                z, walk_wait, talk_speed, idle_speed,
                blocking_width, blocking_height, idx_id,
                pic_xoffs, walkwaitcounter, loop, frame,
                walking, animating, walkspeed, animspeed,
                items, actx, acty, name, script, on,
            ])

        if data_version > 19:
            lipsyncframes = vec(str, [50], ct=20)
        else:
            libsyncframes = []
    
        for idx in range(len(g_msg_mask)):
            if g_msg_mask[idx]:
                if data_version < 26:
                    g_msg_mask[idx] = cstr()
                else:
                    g_msg_mask[idx] = decrypt(bytes())
            else:
                g_msg_mask[idx] = None

        assert not "dialog topics and further content"

            
    SIG = b"Adventure Creator Game File v2"
    PWD = b"Avis Durgan"

if __name__ == '__main__':
    with open('ags-camdemo/build/files/game28.dta','rb') as f:
        datafile = DataFile.from_stream(f)
        print(datafile)
