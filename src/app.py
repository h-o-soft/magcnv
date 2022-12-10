import sys
import argparse
import glob
from io import StringIO
from PIL import Image, ImageFilter
import codecs
import os

class MAGImage:
    image = Image.Image

    copyx = [0, 1, 2, 4, 0, 1, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0]
    copyy = [0, 0, 0, 0, 1, 1, 2, 2, 2, 4, 4, 4, 8, 8, 8, 16]
    check_order = [1,4,5,6,7,9,10,2,8,11,12,13,14,3,15]

    def loadImage(self, filepath):
        self.image = Image.open(filepath).convert('RGB')

    def get_1pixel(x, y, step):
        return
    
    class MAGPixel:
        pixels = bytearray()
        colors = 16
        pixel_temp = 0
        pixel_index = 0

        def __init__(self, colors):
            self.colors = colors

        def clear(self):
            self.pixels = bytearray()
            self.pixel_temp = 0
            self.pixel_index = 0
        
        def append(self, col):
            if self.colors == 16:
                if (self.pixel_index & 1) == 0:
                    self.pixel_temp = col << 4
                else:
                    self.pixel_temp = self.pixel_temp | col
                    self.pixels.append(self.pixel_temp)
                    self.pixel_temp = 0
                self.pixel_index = self.pixel_index + 1
            else:
                self.pixels.append(col)

    class MAGFlag:
        flag = bytearray()
        flag_index = 0
        flag_temp = 0
        flag_a = bytearray()
        flag_b = bytearray()
        compressed = False

        def compress(self, width):
            if self.compressed:
                return

            # フラグの書き漏らしがある場合は書いておく
            if (self.flag_index & 1) == 1:
                self.flag.append(self.flag_temp)
                self.flag_index = self.flag_index + 1

            # 1ライン上からxorを取る
            flag_height = len(self.flag) // width * 2
            flag_width  = width // 2

            for y in range(flag_height-1, 0, -1):
                for x in range(flag_width):
                    prev_ofs = x + (y - 1) * flag_width
                    ofs = x + y * flag_width
                    self.flag[ofs] = self.flag[ofs] ^ self.flag[prev_ofs]

            # flag_aとflag_bを作る
            self.flag_a.clear()
            self.flag_b.clear()

            val_a = 0
            val_a_idx = 0
            for i in range(len(self.flag)):
                if self.flag[i] != 0:
                    # 上位ビットから埋めていく
                    val_a = val_a | (1 << (7 - val_a_idx))
                    self.flag_b.append(self.flag[i])
                val_a_idx = val_a_idx + 1
                if val_a_idx == 8:
                    self.flag_a.append(val_a)
                    val_a = 0
                    val_a_idx = 0

            if val_a_idx != 0:
                self.flag_a.append(val_a)
            
            self.compressed = True


        def clear(self):
            self.flag = bytearray()
            self.flag_index = 0
            self.flag_temp = 0
            self.compressed = False
        
        def append(self, value):
            if (self.flag_index & 1) == 0:
                self.flag_temp = (value << 4) & 0xf0
            else:
                self.flag_temp = self.flag_temp | (value & 0xf)
                self.flag.append(self.flag_temp)
            self.flag_index = self.flag_index + 1

    # force digital 8 colors
    def saveMAG(self, filepath, colors = 16):
        pixel_step = 4 if colors ==16 else 2
        flag_buff = MAGImage.MAGFlag()
        pixel_buff = MAGImage.MAGPixel(colors)

        width  = self.image.width // pixel_step
        height = self.image.height

        for y in range(height):
            for x in range(width):
                # 同一ピクセルがあるか調べる
                is_same = False
                for idx in self.check_order:
                    cx = x * pixel_step - self.copyx[idx] * pixel_step
                    cy = y - self.copyy[idx]
                    if cx < 0 or cy < 0:
                        continue
                    # pixel_stepドットぶんが一致するか調べる
                    is_same = True
                    for pidx in range(pixel_step):
                        chkcol = self.image.getpixel((cx + pidx, cy))
                        curcol = self.image.getpixel((x * pixel_step + pidx, y))
                        if chkcol != curcol:
                            is_same = False
                            break
                    if is_same:
                        flag_buff.append(idx)
                        break;
                    is_same = False

                if not is_same:
                    # 一致しなかったのでフラグに0を書き、ピクセル情報も書く
                    flag_buff.append(0)
                    for pidx in range(pixel_step):
                        curcol = self.image.getpixel((x * pixel_step + pidx, y))
                        r = 1 if curcol[0] > 127 else 0
                        g = 1 if curcol[1] > 127 else 0
                        b = 1 if curcol[2] > 127 else 0
                        pixel_bit = (g << 2) | (r << 1) | b
                        pixel_buff.append(pixel_bit)
        
        # ここまでで情報が揃っている
        flag_buff.compress(width)

        # デジタル8色で出力する(固定)
        f = open(filepath, 'wb')
        f.write('MAKI02  '.encode())
        f.write('PYTN '.encode())
        f.write('>??<               '.encode())

        f.seek(32, os.SEEK_SET)
        f.write('magcnv'.encode())
        f.write(bytes([0x1a]))

        # 7 = 200 line / 6 = 400 line
        f.write(bytes([0, 0, 0, 7]))
        start_x = 0
        start_y = 0
        end_x = width * pixel_step -1
        end_y = height-1
        f.write(start_x.to_bytes(2, 'little'))
        f.write(start_y.to_bytes(2, 'little'))
        f.write(end_x.to_bytes(2, 'little'))
        f.write(end_y.to_bytes(2, 'little'))

        flaga_offset = 32 + 48
        flagb_offset = flaga_offset + len(flag_buff.flag_a)
        flagb_size   = len(flag_buff.flag_b)
        pixel_offset = flagb_offset + flagb_size 
        pixel_size   = len(pixel_buff.pixels)

        f.write(flaga_offset.to_bytes(4, 'little'))
        f.write(flagb_offset.to_bytes(4, 'little'))
        f.write(flagb_size.to_bytes(4, 'little'))
        f.write(pixel_offset.to_bytes(4, 'little'))
        f.write(pixel_size.to_bytes(4, 'little'))

        # デジタル8色パレット(固定)
        # 24bytesを2回書く
        digital_pal = bytearray()
        for i in range(2):
            for idx in range(8):
                # G
                digital_pal.append(255 if (idx & 4) != 0 else 0 )
                # R
                digital_pal.append(255 if (idx & 2) != 0 else 0 )
                # B
                digital_pal.append(255 if (idx & 1) != 0 else 0 )

        f.write(digital_pal)

        f.write(flag_buff.flag_a)
        f.write(flag_buff.flag_b)
        f.write(pixel_buff.pixels)

        f.close()
        return

    def loadMAG(self, filepath):
        # load mag image
        f = open(filepath, 'rb')
        head = f.read(8).decode()
        if head != "MAKI02  ":
            raise Exception('mag format error')
        machine_name = f.read(5).decode()
        user_name = f.read(18).decode('Shift-JIS')
        f.seek(32, os.SEEK_SET)

        comment_byte = bytes()
        for ch in iter(lambda: f.read(1), ''):
            if ch[0] == 0x1a:
                break
            comment_byte += ch
        comment = codecs.decode(comment_byte, 'Shift-JIS')

        # header
        header_offset = f.tell()

        head_byte = f.read(1)[0]
        machine_code = f.read(1)[0]
        machine_flag = f.read(1)[0]
        screen_mode = f.read(1)[0]
        start_x = int.from_bytes(f.read(2),'little')
        start_y = int.from_bytes(f.read(2),'little')
        end_x = int.from_bytes(f.read(2),'little')
        end_y = int.from_bytes(f.read(2),'little')
        flaga_offset = int.from_bytes(f.read(4),'little')
        flagb_offset = int.from_bytes(f.read(4),'little')
        flaga_size = flagb_offset - flaga_offset
        flagb_size = int.from_bytes(f.read(4),'little')
        pixel_offset = int.from_bytes(f.read(4),'little')
        pixel_size = int.from_bytes(f.read(4),'little')
        colors = 256 if (screen_mode & 0x80) != 0 else 16
        pixel_unit_log = 1 if (screen_mode & 0x80) != 0 else 2

        # load palette
        f.seek(header_offset + 32, os.SEEK_SET)
        palette = f.read(colors * 3)
        f.seek(header_offset + flaga_offset, os.SEEK_SET)
        flaga_buf = f.read(flaga_size)
        f.seek(header_offset + flagb_offset, os.SEEK_SET)
        flagb_buf = f.read(flagb_size)

        width = ((end_x & 0xFFF8) | 7) - (start_x & 0xFFF8) + 1
        flag_size = width >> (pixel_unit_log + 1)
        height = end_y - start_y + 1
        flag_buf = bytearray(flag_size)

        f.seek(header_offset + pixel_offset, os.SEEK_SET)
        pixel = f.read(pixel_size);

        f.close()

        self.image = Image.new("RGB", (width, height), (0, 0, 0))
        im = self.image
        flaga_pos = 0;
        flagb_pos = 0;
        src = 0;
        mask = 0x80;
        for y in range(height):
            # フラグを1ライン分展開
            for x in range(flag_size):
                # フラグAを1ビット調べる
                if (flaga_buf[flaga_pos] & mask) != 0:
                    # 1ならフラグBから1バイト読んでXORを取る
                    flag_buf[x] = flag_buf[x] ^ flagb_buf[flagb_pos]
                    flagb_pos = flagb_pos + 1
                mask = mask >> 1
                if mask == 0:
                    mask = 0x80
                    flaga_pos = flaga_pos + 1
            for x in range(flag_size):
                # フラグを1つ調べる
                vv = flag_buf[x]
                v = (vv >> 4) & 0xff
                dest_x = x * 8 if colors == 16 else x * 4
                if v == 0:
                    # 0ならピクセルデータから1ピクセル(2バイト)読む
                    if (colors == 16):
                        c = (pixel[src] >> 4) * 3;
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                        c = (pixel[src] & 0xF) * 3;
                        src = src + 1
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                        c = (pixel[src] >> 4) * 3;
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                        c = (pixel[src] & 0xF) * 3;
                        src = src + 1
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                    else:
                        c = pixel[src] * 3;
                        src = src + 1
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                        c = pixel[src] * 3;
                        src = src + 1
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                else:
                    # 0以外なら指定位置から1ピクセル(16色なら4ドット/256色なら2ドット)コピー
                    px = dest_x - self.copyx[v] * pixel_unit_log * 2
                    py = y - self.copyy[v]
                    for j in range(pixel_unit_log * 2):
                        col = im.getpixel((px+j,py))
                        im.putpixel((dest_x+j, y), col )
                    dest_x = dest_x + pixel_unit_log * 2

                v = vv & 0xF
                if v == 0:
                    # 0ならピクセルデータから1ピクセル(2バイト)読む
                    if (colors == 16):
                        c = (pixel[src] >> 4) * 3;
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                        c = (pixel[src] & 0xF) * 3;
                        src = src + 1
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                        c = (pixel[src] >> 4) * 3;
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                        c = (pixel[src] & 0xF) * 3;
                        src = src + 1
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                    else:
                        c = pixel[src] * 3;
                        src = src + 1
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                        c = pixel[src] * 3;
                        src = src + 1
                        col = (palette[c+1], palette[c], palette[c+2])
                        im.putpixel((dest_x,y), col)
                        dest_x = dest_x + 1
                else:
                    # 0以外なら指定位置から1ピクセル(16色なら4ドット/256色なら2ドット)コピー
                    px = dest_x - self.copyx[v] * pixel_unit_log * 2
                    py = y - self.copyy[v]
                    for j in range(pixel_unit_log * 2):
                        col = im.getpixel((px+j,py))
                        im.putpixel((dest_x+j, y), col )
                    dest_x = dest_x + pixel_unit_log * 2
        return

