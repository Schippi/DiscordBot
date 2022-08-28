from concurrent.futures import ThreadPoolExecutor

import aiohttp
import asyncio
from threading import Thread
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import numpy as np
import json
import sys

from PySide6.QtWidgets import QLabel, QVBoxLayout

from keyboard import char_dict, repl_text, specials
import traceback
import re


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
        self.effect_dict = {

        }

    async def cancel_effect(self):
        self.show_effect = False
        for _ in range(10):
            if self.current_effect is None:
                return True
            await asyncio.sleep(0.1)
        return False

    async def disconnect(self):
        self.effect_dict = {}
        if self.custom_url:
            base_url = '%s:%s/razer/chromasdk' % (self.custom_url, self.custom_port)
            async with aiohttp.ClientSession() as session:
                async with session.delete(base_url, params=self.remote_local_port) as resp:
                    print(await resp.json())
        elif self.uri:
            async with aiohttp.ClientSession() as session:
                async with session.delete(self.uri, params=self.remote_local_port) as resp:
                    print(await resp.json())

    async def connect(self):
        for port in [54235, 54236]:
            if self.custom_url:
                base_url = '%s:%s/razer/chromasdk' % (self.custom_url, self.custom_port)
                print(base_url)
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(base_url, json=self.app_dict) as resp:
                            json_resp = await resp.json()
                            print(json_resp)
                            self.remote_local_port = {'port': json_resp['uri'].split(':')[-1].split('/')[0]}
                            self.uri = '%s:%s/chromasdk' % (self.custom_url, self.custom_port)
                            break
                except Exception as e:
                    self.session_id = None
                    print("Failed to connect to custom port %s" % self.custom_port)
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
        print("Connected to %s" % self.uri)
        return self.uri

    async def blink_letter(self,x,y):
        async with aiohttp.ClientSession() as session:
            arr = [[0] * 22 for _ in range(6)]
            arr[x][y] = 255
            effect_json = {
                "effect": "CHROMA_CUSTOM",
                "param": arr
            }
            async with session.post(self.uri + '/keyboard', params=self.remote_local_port, json=effect_json) as resp:
                resp_data = await resp.json()
                effect_id = resp_data['id'];
                await self.send_effect(effect_id, session)

    async def init_letters(self, color=33554431, letter = None):
        all_effects = {'effects': []}
        txt = 'abcdefghijklmnopqrstuvwxyz/'
        for i, t in enumerate(txt):
            if (t, color) in self.effect_dict:
                continue
            arr = [[0] * 22 for _ in range(6)]
            effect_json = {
                "effect": "CHROMA_CUSTOM",
                "param": arr
            }
            x, y = char_dict[t]
            arr[x][y] = color
            all_effects['effects'].append(effect_json)
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.uri + '/keyboard', params=self.remote_local_port, json=all_effects) as resp:
                    resp_data = await resp.json()
                    results = resp_data['results']
                    for idx, result in enumerate(results):
                        character = txt[idx]
                        self.effect_dict[(character, color)] = result['id']
                    print(str(zip(txt, results)))
            except Exception as e:
                print("error generating keyboard effect for text")
                print('%s: %s' % (t, all_effects))
                traceback.print_exc()
        if letter is not None:
            await self.show_letter(letter, color)

    async def show_letter(self, letter, color=33554431):
        async with aiohttp.ClientSession() as session:
            await self.send_effect(self.effect_dict[(letter, color)], session)


    async def show_text(self, txt, speed=20, color=33554431):
        self.show_effect = True
        if type(color) == tuple:
            color = rgb_to_bgr_int(color)
        txt = repl_text(txt)
        all_effects = {'effects': []}

        looked_up_text = ''
        for i, t in enumerate(txt):

            if (t, color) in self.effect_dict:
                continue
            looked_up_text += t
            arr = [[0] * 22 for _ in range(6)]

            if t in specials:
                for (x, y) in specials[t][0]:
                    arr[x][y] = rgb_to_bgr_int(specials[t][1])  # red
            elif t in char_dict:
                x, y = char_dict[t]
                arr[x][y] = color
            else:
                print('char not found:', t)
                continue

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
            all_effects['effects'].append(effect_json)
        async with aiohttp.ClientSession() as session:
            clear_effect_id = await self.get_clear_effect(session)
            async with session.post(self.uri + '/keyboard', params=self.remote_local_port, json=all_effects) as resp:
                resp_data = await resp.json()

                try:
                    results = resp_data['results']
                    for idx, result in enumerate(results):
                        character = looked_up_text[idx]
                        self.effect_dict[(character, color)] = result['id']
                    print(zip(looked_up_text, results))

                except Exception as e:
                    print("error generating keyboard effect for text")
                    print('%s: %s' % (t, all_effects))
                    traceback.print_exc()

            for idx, t in enumerate(txt):
                print('%s %s %s' % (idx, txt[:idx], self.effect_dict[(t, color)]))
                for _ in range(1):
                    await self.send_effect(clear_effect_id, session)
                    await asyncio.sleep(1.0 / speed)
                    await self.send_effect(self.effect_dict[(t, color)], session)
                    await asyncio.sleep(1.0 / speed)
            self.current_effect = None

    async def get_effect(self, session, effect, json):
        if effect in self.effect_dict:
            return self.effect_dict[effect]
        else:
            async with session.post(self.uri + '/keyboard', params=self.remote_local_port, json=json) as resp:
                resp_data = await resp.json()
                self.effect_dict[effect] = resp_data['id']
                return resp_data['id']

    async def get_clear_effect(self, session):
        clear_effect_json = {
            "effect": "CHROMA_STATIC",
            "param":
                {
                    "color": 1
                }
        }
        return await self.get_effect(session, 'clear', clear_effect_json)

    async def send_effect(self, clear_effect_id, session):
        async with await session.put(self.uri + '/effect', params=self.remote_local_port, json={"id": str(clear_effect_id)}) as resp:
            data = await resp.json()
            if 'result' not in data or data['result'] != 0:
                print('error sending effect: %s' % data)

    async def flash(self, color=None, speed=5.0):
        async with aiohttp.ClientSession() as session:
            static_effect = {
                "effect": "CHROMA_STATIC",
                "param":
                    {
                        "color": 255
                    }
            }
            effects = [(await self.get_effect(session, 'flash', static_effect)), (await self.get_clear_effect(session))]

            for _ in range(3):
                for effect_id in effects:
                    await self.send_effect(effect_id, session)
                    await asyncio.sleep(1.0 / speed)

    async def show_image(self, img, speed=20, repeat=1, reverse=False):
        self.show_effect = True
        self.current_effect = 'show_image'
        slices = horizontal_slices(img)
        effect_ids = []
        all_effects = {'effects': []}

        if reverse:
            slices = reversed(slices)
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
            all_effects['effects'].append(effect_json)
            #print(json.dumps(effect_json))

        async with aiohttp.ClientSession() as session:
            async with session.post(self.uri + '/keyboard', params=self.remote_local_port, json=all_effects) as resp:
                response = await resp.json()
                try:
                    effect_ids = [result['id'] for result in response['results']]
                except Exception as e:
                    print("error generating keyboard effect for image")
                    traceback.print_exc()
            for _ in range(repeat):
                if not self.show_effect:
                    break
                for idx, effect_id in enumerate(effect_ids):
                    await self.send_effect(effect_id, session)
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
                        if resp.status != 200:
                            print(resp.json())
            except:
                self.uri = None
                print("Heartbeat except")
        # if not self.uri:
        #     print("Heartbeat fail")
        #     uri = self.connect()
        #     if not uri:
        #         print("No connection")
        #         exit(1)


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
    await asyncio.sleep(1.0)
    while True:
        print('heartbeat')
        await asyncio.sleep(1.0)
        await keyboard.heartbeat()
        if not keyboard.uri:
            return


