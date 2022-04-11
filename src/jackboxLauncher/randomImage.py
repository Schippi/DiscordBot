import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
import math
import numpy as np
import cv2
from jackbox_config import games
from jackbox_server import getGameImage
import sys


def getImagesFromDir(folder: str):
    images = []
    getImagesRecursive(folder, images)
    return images


def getImagesRecursive(folder: str, images: list):
    for file in os.listdir(folder):
        if file.endswith('.jpg') or file.endswith('.png') or file.endswith('.webp'):
            images.append(folder + '/' + file)
        elif os.path.isdir(folder + '/' + file):
            getImagesRecursive(folder + '/' + file, images)


def convert_png_transparent(image, bg_color=(255, 255, 255)):
    array = np.array(image, dtype=np.ubyte)
    mask = (array[:, :, :3] == bg_color).all(axis=2)
    alpha = np.where(mask, 0, 255)
    array[:, :, -1] = alpha
    return Image.fromarray(np.ubyte(array))


def random(steamid: int = 0, all_games: list = games, myprefix :str = ''):
    root_folder = os.path.dirname(sys.argv[0])
    #stuff = [getGameImage(x,root_folder+'/') for x in all_games]
    amount = len(all_games)
    angle = 360 / amount / 2
    masked_images = []
    pic2 = None
    pic = None
    results = [];
    #im = Image.open('images/PartyPack01/Jack_2015.webp')
    #im.show()
    for i, g in enumerate(all_games):
        img = myprefix + getGameImage(g,'/',True)[1:]
        if img[:len('slice_')] == 'slice_':
            pass
        else:
            #print('{\'text\' : \'%s\'},' % g.name)
            results.append('{\'text\' : \'%s\'},' % (g.name.replace('\'', '\\\'')))
            #print('img:%s' % img)
            im = Image.open(img)
            im.convert('RGB')
            w, h = im.size
            #+2 for the pixel border
            height = 2+w * math.sin(math.radians(angle))
            cv_image = cv2.imread(img)
            mask = np.zeros(cv_image.shape, dtype=np.uint8)
            roi_corners = np.array([[(0, h / 2), (w, h / 2 - height), (w, h / 2 + height)]], dtype=np.int32)
            # print(roi_corners,height)
            white = (255, 255, 255)
            cv2.fillPoly(mask, roi_corners, white)
            masked_image = cv2.bitwise_and(cv_image, mask)
            # save the image
            cv2.imwrite('' + str(i) + '.png', masked_image)
        #cv2.imshow('masked image', masked_image)
        #cv2.waitKey()
        if pic is None:
            pic = Image.new('RGBA', (600, 600))
        pic2 = Image.new('RGBA', (600, 600))
        im = Image.open('' + str(i) + '.png')
        im = im.convert('RGBA')
        im = convert_png_transparent(im, bg_color=(0, 0, 0))
        w, h = im.size
        # resize image keep ratio
        newh = int(h * 300 / w)
        im = im.resize((300, newh))

        #im.save("x.png")
        #break;
        im = im.convert('RGBA')
        pic2.paste(im, (300, int(300 - newh / 2)), im)
        pic2 = pic2.rotate(-angle * i *2 ).convert('RGBA')
        masked_images.append(pic2)
        pic.paste(pic2, (0, 0), pic2)

        #delete the image
        os.remove('' + str(i) + '.png')
        if i == amount - 1:
            break;
        #pic.save('' + str(i) + '.png')
    pic = pic.rotate(90-angle).convert('RGBA')
    mask = Image.open(myprefix+'htdocs/mask.png').convert('L')
    pic = ImageOps.fit(pic, mask.size, centering=(0.5, 0.5))
    pic.putalpha(mask)
    pic.save(myprefix+'images/random%d.png' % steamid)
    return '\n'.join(results);

if __name__ == '__main__':
    random();
    im = Image.open('images/random0.png')
    im.show()
