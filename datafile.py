class DataFile:
    @classmethod
    def from_stream(cls, file):
        def bytes(len):
            return file.read(len)
        def uchar():
            return int.from_bytes(bytes(1), 'little', signed=False)
        def ushort():
            return int.from_bytes(bytes(2), 'little', signed=False)
        def sint():
            return int.from_bytes(bytes(4), 'little', signed=True)
        def uint():
            return int.from_bytes(bytes(4), 'little', signed=False)
        def bool():
            v = uchar()
            assert v & 1 == v
            return bool(v)
        def str(len=None):
            if len is None:
                len = uint()
            return bytes(len).decode().rstrip('\0')
        def cstr():
            # could maybe simplify by enforcing file is io.BufferedReader, maybe using TextWrapper or something
            data = b''
            str = ''
            while str[-1] != '\0':
                data += bytes(1)
                str = data.decode()
            return str[:-1]
        def vec(typ, params=[], kwparams={}, ct=None):
            if ct is None:
                ct = uint()
            return [typ(*params, **kwparams) for x in range(ct)]
        def decrypt(data):
            return bytes([
                (data[idx] + 0x100 - cls.PWD[idx % len(cls.PWD)]) & 0xff
            ]).decode()
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
        def name_off():
            return [cstr(), uint()]
        def scom():
            assert str(4) == 'SCOM'
            ver = uint()
            g_datasize = uint()
            codesize = uint()
            strsize = uint()
            g_data = bytes(g_datasize)
            code = bytes(codesize)
            strs = bytes(strsize)
            n_fixups = uint()
            fixup_types = vec(uchar, ct=n_fixups)
            fixups = vec(uint, ct=n_fixups)
            imports = vec(cstr)
            exports = vec(name_off)
            sections = vec(name_off) if ver >= 83 else []
            assert uint() == 0xbeefcafe
            return [ver, g_data, code, strs, fixup_types, fixups, imports, exports, sections]

        assert len(cls.SIG) == 30
        file_sig = str(30)
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
        palette = vec(vec, [uint], {'ct':4}, ct=256)
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
        g_msg_mask = vec(bool, ct=500)
        n_g_msgs = sum(g_msg_mask)
        has_dict = bool()
        has_globalscript = bool()
        has_chars = bool()
        has_compiled_script = bool()
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
        assert not any(bytes(68))
        items = []
        for idx in range(n_items):
            descr = str(24)
            assert uint() == 0
            image = uint()
            cursor = uint()
            hotspot_x = uint()
            hotspot_y = uint()
            assert not any(bytes(5*4))
            startwith = bool()
            assert not any(bytes(3))
            items.append([descr, image, cursor, hotspot_x, hotspot_y])
        cursors = []
        for idx in range(n_cursors):
            image = uint()
            hotspot_x = ushort()
            hotspot_y = ushort()
            anim = ushort()
            name = str(9)
            assert uchar() == 0
            flags = uchar()
            assert bytes(3) == 0
            cursor.append([image, hotspot_x, hotspot_y, anim, name, flags])
        _n_funcnames = uint()
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
            words = []
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
                        sound = uint()
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
            blink_view, blink_interval, blink_timer, blink_frane, walkspeed_y, pic_yoffs = vec(ushort, 6)
            z, walk_wait = uint(), uint()
            talk_speed, idle_speed = ushort(), ushort()
            blocking_width, blocking_height = ushort(), ushort()
            idx_id = uint()
            pic_xoffs, walkwaitcounter, loop, frame = vec(ushort, ct=4)
            walking, animating, walkspeed, animspeed = vec(ushort, ct=4)
            items = vec(ushort, 301)
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
    
        for idx in range(len(g_msgs)):
            if g_msgs[idx]:
                if data_version < 26:
                    g_msgs[idx] = cstr()
                else:
                    g_msgs[idx] = decrypt(bytes())
            else:
                g_msgs[idx] = None

        assert not "dialog topics and further content"

            
    SIG = "Adventure Creator Game File v2"
    PWD = "Avis Durgan"

if __name__ == '__main__':
    with open('ags-camdemo/build/files/game28.dta','rb') as f:
        DataFile.from_stream(f)
