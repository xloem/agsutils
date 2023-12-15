import warnings
warnings.warn('this code was made against xloem/cstruct/merged')
import dissect.cstruct

# You can implement your own types by subclassing BaseType or RawType, and
# adding them to your cstruct instance with addtype(name, type)

TRUE = 0xffffffffffffffff
FALSE = 0
dissect.cstruct.expression.Expression.binary_operators.update({
#    ['members', lambda x, y: [getattr(z, y) for z in x]],
    'andsumright': lambda x, y: x & sum(y), # operate on lists of 1s or 0s to calculate an entry for each item with a value of 1
    'lt':  lambda x, y: TRUE if x <  y else FALSE,
    'lte': lambda x, y: TRUE if x <= y else FALSE,
    'eq': lambda x, y: TRUE if x == y else FALSE,
    'gte': lambda x, y: TRUE if x >= y else FALSE,
    'gt':  lambda x, y: TRUE if x >  y else FALSE,
})
dissect.cstruct.expression.Expression.precedence_levels.update({
    'andsumright': 0,
    'lt':  0,
    'lte': 0,
    'eq': 0,
    'gte': 0,
    'gt':  0,
})

class ZeroTerminated(dissect.cstruct.BaseType):
    type : dissect.cstruct.BaseType
    @classmethod
    def _read(cls, stream, context = None):
        return cls.type._read_0(stream, context)
        #return cls._read_0(stream, context)
    @classmethod
    def _write(cls, stream, data):
        return cls.type._write_0(stream, data)
        #return cls._write_0(stream, data)

class ConditionalType(dissect.cstruct.BaseType):
    type : dissect.cstruct.BaseType
    dflt : object
    class ArrayType(dissect.cstruct.BaseType, metaclass=dissect.cstruct.types.ArrayMetaType):
        @classmethod
        def _read(cls, stream, context):
            count = cls.num_entries.evaluate(context)
            assert count == TRUE or count == FALSE
            if count == TRUE:
                return cls.type.type._read(stream, context)
            else:
                return cls.type.dflt
        @classmethod
        def _write(cls, stream, data):
            if data is not None and data != cls.dflt:
                return cls.type.type._write(stream, data) 
            else:
                return 0

class ConstantType(dissect.cstruct.BaseType):
    type : dissect.cstruct.BaseType
    class ArrayType(dissect.cstruct.BaseType, metaclass=dissect.cstruct.types.ArrayMetaType):
        @classmethod
        def _read(cls, stream, context):
            expected = cls.num_entries
            expected = cls.type.type(expected)
            data = cls.type.type._read(stream, context)
            assert data == expected
            return data
        @classmethod
        def _write(cls, stream, data):
            expected = cls.num_entries
            expected = cls.type.type(expected)
            assert data == expected
            return cls.type.type._write(stream, data) 

class ValueTerminatedArray(dissect.cstruct.BaseType):
    type : dissect.cstruct.BaseType
    class ArrayType(dissect.cstruct.BaseType, metaclass=dissect.cstruct.types.ArrayMetaType):
        @classmethod
        def _read(cls, stream, context):
            term = cls.num_entries
            term = cls.type.type(term)
            result = []
            while (item := cls.type.type._read(stream, context)) != term:
                result.append(item)
            return result
        @classmethod
        def _write(cls, stream, data):
            result = 0
            for item in data:
                result += cls.type.type._write(stream, item) 
            term = cls.num_entries
            term = cls.type.type(term)
            result += cls.type.type._write(stream, term) 
            return result

#class LengthPrefixedArray:
#    type : dissect.cstruct.BaseType
#    class ArrayType(dissect.cstruct.BaseType, metaclass=dissect.cstruct.types.ArrayMetaType):
#        @classmethod
#        def _read(cls, stream, context):
#            prefixtype = cls.cs._typedefs[cls.num_entries.expression]
#            count = prefixtype._read(stream, context)
#            return cls.type.type._read_array(stream, count, context)
#        @classmethod
#        def _write(cls, stream, data):
#            prefixtype = cls.cs._typedefs[cls.num_entries.expression]
#            return prefixtype._write(stream, len(data)) + cls.type.type._write_array(stream, data) 

class LengthPrefixedArray(dissect.cstruct.BaseType):
    prefixtype : type
    itemtype : type
    @classmethod
    def _read(cls, stream, context = None):
        #import pdb; pdb.set_trace()
        count = cls.prefixtype._read(stream, context)
        # this could maybe be slightly better done now with a nested ArrayType. cdef would need brackets.
        return cls.itemtype._read_array(stream, count, context)
        #array = cls.cs._make_array(cls.itemtype, count)
        #return array._read(stream, context)
    @classmethod
    def _write(cls, stream, data):
        return cls.prefixtype._write(stream, len(data)) + cls.itemtype._write_array(stream, data)
    @classmethod
    def default(cls):
        return self.itemtype.default_array()

