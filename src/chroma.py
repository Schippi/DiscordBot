import aiohttp
import asyncio
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import numpy as np
import json
import sys
from keyboard import char_dict
import traceback


class ChromaImpl:
    def __init__(self, app_dict={
        "title": "Razer Chroma",
        "description": "This is a REST",
        "author": {
            "name": "Chroma Developer",
            "contact": "www.razerzone.com"
        },
        "device_supported": [
            "keyboard"
        ],
        "category": "application"
    }
                 , custom_url=None
                 , custom_port=None):

        self.app_dict = app_dict
        self.session_id = None
        self.show_effect = False
        self.uri = None
        self.current_effect = None
        self.custom_url = custom_url
        self.custom_port = custom_port
        self.remote_local_port = {}


    async def cancel_effect(self):
        self.show_effect = False
        for _ in range(10):
            if self.current_effect is None:
                return True
            await asyncio.sleep(0.1)
        return False

    async def disconnect(self):
        if self.uri:
            async with aiohttp.ClientSession() as session:
                async with session.delete(self.uri) as resp:
                    print(await resp.json())

    async def connect(self):
        for port in [54235, 54236]:
            if self.custom_url:
                base_url = '%s:%s/razer/chromasdk' % (self.custom_url, self.custom_port)
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(base_url, json=self.app_dict) as resp:
                            json_resp = await resp.json()
                            print(json_resp)
                            self.remote_local_port = {'port' : json_resp['uri'].split(':')[-1]}
                            self.uri = '%s:%s' % (self.custom_url, self.custom_port)
                            break
                except Exception as e:
                    self.session_id = None
                    print("Failed to connect to custom port %d" % self.custom_port)
                    traceback.print_exc()
                    pass
                return
            else:
                base_url = 'http://localhost:%d/razer/chromasdk' % port
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(base_url, json=self.app_dict) as resp:
                            self.uri = (await resp.json())['uri']
                            break
                except Exception as e:
                    self.session_id = None
                    print("Failed to connect to port %d" % port)
                    traceback.print_exc()
                    pass
        return self.uri

    async def show_text(self, txt, speed=20, color=33554431):
        self.show_effect = True
        if type(color) == tuple:
            color = rgb_to_bgr_int(color)
        clear_arr = [[0] * 22 for _ in range(6)]
        # clear_effect_json = {
        #     "effect": "CHROMA_CUSTOM_KEY",
        #     "param": {
        #             "color": clear_arr,
        #             "key": clear_arr
        #         }
        # }
        clear_effect_json = {
            "effect": "CHROMA_CUSTOM",
            "param": clear_arr
        }
        effect_ids = []
        async with aiohttp.ClientSession() as session:
            async with session.post(self.uri + '/keyboard', params=self.remote_local_port, json=clear_effect_json) as resp:
                cnt = await resp.json()
                try:
                    effect_ids.append(cnt['id'])
                except Exception as e:
                    print("error clearing keyboard")
                    traceback.print_exc()
            prev = ''
            for i, t in enumerate(txt):
                if t in char_dict:
                    x, y = char_dict[t]
                else:
                    print('char not found:', t)
                    continue
                arr = [[0] * 22 for _ in range(6)]
                arr[x][y] = color

                # color_arr = [[0] * 22 for _ in range(6)]
                # color_arr[x][y] = 0xff0000
                # effect_json = {
                #     "effect": "CHROMA_CUSTOM_KEY",
                #     "param":
                #         {
                #             "color": color_arr,
                #             "key": arr
                #         }
                # }

                effect_json = {
                    "effect": "CHROMA_CUSTOM",
                    "param": arr
                }

                async with session.post(self.uri + '/keyboard', params=self.remote_local_port, json=effect_json) as resp:
                    cnt = await resp.json()
                    try:
                        effect_ids.append(cnt['id'])
                    except e as e:
                        print("error generating keyboard effect for letter")
                        print('%s: %s' % (t, effect_json))
                        traceback.print_exc()

            for idx, effect_id in enumerate(effect_ids):
                print('%s %s %s' % (idx, txt[:idx], effect_id))
                for _ in range(1):
                    async with await session.put(self.uri + '/effect', params=self.remote_local_port, json={"id": str(effect_id)}) as resp:
                        print(await resp.json())
                    await asyncio.sleep(1.0 / speed)
                    async with await session.put(self.uri + '/effect', params=self.remote_local_port, json={"id": str(effect_ids[0])}) as resp:
                        print(await resp.json())
                    await asyncio.sleep(1.0 / speed)
            self.current_effect = None

    async def show_image(self, img, speed=20, repeat=1, reverse=False):
        self.show_effect = True
        self.current_effect = 'show_image'
        slices = horizontal_slices(img)
        effect_ids = []
        async with aiohttp.ClientSession() as session:
            for i, img in enumerate(slices):
                # s.save("./debug/%s.bmp"%i)
                # self.set_static_image(build_img(s))
                # time.sleep(1.0/speed)
                arr = np.array(img)
                print('%s %s ' % (len(arr), len(arr[0])))
                print(arr)
                arr2 = []
                for ii, y in enumerate(arr):
                    arr3 = []
                    for jj, x in enumerate(y):

                        arr3.append(int(arr[ii][jj][0] + arr[ii][jj][1] * 256 + arr[ii][jj][2] * 65536))
                    arr2.append(arr3)
                effect_json = {
                    "effect": "CHROMA_CUSTOM",
                    "param":
                        arr2
                }
                print(json.dumps(effect_json))
                async with session.post(self.uri + '/keyboard', params=self.remote_local_port, json=effect_json) as resp:
                    cnt = await resp.json()
                    try:
                        effect_ids.append(cnt['id'])
                    except Exception as e:
                        print("error generating keyboard effect for image")
                        traceback.print_exc()
            if reverse:
                effect_ids.reverse()
            for _ in range(repeat):
                if not self.show_effect:
                    break
                for idx, effect_id in enumerate(effect_ids):
                    async with await session.put(self.uri + '/effect', params=self.remote_local_port, json={"id": str(effect_id)}) as resp:
                        print(await resp.json())
                    await asyncio.sleep(1.0 / speed)
                    if not self.show_effect:
                        break
        self.current_effect = None

    async def show_text_as_img(self, txt, speed=20, font=None):
        if (type(txt) is not list) or (len(txt) == 0) or (type(txt[0]) is not tuple):
            raise Exception("a list of tuple is expected")
        im = draw_multiple_to_image(txt, font)
        # im.show()
        self.show_image(im)

    async def heartbeat(self):
        if self.uri:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.put(self.uri, params=self.remote_local_port) as resp:
                        print(resp.status)
            except:
                self.uri = None
                print("Heartbeat except")
        if not self.uri:
            print("Heartbeat fail")
            uri = self.init_connection()
            if not uri:
                print("No connection")
                exit(1)