async def move_around(keyboard: ChromaImpl):
    x = 2
    y = 2
    while True:
        await keyboard.blink_letter(x, y)
        inp = await ainput('next: ')
        if inp == 's':
            x = x + 1
        if inp == 'w':
            x = x - 1
        if inp == 'a':
            y = y - 1
        if inp == 'd':
            y = y + 1
        if inp == 'p':
            print('x: ' + str(x) + ' y: ' + str(y))
        if inp == 'q':
            break
    await keyboard.disconnect()

async def main(keyboard: ChromaImpl):
    # await show_text_as_img([("Razer Chroma", "red")],10)
    print('and now text')
    # input()
    await keyboard.connect()
    # await keyboard.show_text(" ccc", 2, color=(255, 255, 0))
    #Image.open('../mng.png').show()
    await keyboard.show_text(":)", 0.2, color=(255, 255, 0))
    #await keyboard.show_image(Image.open('../mng2.png').convert('RGB'), speed=10, repeat=4)
    await keyboard.show_image(Image.open('../mng2.png').convert('RGB'), speed=0.2, repeat=1)

    await move_around(keyboard)
    # await show_text("qwertz",2)

    # await keyboard.show_text_as_img([("Razer Chroma", "red"), ("REST", "green")],4)
    await keyboard.disconnect()
    pass

async def ainput(prompt: str = ''):
    with ThreadPoolExecutor(1, 'ainput') as executor:
        return (await asyncio.get_event_loop().run_in_executor(executor, input, prompt)).rstrip()