class AdditionEncryptedString(LengthPrefixedArray):
    key : object
    @classmethod
    def _read(cls, stream, context = None):
        #import pdb; pdb.set_trace()
        encrypted = super()._read(stream, context)
        decrypted = bytes([
            (encrypted[idx] - cls.key[idx % len(cls.key)]) & 0xff
            for idx in range(len(encrypted))
        ]).decode()
        assert decrypted[-1] == '\0'
        return decrypted[:-1]
    @classmethod
    def _write(cls, stream, decrypted):
        decrypted = (decrypted + '\0').encode()
        encrypted = bytes([
            (decrypted[idx] + cls.key[idx % len(cls.key)]) & 0xff
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
cstructs.add_type('cstr', cstructs._make_type('cstr', (str,ZeroTerminated), None, alignment=1, attrs=dict(type=cstructs.typedefs['char'])))
#cstructs.add_type('SCOMchars', Constant(cstructs, 'char', b'SCOM'))
cstructs.add_type('uint32_const', cstructs._make_type('uint32_const', (int,ConstantType,), None, alignment=4, attrs=dict(type=cstructs.typedefs['uint32'])))
cstructs.add_type('uint32s_to', cstructs._make_type('uint32s_to', (int,ValueTerminatedArray,), None, alignment=4, attrs=dict(type=cstructs.typedefs['uint32'])))
cstructs.add_type('uint32_cond_or_0', cstructs._make_type('uint32_cond_or_0', (int,ConditionalType,), None, alignment=4, attrs=dict(type=cstructs.typedefs['uint32'],dflt=0)))
cstructs.add_type('uint32_cond_or_6000', cstructs._make_type('uint32_cond_or_6000', (int,ConditionalType,), None, alignment=4, attrs=dict(type=cstructs.typedefs['uint32'],dflt=6000)))
cstructs.add_type('uint32_chars', cstructs._make_type('uint32_chars', (str,LengthPrefixedArray), None, alignment=1, attrs=dict(prefixtype=cstructs.typedefs['uint32'], itemtype=cstructs.typedefs['char'])))
cstructs.add_type('uint32_uint32_chars', cstructs._make_type('uint32_uint32_chars', (list,LengthPrefixedArray,), None, alignment=1, attrs=dict(prefixtype=cstructs.typedefs['uint32'], itemtype=cstructs.typedefs['uint32_chars'])))
cstructs.add_type('uint32_cstrs', cstructs._make_type('uint32_cstrs', (str,LengthPrefixedArray,), None, alignment=1, attrs=dict(prefixtype=cstructs.typedefs['uint32'], itemtype=cstructs.typedefs['cstr'])))
cstructs.add_type('uint32_uint8s', cstructs._make_type('uint32_uint8s', (list,LengthPrefixedArray,), None, alignment=1, attrs=dict(prefixtype=cstructs.typedefs['uint32'], itemtype=cstructs.typedefs['uint8'])))
cstructs.add_type('uint32_uint32s', cstructs._make_type('uint32_uint32s', (list,LengthPrefixedArray,), None, alignment=4, attrs=dict(prefixtype=cstructs.typedefs['uint32'], itemtype=cstructs.typedefs['uint32'])))
cstructs.add_type('uint32_int32s', cstructs._make_type('uint32_int32s', (list,LengthPrefixedArray,), None, alignment=4, attrs=dict(prefixtype=cstructs.typedefs['uint32'], itemtype=cstructs.typedefs['int32'])))
cstructs.add_type('encrypted', cstructs._make_type('encrypted', (str,AdditionEncryptedString,), None, alignment=1, attrs=dict(prefixtype=cstructs.typedefs['uint32'], itemtype=cstructs.typedefs['uint8'], key=b'Avis Durgan')))
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
  int32 coords[2];
};
union Coord2x16 {
  struct {
     int16 x;
     int16 y;
  };
  uint16 coords[2];
};
union Coord4x32 {
  struct {
     uint32 x;
     uint32 y;
     uint32 width;
     uint32 height;
  };
  struct {
     Coord2x32 pos;
     Coord2x32 size;
  };
  uint32 coords[4];
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
  uint32_cond_or_0 n_cmds[flag eq 1];
  uint32 types[n_cmds];
   int32 f_resps[n_cmds];
  uint8 unimplemntedted[unimplemented use MaskItems or andsumright to implement];
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
  uint32_const SCOM[0x4d4f4353];
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
  uint32_cond_or_0 n_sections[ver gte 83];
  Placement sections[n_sections];
  uint32_const BEEFCAFE[0xBEEFCAFE];
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
struct Dialog {
  char optionnames[30][150];
  uint32 optionflags[30]; // NativeConstants.DFLG_*
  uint32 optionscripts;
  int16 entrypoints[30];
  int16 startupentrypoint;
  int16 codesize;
  uint32 numoptions;
  uint32 topicflags;
};
struct Dialog00 {
  uint32 unimplemented[old dialog scripts not implemented mqybe use custom type];
};
struct GUIObj000 {
  uint32 unk[7];
};
struct GUIObj106 {
  uint32 unk[7];
  cstr scriptname;
};
struct GUIObj108 {
  uint32 unk[7];
  cstr scriptname;
  uint32_cstrs evt_handlers;
};
struct GUIObj119 {
  //uint32 unk[6];
  uint32 flags;
  Coord2x32 pos;
  Coord2x32 size;
  uint32 zorder;
  cstr scriptname;
  uint32_cstrs evt_handlers;
};
struct GUIButtonData000 {
  uint32 unk[12];
  char text[50];
   int32 alignment;
  uint32 reserved;
};
struct GUIButton119 {
  GUIObj119 ctl;
  uint32 pic;
  uint32 overpic;
  uint32 pushedpic;
  uint32 font;
  uint32 textcol;
   int32 leftclick;
   int32 rightclick;
  uint32 lclickdata;
  uint32 rclickdata;
  cstr text;
   int32 alignment;
};
struct GUI000 {
  uint32 vtext;
  char name[16];
  char onclick[20];
  uint32 coords[5]; // unsure what fifth is or where it is
  uint32 unk[22];
  uint32 objs[30][2];
  uint32 n_buttons;
};
struct GUI118 {
  uint32_chars name;
  uint32_chars onclick;
  Coord2x32 pos;
  Coord2x32 size;
  uint32 n_objs;
  uint32 unk[21];
  uint32 objs[n_objs];
  uint32 n_buttons;
};
struct GUI119 {
  uint32_chars name;
  uint32_chars onclick;
  uint32 x;
  uint32 y;
  uint32 width;
  uint32 height;
  uint32 n_objs;
  uint32 unk[10];
  uint32 objs[n_objs];
  uint32 n_buttons;
};
struct DataFile {
  char SIG[30];
  uint32 data_ver;
  uint32_cond_or_0 editor_ver_len[data_ver gte 12];
  char editor_ver[editor_ver_len];
  uint32_cond_or_0 n_caps[data_ver gte 48];
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
  uint32 res_custom[(data_ver gte 43) & (res_id eq 8) & 2];
  uint32 lipsync_frame;
  uint32 inv_hotspot;
  uint8 padding_reserved[17*4];
  uint32 f_g_msgs[500];
  uint32 f_dict;
  uint32 f_g_script;
  uint32 f_chars;
  uint32 f_scom;
  char guid[(data_ver gte 33) & 40];
  char save_ext[(data_ver gte 33) & 20];
  char save_dir[(data_ver gte 33) & 50];
  Font00 fonts00[(data_ver lt 50) & n_fonts];
  Font48 fonts48[(data_ver eq 48) & n_fonts];
  Font49 fonts49[(data_ver eq 49) & n_fonts];
  Font50 fonts50[(data_ver gte 50) & n_fonts];
  uint32_cond_or_6000 n_sprites[data_ver gt 23];
  uint8 sprite_flags[n_sprites];
  uint8 padding_item[68];
  Item items[n_items-1];
  Cursor cursors[n_cursors];
  CommandList00 char_evts00[(data_ver lt  33) & n_chars];
  CommandList33 char_evts33[(data_ver gte 33) & n_chars];
  CommandList00 item_evts00[(data_ver lt  33) & (n_items-1)];
  CommandList33 item_evts33[(data_ver gte 33) & (n_items-1)];
  uint32_cond_or_0 n_g_vars[data_ver lt 33];
  uint8 g_vars[n_g_vars][28];
  uint32_cond_or_0 n_words[f_dict eq 1];
  Word dict[n_words];
  Script g_scripts[((data_ver gte 38) & 1) + 1];
  uint32_cond_or_0 n_scripts[data_ver gte 31];
  Script scripts[n_scripts];
  View00 views00[(data_ver lt  33) & n_views];
  View33 views38[(data_ver gte 33) & n_views];
  uint8 unknown[(data_ver lt 20) & 0x204];
  Character chars[n_chars];
  uint32_uint8s lipsyncframes[(data_ver gte 20) & 50];
  cstr g_msgs00[(data_ver lt 26) andsumright f_g_msgs];
  encrypted g_msgs26[(data_ver gte 26) andsumright f_g_msgs];
  Dialog dlgs[n_dlgs];
  Dialog00 dlg_scripts[(data_ver lt 38) & n_dlgs];
  uint32 CAFEBEEF;
  uint32 gui_verct0;
  uint32_cond_or_0 gui_verct1[gui_verct0 gte 100];
//#define gui_ver gui_verct0 gte 100 & guiverct0
//#define n_guis gui_verct0 lt 100 & gui_verct0 | gui_verct1
};
'''
cstructs.load(cdef, compiled=False)
class DataFile:
    @classmethod
    def from_stream(cls, stream):
        #import pdb; pdb.set_trace()
        datafile = cstructs.DataFile(stream)
        return datafile

if __name__ == '__main__':
    with open('ags-camdemo/build/files/game28.dta','rb') as f:
        datafile = DataFile.from_stream(f)
        print(datafile)