def rgb_to_bgr_int(rgb):
    return (0xff << 24) | (rgb[2] << 16) | (rgb[1] << 8) | rgb[0]


def create_default_image(size=(22, 6)):
    im = Image.new("RGB", size)
    return im


def draw_text_to_image(text, color="red", size=(0, 22), empty_start=True, empty_end=True, font=None):
    '''Draws the string in given color to an image and returns this image'''
    if not font:
        import os
        fn = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'fonts/5 9x9 Strict Sans.ttf'), 10)
    else:
        fn = font
    draw_txt = ImageDraw.Draw(create_default_image())
    width, height = draw_txt.textsize(text, font=fn)
    del draw_txt
    if empty_start:
        width += size[1]
    if empty_end:
        width += size[1]
    im = create_default_image((width, size[1]))
    draw = ImageDraw.Draw(im)
    if empty_start:
        offset_x = size[1]
    else:
        offset_x = 0
    draw.text((offset_x, 0), text.upper(), font=fn, fill=color)
    del draw
    return im


def concatenate(image1, image2, way=1):
    '''Concatenates the sencond image to the first'''

    width = image1.width + image2.width
    height = max(image1.height, image2.height)
    result_img = create_default_image((width, 6))
    result_img.paste(image1, (0, 0))
    result_img.paste(image2, (image1.width, 0))
    return result_img


def draw_multiple_to_image(texts, font=None):
    img_result = Image.new("RGB", (0, 0))
    empty_start = True
    for txt, color in texts:
        im = draw_text_to_image(txt, color, empty_start=empty_start, empty_end=False, font=font)
        empty_start = False
        img_result = concatenate(img_result, im)
    img_result = concatenate(img_result, create_default_image((22, 6)))
    return img_result


def horizontal_slices(image, slice_size=22):
    '''Create 10x10 images from a bigger image e.g. 10x40.'''
    width, height = image.size
    way = 1
    slices = 1
    if (way == 1) or (way == 3):
        slices = width - slice_size

    result_images = []

    for slice in range(slices):
        new_box = (slice, 0, slice + slice_size, height)
        new_img = image.crop(new_box)
        result_images.append(new_img)
        # new_img.show()
    return result_images


async def heartbeat_loop(keyboard: ChromaImpl):
    while True:
        await asyncio.sleep(1.0)
        await keyboard.heartbeat()


async def main(keyboard: ChromaImpl):
    # await show_text_as_img([("Razer Chroma", "red")],10)
    print('and now text')
    # input()
    await keyboard.connect()
    # await keyboard.show_text(" ccc", 2, color=(255, 255, 0))
    Image.open('../gradient2.png').show()
    await keyboard.show_text(" welcome", 5, color=(255, 255, 0))
    await keyboard.show_image(Image.open('../gradient2.png').convert('RGB'), speed=10, repeat=4, reverse=True)
    # await show_text("qwertz",2)

    # await keyboard.show_text_as_img([("Razer Chroma", "red"), ("REST", "green")],4)
    pass


async def m(keyboard: ChromaImpl):
    await asyncio.gather(main(keyboard), heartbeat_loop(keyboard))

if __name__ == "__main__":
    #  loop = asyncio.get_event_loop()
    #   loop.run_until_complete(main())
    #    loop.run_until_complete(heartbeat()
    keyboard = ChromaImpl()
    try:
        asyncio.run(m(keyboard))
    except KeyboardInterrupt:
        print("Exiting")
        asyncio.run(keyboard.disconnect())
    #asyncio.get_event_loop.run_until_complete(setuphttp().start())

