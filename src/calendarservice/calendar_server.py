import json
import random

from aiohttp import web
import aiohttp
import asyncio
import sys
import time
import os.path
import os
import datetime
import imagehash
import re
import platform

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
import requests
from io import BytesIO
from PIL import Image, UnidentifiedImageError, ImageOps
import matplotlib.pyplot as plt
import cairosvg
import traceback


calendarroutes = web.RouteTableDef()
call_cnt = 0
sys.path.append('..')
import util

cached_events = (None, None)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
API_KEY_SEARCH=util.SEARCH_API_KEY  # from util
CX_ENGINE=util.SEARCH_CX_ENGINE  # from util

def current_milli_time():
    return round(time.time() * 1000)

def isTestingCal():
    testing = False
    try:
        fil = open(util.cfgPath + '/testing.cfg', 'r')
        testing = True
        fil.close()
    except Exception:
        pass
    return testing

async def fetch_async(link, timeout=10, params=None):
    headers = {
        "User-Agent": "MyBandLogoFetcher/1.0 (theschippi@gmail.com)"
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.get(link, headers=headers, params=params) as resp:
            if resp.status < 200 or resp.status >= 300:
                try:
                    txt = await resp.text()
                    raise Exception(f"HTTP error {resp.status} for {link}: {txt}")
                except Exception:
                    raise Exception(f"HTTP error {resp.status} for {link}")
            resp.raise_for_status()
            ct = resp.headers.get("Content-Type", "").lower()
            if "json" in ct:
                data = await resp.json()
                return data, ct
            elif "text" in ct:
                data = await resp.text()
                return data, ct
            elif 'image/svg+xml' in ct:
                txt = await resp.text()
                png_bytes = cairosvg.svg2png(bytestring=txt.encode("utf-8"))
                #img = Image.open(BytesIO(png_bytes))
                #img.load()
                #img.save("D:/_TMP/Tloftr-logo.png")
                return BytesIO(png_bytes), ct
            else:
                data = await resp.read()
                return BytesIO(data), ct



async def start_site(app: web.Application, theConfig: dict):
    host = theConfig['host']
    port = theConfig['port']
    app.add_routes(calendarroutes)
    runner = web.AppRunner(app)
    root_folder = os.path.dirname(sys.argv[0])


    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()


@calendarroutes.get('/cal/acc')
async def cal_acc(request):
    return web.Response(text="ok")


def atkinson_dither(gray: Image.Image, threshold: int = 128, invert_if_dark: bool = True) -> Image.Image:

    pixels = gray.load()
    w, h = gray.size

    for y in range(h):
        for x in range(w):
            old_pixel = pixels[x, y]
            new_pixel = 255 if old_pixel > threshold else 0
            quant_error = old_pixel - new_pixel
            pixels[x, y] = new_pixel

            # Distribute error (Atkinson kernel)
            for dx, dy in [(1,0),(2,0),(-1,1),(0,1),(1,1),(0,2)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    pixels[nx, ny] = min(255, max(0, pixels[nx, ny] + quant_error // 8))

    # Convert to 1-bit
    bw = gray.point(lambda p: 255 if p > threshold else 0, mode="1")

    return bw
@calendarroutes.get('/cal/test')
async def cal_test(request):
    if not isTestingCal():
        return web.Response(text="nope")
    data,_ = await fetch_async("https://image.jimcdn.com/app/cms/image/transf/dimension=774x10000:format=png/path/s7bca863384a120f8/image/i1ad430d069febb44/version/1762202550/image.png")
    img = Image.open(data)
    img = img.resize((390,220), Image.NEAREST)\
        .convert("RGBA")\
        .convert("L")
    #img.save("D:/_TMP/fut_l.png")
    fbw = img.convert("1")
    #fbw.save("D:/_TMP/fut_bw.png")
    atkinson_dithered = atkinson_dither(img.copy(), threshold=40, invert_if_dark=False)
    #atkinson_dithered.save(f"D:/_TMP/fut_atkinson_wb_{j}.png")

    rect_img = drawrectimage(generateImage(path=None, source=fbw))
    #rect_img.save("D:/_TMP/fut_rects.png")
    for txt in ["Herr der Ringe Couch Marathon", "Brettspiele", "Stromberg   Wieder alles wie immer", "Zusammen unterwegs   ", "Essen mit Marc"]:
        rects = generateImage(path=None, source=replacementImage(txt))
        print(f" {txt} amount of rects",len(rects))
        rect_img = drawrectimage(generateImage(path=None, source=replacementImage(txt)))
        rect_img.save(f"D:/_TMP/{txt}_replacement_x.png")

    return web.Response(text="ok")

def drawrectimage(data):
    from PIL import Image, ImageDraw
    SIZE = (390, 220)
    img = Image.new('1', SIZE, 1)  # white background
    draw = ImageDraw.Draw(img)

    for rect in data:
        x = rect['x']
        y = rect['y']
        w = rect['w']
        h = rect['h']
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=0)  # black rectangle

    return img

def generateImage(path='D:/_TMP/base64.png', source=None):
    from PIL import Image
    SIZE = (390, 220)
    MIN_W = 1
    MIN_H = 1
    MIN_AREA = 1 # +2 in loop below
    if source is not None:
        img = source
    else:
        img = Image.open(path)
    # Resize
    img = img.resize(SIZE, Image.NEAREST)
    # Convert to 1-bit (black & white)
    img = img.convert("RGBA").convert("L").convert("1")
    width, height = img.size

    pixels = img.load()
    covered = [[False]*width for _ in range(height)]

    rectangles = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0 and not covered[y][x]:  # black & not yet covered
                # Grow rectangle
                rect_width = 1
                rect_height = 1

                # Determine max width
                while x + rect_width < width and pixels[x + rect_width, y] == 0 and not covered[y][x + rect_width]:
                    rect_width += 1

                # Determine max height
                max_height = 1
                while y + max_height < height:
                    row_valid = True
                    for dx in range(rect_width):
                        if pixels[x + dx, y + max_height] != 0 or covered[y + max_height][x + dx]:
                            row_valid = False
                            break
                    if row_valid:
                        max_height += 1
                    else:
                        break

                # Mark pixels as covered
                for dy in range(max_height):
                    for dx in range(rect_width):
                        covered[y + dy][x + dx] = True

                if (
                        rect_width >= MIN_W and
                        max_height >= MIN_H and
                        rect_width * max_height >= MIN_AREA
                ):
                    rectangles.append({
                        "x": x,
                        "y": y,
                        "w": rect_width,
                        "h": max_height
                    })
    while len(rectangles) > 3000:
        #remove smallest rectangle
        smallest = min([r['w']*r['h'] for r in rectangles])
        rectangles = [r for r in rectangles if r['w']*r['h'] != smallest]


    return rectangles
    pass

async def fetch_band_logos(band_name, num_images=5, display=True, engine=CX_ENGINE):
    """
    Search for a band's logo using Google Custom Search API,
    download up to num_images results, display them, and save locally.

    Skips invalid or non-image URLs gracefully.
    """
    search_query = f"{band_name} logo"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": search_query,
        "cx": engine,
        "key": API_KEY_SEARCH,
        "searchType": "image",
        "num": num_images * 2,  # ask for more, since some might fail
    }

    print(f"Searching for: {search_query} in engine {engine}")
    data,_ = await fetch_async(url, params=params)
    if "items" not in data:
        print("❌ No images found.")
        return (None,None)

    saved_images = []
    image_count = 0
    seen_hashes = set()
    img = None

    for item in data["items"]:
        if image_count >= num_images:
            break

        image_url = item["link"]
        #print(f"⬇️  Downloading: {image_url}")

        try:
            img_data, content_type = await fetch_async(image_url, timeout=10)
            if not content_type.startswith("image/"):
                print(f"⚠️  Skipped non-image URL ({content_type})")
                #print(resp.content[:500])
                continue

            img = Image.open(img_data)

            if not display:
                #print('✅ Image downloaded successfully 001')
                return (img, image_url)

            img_hash = imagehash.average_hash(img)

            if img_hash in seen_hashes:
                print("⚠️ Duplicate image detected, skipping")
                continue
            seen_hashes.add(img_hash)

            image_count += 1
            filename = f"img{image_count}.jpg"
            img.save(filename)
            saved_images.append(filename)
            break

        except (requests.RequestException, UnidentifiedImageError) as e:
            print(f"⚠️  Skipped bad image: {e}")

    # Display the downloaded images
    if saved_images:
        imgs = [Image.open(f) for f in saved_images]
        showImages(imgs, saved_images, band_name)


    # print(f"\n✅ Done! Saved {len(saved_images)} valid images, returning first")
    if len(saved_images) == 0:
        print('✅ Image downloaded successfully 002')
        return (None, None)
    print('✅ Image downloaded successfully 003')
    return (Image.open(saved_images[0]), saved_images[0])

def showImages(imgs, imgnames, band_name='Band Lo'):
    if not imgnames:
        imgnames = ["None" for _ in imgs]
    fig, axes = plt.subplots(1, len(imgs), figsize=(15, 5))
    if len(imgs) == 1:
        axes = [axes]
    for ax, img, name in zip(axes, imgs, imgnames):
        ax.imshow(img, cmap="OrRd")
        ax.axis("off")
        ax.set_title(band_name + ' ' + name)
    plt.tight_layout()
    plt.show()

def cal_auth():
    token_file_name = util.cfgPath+"/../tokens/calendar_secret.json"
    secret_file_name = util.cfgPath+"/../tokens/google_calendar_desktop.json"
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file_name):
        creds = Credentials.from_authorized_user_file(token_file_name, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                # Refresh token is invalid — need to go through full auth flow again
                flow = InstalledAppFlow.from_client_secrets_file(secret_file_name, SCOPES)
                if not isTestingCal():
                    util.sendMail('Bot Calendar Perms 01', 'refresh expired')
                else:
                    print('Bot Calendar Perms 01 - need to reauthorize')
                creds = flow.run_local_server(port=0)
        else:
            if not isTestingCal():
                util.sendMail('Bot Calendar Perms 02', 'nop creds')
            else:
                print('Bot Calendar Perms 02 - need to reauthorize')
                flow = InstalledAppFlow.from_client_secrets_file(
                    secret_file_name, SCOPES
                )
                creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file_name, "w") as token:
            token.write(creds.to_json())
    return creds


async def keep_auth():
    while True:
        try:
            creds = cal_auth()
            print("Calendar auth refreshed "+str(creds.expiry))
        except Exception as e:
            print("Error refreshing calendar auth: "+str(e))
        await asyncio.sleep(3600*random.choice(range(1, 4)))  # Sleep for 1 hour


def fetch_events():
    creds = cal_auth()
    service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    print("Getting the upcoming 10 events")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
        return {}

    result_events = [e for e in events if 'Elyas' not in e["summary"] and 'Wiesbaden' not in e["summary"]] 
    return result_events

def replacementImage(event_name):
    #create image with text
    from PIL import Image, ImageDraw, ImageFont
    SIZE = (390, 220)
    img = Image.new('RGB', SIZE, color = (255, 255, 255))
    d = ImageDraw.Draw(img)
    #make text as large as possible
    text = event_name.split(' ')[0]
    text_size = 40
    while True:
        font = ImageFont.truetype("impact.ttf", text_size)
        text_width, text_height = d.textsize(text, font=font)
        if text_width > SIZE[0] or text_height > SIZE[1]:
            break
        text_size += 2
    #print("text size", text_size)
    d.text(((SIZE[0]-text_width)/2,(SIZE[1]-text_height)/2), text, fill=(0,0,0), font=font)
    #img.save(f'D:/_TMP/{text}.png')
    return img


def getcachedevents():
    with util.OpenCursor(util.DB) as cur:
        cur.execute('select * from control where key = ?', ('calendar_cache',))
        rows = cur.fetchall()
        if len(rows) > 0:
            cur.execute('select * from control where key = ?', ('calendar_reply_cache',))
            rows_2 = cur.fetchall()
            if len(rows_2) > 0:
                return json.loads(rows[0]['value']), json.loads(rows_2[0]['value'])
    return (None, None)

def updatecachedevents(events, reply):
    if not events or not reply:
        return
    util.updateOrInsert('control', {'key': 'calendar_cache'}, {'value': json.dumps(events)}, True, True)
    util.updateOrInsert('control', {'key': 'calendar_reply_cache'}, {'value': json.dumps(reply)}, True, True)
    util.DB.commit()
@calendarroutes.get('/cal/get')
async def get_next(request):
    current_unix_time = int(time.time())
    try:
        cal_events = fetch_events()
        cache = getcachedevents()
        req_val = json.dumps(cal_events)
        if cache[0] == req_val:
            print("Using cached events")
            data = cache[1]
            return web.json_response(data)
        old_events = cache[1]["events"] if cache[1] else []
        pd_events = []
        for event in cal_events:
            #find a link in the description
            links = [lx for lx in event['description'].split() if lx.startswith('http')] if 'description' in event else []
            old_event = None
            for oe in old_events:
                if oe["sourceevent"]["id"] == event["id"]:
                    old_event = oe
                    break
            img = None
            img_url = None
            rects = None
            rects = old_event["rects"] if old_event and \
                                          "rects" in old_event and \
                                          "imageUrl" in old_event and \
                                          old_event["imageUrl"] in links else None
            if rects:
                img_url = old_event["imageUrl"]
                print("Using old cached image for event: "+event["summary"]+": "+img_url)
            else:
                for li in links:
                    data, ct = await fetch_async(li)
                    try:
                        img = Image.open(data)
                        if img:
                            img_url = li
                            print("Found image link in description: "+li)
                            break
                    except Exception as ex:
                        print("exception on : "+li)
                        traceback.print_exception(type(ex), ex, ex.__traceback__)
                        img = None


            if rects is None and img is None and cache[1]:
                #try get the old one
                for old_event in cache[1]["events"]:
                    if old_event["sourceevent"]["id"] == event["id"]:
                        print("Using old cached image for event: "+event["summary"])
                        rects = old_event["rects"]
                        img_url = old_event["imageUrl"]
                        break

            search_list = event["summary"].split(' ')
            search_term = event["summary"]

            while rects is None and img is None and len(search_list)>0:
                search_term = ' '.join(search_list)
                #print("Searching for Image: "+search_term)
                (img, img_url) = await fetch_band_logos(search_term, num_images=2, display=False, engine=CX_ENGINE[0])
                if not img:
                    #print("Searching for Image ALT: "+search_term)
                    (img, img_url) = await fetch_band_logos(search_term, num_images=2, display=False, engine=CX_ENGINE[1])
                if not img:
                    img = replacementImage(event["summary"])
                    img_url = None
                #search_list = search_list[:-1]
                search_list = []

            if img is None and rects is None:
                print("No image found for event: "+event["summary"])
                continue

            if rects is None:
                rects = generateImage(source=img)

            sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', event["summary"].strip())
            if "date" in event["start"]:
                days_until = (datetime.datetime.fromisoformat(event["start"]["date"]).replace(tzinfo=datetime.timezone.utc) - datetime.datetime.now(datetime.timezone.utc)).days
            else:
                days_until = (datetime.datetime.fromisoformat(event["start"]["dateTime"]) - datetime.datetime.now(datetime.timezone.utc)).days
            pd_events.append({
                "daysUntil": days_until,
                "imagePath": "logo_"+sanitized_name,
                "rects": rects,
                "imageUrl": img_url,
                "sourceevent": event
            })
        data = {
            "updated": current_unix_time,
            "events": pd_events
        }
        updatecachedevents(req_val, data)
    except HttpError as error:
        print(f"An error occurred: {error}")
        data = {
            "updated": current_unix_time,
            "events": [
                {
                    "daysUntil": 5,
                    "imagePath": "images/server",
                    "rects": generateImage()
                }
            ]
        }

    return web.json_response(data)



if __name__ == '__main__':
    config = {
        'host': '::',
        'port': 8080
    }
    DBFile = util.cfgPath + '/bot.db';
    import sqlite3
    util.DB = sqlite3.connect(DBFile);
    util.DB.row_factory = util.dict_factory;
    util.DBcursor = util.DB.cursor();
    loop = asyncio.get_event_loop()
    loop.create_task(start_site(web.Application(client_max_size=10000000), config))
    #loop.create_task(download_all_loop([4476, 4478]))
    try:
        print("starting, config:")
        print(config)
        loop.run_forever()
    except Exception as e:
        pass