class MAGConverter:
    paths = []
    image = MAGImage()
    force_write = False

    def __init__(self, paths):
        self.paths = paths

    def exec(self):
        if self.paths == None or len(self.paths) == 0:
            return True
        
        from_path = self.paths[0]
        from_ext = os.path.splitext(from_path)[1].lower()
        to_path = ''
        if len(self.paths) >= 2:
            to_path = self.paths[1]
        else:
            if from_ext == ".mag":
                to_path = os.path.splitext(from_path)[0] + '.png'
            else:
                to_path = os.path.splitext(from_path)[0] + '.mag'

        if os.path.exists(to_path) and not self.force_write:
            print("file already exists. " + to_path)
            return

        if from_ext == ".mag":
            self.image.loadMAG(from_path)
            self.image.image.save(to_path, format='png')
        else:
            self.image.loadImage(from_path)
            self.image.saveMAG(to_path)

        print("convert..." + from_path + " to " + to_path )

def main():
    parser = argparse.ArgumentParser(description='magcnv MAG image converter Version 0.1.0 Copyright 2022 H.O SOFT Inc.')

    parser.add_argument('-f', '--force', help='set force write ', action='store_true')
    parser.add_argument('path', help='file path(s)', nargs="*")

    args = parser.parse_args()

    paths = args.path

    magconv = MAGConverter(paths);
    magconv.force_write = args.force
    if magconv.exec():
        parser.print_help()
        exit()

if __name__=='__main__':
    main()