async def m(keyboard: ChromaImpl):
    await asyncio.gather(main(keyboard)
                         , heartbeat_loop(keyboard)
                         )

curchar = '?'
score = 0
hits = 0
misses = 0

async def letterloop(keyboard):
    #await keyboard.connect()
    #await keyboard.init_letters()

    from datetime import datetime
    from datetime import timedelta
    import random
    global curchar
    nextchar = '?'
    curchar = '?'
    global score
    score = 0
    now = datetime.now()
    finish = now + timedelta(seconds=60)
    while now < finish:
        now = datetime.now()
        sl = max((30+(score+3)*8)/((score+3)**2+40), 0.3)
        print(sl)
        await asyncio.sleep(sl)
        while nextchar == curchar:
            nextchar = random.choice(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']).lower()
        curchar = nextchar
        #print(curchar)
        await keyboard.show_letter(curchar)
    await keyboard.flash()
    await keyboard.show_letter('/')
    curchar = '?'


class AsyncLoopThread(Thread):
    def __init__(self):
        super().__init__(daemon=False)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

def whackamole():
    from PySide6.QtWidgets import QLineEdit
    from PySide6 import QtCore
    from PySide6 import QtWidgets
    import time
    class Example(QtWidgets.QWidget):
        def closeEvent(self, event):
            asyncio.run_coroutine_threadsafe(self.keyboard.disconnect(), self.yourthread)
            event.accept()
        def eventFilter(self, sourceObj, event):
            global curchar
            global score
            global hits
            global misses
            if event.type() == QtCore.QEvent.KeyPress:
                c = event.text()[:1].lower()
                if c == curchar:
                    score += 1
                    hits += 1
                    #print(score)
                    curchar = '_'
                elif c == '*':
                    asyncio.run_coroutine_threadsafe(self.keyboard.disconnect(), self.yourthread)
                    self.close()
                elif c == '/':
                    if curchar == '?':
                        score = 0
                        asyncio.run_coroutine_threadsafe(letterloop(self.keyboard), self.yourthread)
                    else:
                        print('already started')
                else:
                    misses += 1
                    score -= 1
                    #print('missed'+ str(curchar) + ' ' + event.text()[:1])
                self.label1.setText("<font color=red>score: %d</font>" % score)
                self.label2.setText("<font color=black>hits: %d misses: %d</font>" % (hits, misses))

            return QtWidgets.QWidget.eventFilter(self, sourceObj, event)
    print('qt')
    loop_handler = AsyncLoopThread()
    loop_handler.start()
    keyboard = ChromaImpl()
    asyncio.get_event_loop().run_until_complete(keyboard.connect())
    asyncio.get_event_loop().run_until_complete(keyboard.init_letters())
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(1.0))
    asyncio.get_event_loop().run_until_complete(keyboard.show_letter('/'))
    asyncio.run_coroutine_threadsafe(heartbeat_loop(keyboard), loop_handler.loop)

    app = QtWidgets.QApplication([])
    widget = Example()
    widget.setWindowTitle('WhackAMole')
    widget.yourthread = loop_handler.loop
    widget.keyboard = keyboard

    widget.label0 = QLabel(widget)
    widget.label0.setAlignment(QtCore.Qt.AlignCenter)
    widget.label0.setText("<font color=black>start with /</font>")

    widget.label1 = QLabel(widget)
    widget.label1.setAlignment(QtCore.Qt.AlignCenter)
    widget.label1.setText("<font color=red>score: 0</font>")

    widget.label2 = QLabel(widget)
    widget.label2.setAlignment(QtCore.Qt.AlignCenter)
    widget.label2.setText("<font color=black>hits: 0 misses: 0</font>")

    widget.textbox = QLineEdit(widget)
    widget.textbox.resize(700, 30)
    widget.textbox.installEventFilter(widget)

    vbox = QVBoxLayout()

    vbox.addWidget(widget.label0)
    vbox.addWidget(widget.label1)
    vbox.addWidget(widget.label2)
    vbox.addWidget(widget.textbox)
    widget.setLayout(vbox)
    widget.resize(800, 100)
    widget.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    keyboard = ChromaImpl()

    whackamole()
    #asyncio.run(whackamole(keyboard))

    #asyncio.run_coroutine_threadsafe(letterloop(keyboard), loop_handler.loop)


    #  loop = asyncio.get_event_loop()
    #   loop.run_until_complete(main())
    #    loop.run_until_complete(heartbeat()

    try:
        asyncio.run(m(keyboard))
    except KeyboardInterrupt:
        print("Exiting")
        asyncio.run(keyboard.disconnect())
    #asyncio.get_event_loop.run_until_complete(setuphttp().start())

