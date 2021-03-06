# Copyright (C) 2010  Alex Yatskov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import time
from math import ceil

DEBUG = False


def set_debug():
    global DEBUG
    DEBUG = True


from PIL import Image, ImageDraw, ImageChops, ImageFilter, ImageOps, ImageStat

from similarity import similarity


class ImageFlags:
    Orient = 1 << 0
    Resize = 1 << 1
    Frame = 1 << 2
    Quantize = 1 << 3
    Stretch = 1 << 4
    SplitRightLeft = 1 << 5  # split right then left
    SplitRight = 1 << 6  # split only the right page
    SplitLeft = 1 << 7  # split only the left page
    SplitLeftRight = 1 << 8  # split left then right page
    AutoCrop = 1 << 9
    Webtoon = 1 << 10


class KindleData:
    Palette4 = [
        0x00, 0x00, 0x00,
        0x55, 0x55, 0x55,
        0xaa, 0xaa, 0xaa,
        0xff, 0xff, 0xff
    ]
    
    Palette15a = [
        0x00, 0x00, 0x00,
        0x11, 0x11, 0x11,
        0x22, 0x22, 0x22,
        0x33, 0x33, 0x33,
        0x44, 0x44, 0x44,
        0x55, 0x55, 0x55,
        0x66, 0x66, 0x66,
        0x77, 0x77, 0x77,
        0x88, 0x88, 0x88,
        0x99, 0x99, 0x99,
        0xaa, 0xaa, 0xaa,
        0xbb, 0xbb, 0xbb,
        0xcc, 0xcc, 0xcc,
        0xdd, 0xdd, 0xdd,
        0xff, 0xff, 0xff,
    ]
    
    Palette15b = [
        0x00, 0x00, 0x00,
        0x11, 0x11, 0x11,
        0x22, 0x22, 0x22,
        0x33, 0x33, 0x33,
        0x44, 0x44, 0x44,
        0x55, 0x55, 0x55,
        0x77, 0x77, 0x77,
        0x88, 0x88, 0x88,
        0x99, 0x99, 0x99,
        0xaa, 0xaa, 0xaa,
        0xbb, 0xbb, 0xbb,
        0xcc, 0xcc, 0xcc,
        0xdd, 0xdd, 0xdd,
        0xee, 0xee, 0xee,
        0xff, 0xff, 0xff,
    ]
    
    Profiles = {
        'Kindle 1'                        : ((600, 800), Palette4),
        'Kindle 2/3/Touch'                : ((600, 800), Palette15a),
        'Kindle 4 & 5'                    : ((600, 800), Palette15b),
        'Kindle DX/DXG'                   : ((824, 1200), Palette15a),
        'Kindle Paperwhite 1 & 2'         : ((758, 1024), Palette15b),
        'Kindle Paperwhite 3/Voyage/Oasis': ((1072, 1448), Palette15b),
        'Kobo Mini/Touch'                 : ((600, 800), Palette15b),
        'Kobo Glo'                        : ((768, 1024), Palette15b),
        'Kobo Glo HD'                     : ((1072, 1448), Palette15b),
        'Kobo Aura'                       : ((758, 1024), Palette15b),
        'Kobo Aura HD'                    : ((1080, 1440), Palette15b),
        'Kobo Aura H2O'                   : ((1080, 1430), Palette15a),
    }


# decorate a function that use image, *** and if there
# is an exception raise by PIL (IOError) then return
# the original image because PIL cannot manage it
def protect_bad_image(func):
    def func_wrapper(*args, **kwargs):
        # If cannot convert (like a bogus image) return the original one
        # args will be "image" and other params are after
        try:
            return func(*args, **kwargs)
        except (IOError, ValueError):  # Exception from PIL about bad image
            return args[0]
    
    
    return func_wrapper


@protect_bad_image
def splitLeft(image):
    widthImg, heightImg = image.size
    
    return image.crop((0, 0, widthImg / 2, heightImg))


@protect_bad_image
def splitRight(image):
    widthImg, heightImg = image.size
    
    return image.crop((widthImg / 2, 0, widthImg, heightImg))


@protect_bad_image
def quantizeImage(image, palette):
    colors = len(palette) / 3
    if colors < 256:
        palette = palette + palette[:3] * (256 - colors)
    
    palImg = Image.new('P', (1, 1))
    palImg.putpalette(palette)
    
    return image.quantize(palette=palImg)


@protect_bad_image
def stretchImage(image, size):
    widthDev, heightDev = size
    
    return image.resize((widthDev, heightDev), Image.ANTIALIAS)


@protect_bad_image
def resizeImage(image, size):
    widthDev, heightDev = size
    widthImg, heightImg = image.size
    
    if widthImg <= widthDev and heightImg <= heightDev:
        return image
    
    ratioImg = float(widthImg) / float(heightImg)
    ratioWidth = float(widthImg) / float(widthDev)
    ratioHeight = float(heightImg) / float(heightDev)
    
    if ratioWidth > ratioHeight:
        widthImg = widthDev
        heightImg = int(widthDev / ratioImg)
    elif ratioWidth < ratioHeight:
        heightImg = heightDev
        widthImg = int(heightDev * ratioImg)
    else:
        widthImg, heightImg = size
    
    if DEBUG:
        print ' * Resizing image from %s to %s/%s' % (image.size, widthImg, heightImg)
    
    return image.resize((widthImg, heightImg), Image.ANTIALIAS)


@protect_bad_image
def formatImage(image):
    if image.mode == 'RGB':
        return image
    
    return image.convert('RGB')


@protect_bad_image
def orientImage(image, size):
    widthDev, heightDev = size
    widthImg, heightImg = image.size
    
    if (widthImg > heightImg) != (widthDev > heightDev):
        return image.rotate(90, Image.BICUBIC, True)
    return image


# We will auto crop the image, by removing just white part around the image
# by inverting colors, and asking a bounder box ^^
@protect_bad_image
def BlurautoCropImage(image):
    orig_image = image
    power = 2.0  # mode: pifometre
    # work on a black image
    blur_image = ImageOps.invert(image.convert(mode='L'))
    blur_image = blur_image.point(lambda x: x and 255)
    blur_image = blur_image.filter(ImageFilter.MinFilter(size=3))
    blur_image = blur_image.filter(ImageFilter.GaussianBlur(radius=5))
    blur_image = blur_image.point(lambda x: (x >= 16 * power) and x)
    blur_bbox = blur_image.getbbox()
    if blur_bbox:
        return orig_image.crop(blur_bbox)
    return orig_image


def _find_dominant_color(img):
    # Resizing parameters
    width, height = 150, 150
    img = img.resize((width, height), resample=0)
    # Get colors from image object
    pixels = img.getcolors(width * height)
    # Sort them by count number(first element of tuple)
    sorted_pixels = sorted(pixels, key=lambda t: t[0])
    # Get the most frequent color
    dominant_color = sorted_pixels[-1][1]
    return dominant_color


def _get_image_variance(image):
    return ImageStat.Stat(image).var[0]


@protect_bad_image
def autoCropImage(image):
    fixed_threshold = 5.0
    
    before = time.time()
    
    if ImageChops.invert(image).getbbox() is None:
        if DEBUG:
            print ' * autoCropImage => Using simpleCropImage because no bbox'
        image = simpleCropImage(image)
        return image
    
    width, height = image.size
    delta = 2
    diff = delta
    if _get_image_variance(image) < 2 * fixed_threshold:
        if DEBUG:
            print ' * autoCropImage => Image variance is already too small, give back image'
        image = simpleCropImage(image)
        return image
    
    while _get_image_variance(image.crop((0, height - diff, width, height))) < fixed_threshold and diff < height:
        diff += delta
    diff -= delta
    pageNumberCut1 = diff
    if diff < delta:
        diff = delta
    oldStat = _get_image_variance(image.crop((0, height - diff, width, height)))
    diff += delta
    while _get_image_variance(image.crop((0, height - diff, width, height))) - oldStat > 0 and diff < height // 4:
        oldStat = _get_image_variance(image.crop((0, height - diff, width, height)))
        diff += delta
    diff -= delta
    pageNumberCut2 = diff
    diff += delta
    oldStat = _get_image_variance(image.crop((0, height - diff, width, height - pageNumberCut2)))
    while _get_image_variance(image.crop((0, height - diff, width, height - pageNumberCut2))) < fixed_threshold + oldStat and diff < height // 4:
        diff += delta
    diff -= delta
    pageNumberCut3 = diff
    delta = 5
    diff = delta
    while _get_image_variance(image.crop((0, height - pageNumberCut2, diff, height))) < fixed_threshold and diff < width:
        diff += delta
    diff -= delta
    pageNumberX1 = diff
    diff = delta
    while _get_image_variance(image.crop((width - diff, height - pageNumberCut2, width, height))) < fixed_threshold and diff < width:
        diff += delta
    diff -= delta
    pageNumberX2 = width - diff
    if pageNumberCut3 - pageNumberCut1 > 2 * delta and float(pageNumberX2 - pageNumberX1) / float(pageNumberCut2 - pageNumberCut1) <= 9.0 \
            and _get_image_variance(image.crop((0, height - pageNumberCut3, width, height))) / ImageStat.Stat(image).var[0] < 0.1 \
            and pageNumberCut3 < height / 4 - delta:
        diff = pageNumberCut3
    else:
        diff = pageNumberCut1
    
    if DEBUG:
        print ' * autoCropImage:: Computing crop diff to %s (in %.3f)' % (diff, time.time() - before)
        image.save('tmp/1_before_crop.png')
    
    before = time.time()
    image = image.crop((0, 0, width, height - diff))
    if DEBUG:
        print ' * autoCropImage:: apply crop to %s (in %.3f)' % (diff, time.time() - before)
        image.save('tmp/2_after_crop.png')
    
    before = time.time()
    image = simpleCropImage(image)
    if DEBUG:
        print ' * autoCropImage:: simple crop to %s in %.3f' % (image.size, time.time() - before)
        image.save('tmp/3_after_simple_crop.png')
    
    before = time.time()
    image = BlurautoCropImage(image)
    if DEBUG:
        print ' * autoCropImage:: Blurauto %s in %.3f' % (image.size, time.time() - before)
        image.save('tmp/4_after_auto_blur.png')
    
    return image


@protect_bad_image
def simpleCropImage(image):
    try:
        x0, y0, xend, yend = ImageChops.invert(image).getbbox()
    except TypeError:  # bad image, specific to chops
        return image
    image = image.crop((x0, y0, xend, yend))
    return image


def frameImage(image, foreground, background, size):
    widthDev, heightDev = size
    widthImg, heightImg = image.size
    
    pastePt = (
        max(0, (widthDev - widthImg) / 2),
        max(0, (heightDev - heightImg) / 2)
    )
    
    corner1 = (
        pastePt[0] - 1,
        pastePt[1] - 1
    )
    
    corner2 = (
        pastePt[0] + widthImg + 1,
        pastePt[1] + heightImg + 1
    )
    
    imageBg = Image.new(image.mode, size, background)
    imageBg.paste(image, pastePt)
    
    draw = ImageDraw.Draw(imageBg)
    draw.rectangle([corner1, corner2], outline=foreground)
    
    return imageBg


QUITE_BLACK_LIMIT = 25  # 25: totally my choice after look at colors ^^


# Can be black is really black, or just VERY dark
def is_quite_black(pixel, precision=QUITE_BLACK_LIMIT):
    if pixel == (0, 0, 0):
        return True
    if pixel[0] <= precision and pixel[1] <= precision and pixel[2] <= precision:
        return True
    return False


def is_quite_white(pixel, precision=QUITE_BLACK_LIMIT):
    if pixel == (255, 255, 255):
        return True
    if pixel[0] >= 255 - precision and pixel[1] >= 255 - precision and pixel[2] >= 255 - precision:
        return True
    return False


def is_background_pixel(pixel, is_black_background):
    if is_black_background:
        return is_quite_black(pixel, precision=10)
    return is_quite_white(pixel, precision=10)


LINE_DEBUG = -1

MIN_BOX_ALLOWED_HEIGHT = 36  # lower than this height, it's a bogus box

SOFT_MAX_BLOC_HEIGHT = 1500  # if higher than this, try to split into parts again

HARD_MAX_BLOC_HEIGHT = 3000  # if higher than this, stop the block


def __get_image_height(image):
    return image.size[1]


def __get_image_width(image):
    return image.size[0]


WHITE_PIXEL = (255, 255, 255)


# Remove images that are full white or full black
def is_full_background_image(image):
    image_rgb = image.convert('RGB')
    height = __get_image_height(image)
    width = __get_image_width(image)
    pixels = image_rgb.load()
    start_pixel = pixels[0, 0]
    is_white = is_quite_white(start_pixel, precision=1)
    is_black = is_quite_black(start_pixel, precision=1)
    if is_white:
        for x in xrange(width):
            for y in xrange(height):
                pixel = pixels[x, y]
                if not is_quite_white(pixel, precision=1):
                    return False
        # all was white
        return True
    if is_black:
        for x in xrange(width):
            for y in xrange(height):
                pixel = pixels[x,y]
                if not is_quite_black(pixel, precision=1):
                    return False
        # all was black
        return True
    
    # First pixel was not white or black
    return False
    


def __fail_back_to_cut_very_big_one(image):
    image_height = __get_image_height(image)
    image_width = __get_image_width(image)
    print "__fail_back_to_cut_very_big_one:: %s" % image_height
    if image_height <= HARD_MAX_BLOC_HEIGHT:
        return [image]
    
    hard_split_images = []
    nb_images = int(ceil(float(image_height) / HARD_MAX_BLOC_HEIGHT))
    
    for idx in xrange(nb_images):
        hard_split = image.crop((0, idx * HARD_MAX_BLOC_HEIGHT, image_width, (idx + 1) * HARD_MAX_BLOC_HEIGHT))
        hard_split_images.append(hard_split)
    print "__fail_back_to_cut_very_big_one:: cut into %s parts" % len(hard_split_images)
    return hard_split_images


# We have a block image that is too big, try to see if with linear cut it's possible to
# have more parts
def __try_to_smart_split_block(image, is_black_background, level=1):
    image = simpleCropImage(image)
    if DEBUG:
        image.save('tmp/input_%s.jpg' % level)
    image_height = __get_image_height(image)
    image_width = __get_image_width(image)
    print " === [LEVEL=%s] Try to smart split block of size %s / %s  (mostly black=%s)" % (level, image_height, image_width, is_black_background)
    
    # Maybe the image is now too small: just give it back :)
    if image_height <= 200:
        return [image]
    
    split_pixel = WHITE_PIXEL if not is_black_background else (0, 0, 0)
    print " ==== Finding for pixel: %s" % str(split_pixel)
    pixels = image.load()
    for y in range(500, image_height - 200, 10):  # do not try to cut too early, it's useless
        # First look if the left => higher right is possible for split
        line_is_valid = False
        found_angle = None
        from_left = True
        pixel = pixels[0, y]
        if is_background_pixel(pixel, is_black_background):
            # if y == 2310:
            #     print " ==== Founded good start pixel at line %s" % y
            for angle_int in range(0, 200):
                angle = float(angle_int) / 100
                found_angle = angle
                line_is_valid = True
                for x in xrange(image_width):
                    tested_pixel_y = y - ceil(x * angle)
                    if tested_pixel_y <= 0:
                        line_is_valid = False
                        break
                    # if y == 2310 and angle_int == 58:
                    #    print " ====== [Y=%s Angle=%s] Testing pixel %s / %s" % (y, angle, x, tested_pixel_y)
                    tested_pixel = pixels[x, tested_pixel_y]
                    # if y == 2310 and angle_int == 58:
                    #    pixels[x, tested_pixel_y] = (255, 0, 0)
                    if not is_background_pixel(tested_pixel, is_black_background):
                        # if y == 2310:
                        #     print "LEFT: [Y=%s Angle=%s] Line is not valid at x=%s y=%s (color=%s)" % (y, angle, x, tested_pixel_y, str(tested_pixel))
                        #     if angle_int == 58:
                        #         image.save('tmp/with_line2.jpg')
                        #         #fuck
                        line_is_valid = False
                        break
                # We did found a valid split line
                if line_is_valid:
                    break
            if line_is_valid:
                print "LEFT:: found a valid split line, angle=%s y=%s" % (found_angle, y)
        
        # Then is the line is not found look if the right => higher left is possible for split
        if not line_is_valid and pixels[image_width - 1, y] == split_pixel:
            from_left = False
            for angle_int in range(0, 200):
                angle = float(angle_int) / 100
                found_angle = angle
                line_is_valid = True
                
                for x in xrange(image_width - 1, -1, -1):
                    tested_pixel_y = y - int(ceil((image_width - x) * angle))
                    if tested_pixel_y <= 0:
                        line_is_valid = False
                        break
                    
                    tested_pixel = pixels[x, tested_pixel_y]
                    if not is_background_pixel(tested_pixel, is_black_background):
                        line_is_valid = False
                        break
                # We did found a valid split line
                if line_is_valid:
                    # print "[RIGHT] Line %s is splitable with angle=%s" % (y, found_angle)
                    break
        
        # Maybe nor left or right was able to split, skip this line
        if not line_is_valid:
            continue
        
        print "Yeah, we can cut from %s with angle %s and from left:%s" % (y, found_angle, from_left)
        
        split_pixels = {}
        if from_left:
            for x in xrange(image_width):
                split_pixels[x] = y - int(ceil(x * found_angle))
        else:
            for x in xrange(image_width - 1, -1, -1):
                split_pixels[x] = y - int(ceil((image_width - x) * found_angle))
        lower_y = min(split_pixels.values())
        higher_y = max(split_pixels.values())
        
        # We will have 2 images:
        # * higher part that will erase all UNDER the line
        # * lower part that will erase all TOP the line
        higher_part_image = image.copy()
        higher_part_pixels = higher_part_image.load()
        rest_to_split_image = image.copy()
        rest_to_split_pixels = rest_to_split_image.load()
        
        # For debug:
        if DEBUG:
            if from_left:
                for x in xrange(image_width):
                    tested_pixel_y = y - ceil(x * found_angle)
                    # print " ====== LEFT [Y=%s Angle=%s] SPLIT LINE WAS Testing pixel %s / %s :: %s" % (y, found_angle, x, tested_pixel_y, str(pixels[x, tested_pixel_y]))
                    pixels[x, tested_pixel_y] = (255, 0, 0)
            else:
                for x in xrange(image_width - 1, -1, -1):
                    tested_pixel_y = y - int(ceil((image_width - x) * found_angle))
                    # print " ====== RIGHT [Y=%s Angle=%s] SPLIT LINE WAS Testing pixel %s / %s :: %s" % (y, found_angle, x, tested_pixel_y, str(pixels[x, tested_pixel_y]))
                    pixels[x, tested_pixel_y] = (255, 0, 0)
        
        if DEBUG:
            image.save('tmp/with_line_%s.jpg' % level)
            print "SPLIT RANGE", lower_y, higher_y
        
        # HIGHER PART: clean all BELOW the line
        for y in xrange(lower_y, higher_y):
            for x in xrange(image_width):
                line_y = split_pixels[x]
                if y > higher_y or y > line_y:
                    higher_part_pixels[x, y] = WHITE_PIXEL
        
        # We must crop it to remove all useless part
        higher_part_image = higher_part_image.crop((0, 0, image_width, higher_y))
        if DEBUG:
            higher_part_image.save('tmp/higher_part_%s.jpg' % level)
        
        # LOWER PART: clean all OVER the line
        for y in xrange(lower_y, higher_y):
            for x in xrange(image_width):
                line_y = split_pixels[x]
                if y < lower_y or y < line_y:
                    rest_to_split_pixels[x, y] = WHITE_PIXEL
        
        rest_to_split_image = rest_to_split_image.crop((0, lower_y, image_width, image_height))
        if DEBUG:
            rest_to_split_image.save('tmp/rest_%s.jpg' % level)
        
        res = [higher_part_image]
        
        rest_image_splitted = __try_to_smart_split_block(rest_to_split_image, is_black_background, level=level + 1)
        res.extend(rest_image_splitted)
        
        return res
    
    # We did failed to split it so give back the original image
    print "did fail to smart split the image, still %s high" % image_height
    # fuck
    fail_back_images = __fail_back_to_cut_very_big_one(image)
    return fail_back_images


def __parse_webtoon_block(image, start_of_box, width, end_of_box, split_final_images, is_black_background):
    box_image = image.crop((0, start_of_box, width, end_of_box))
    
    potential_images = [box_image]
    # Maybe it's too high
    img_height = __get_image_height(box_image)
    if img_height >= SOFT_MAX_BLOC_HEIGHT:
        print " *** WebToon block is too high (%s), trying to split it again" % img_height
        potential_images = __try_to_smart_split_block(box_image, is_black_background, level=0)
    
    for p_image in potential_images:
        # TODO: TEST: if all pixels are black: drop
        image_cropped = autoCropImage(p_image)
        # Skip images that are too small (bugs in cut detection protection)
        if __get_image_height(image_cropped) <= MIN_BOX_ALLOWED_HEIGHT:
            print "SKIP: image is too small to save (%dpx)" % __get_image_height(image_cropped)
            continue
        if not similarity.is_valid_image(image_cropped):
            print " ** DROPPING IMAGE"
            continue
        if is_full_background_image(image_cropped):
            print " ** Dropping full white/black image"
            continue
        print " Split size: %s" % str(image_cropped.size)
        split_final_images.append(image_cropped)


def splitWebtoon(image):
    split_images = []
    width, height = image.size
    
    # If we have a black background, good luck to split by white
    most_color = _find_dominant_color(image)
    is_black_background = most_color == (0, 0, 0)
    
    print " TOON: analysing image %s/%s  (is black background=%s)" % (width, height, is_black_background)
    MIN_COLOR_HEIGHT = 30  # not less than 30px for an picture
    MAX_BOX_HEIGHT = 1400  # if more than 1400, if possible, close box
    pixels = image.load()  # this is not a list, nor is it list()'able
    
    lines = []
    for y in range(height):
        is_white = True
        for x in range(width):
            cpixel = pixels[x, y]
            # If classic white background
            if not is_black_background:
                if cpixel != WHITE_PIXEL:
                    is_white = False
                    break
            else:  # black background, do not look at black
                if y == LINE_DEBUG:
                    print "PIXEL: %s => %s" % (x, str(cpixel))
                if not is_quite_black(cpixel) and not cpixel == WHITE_PIXEL:
                    is_white = False
                    break
                # else:
                #    print "Line %s is white" % y
        if y == LINE_DEBUG:
            print "%s IS WHITE LINE: %s" % (y, is_white)
        lines.append((y, is_white))
    
    print "Number of white lines: %s" % (len([c for c in lines if c[1]]))
    
    start_of_box = None
    in_box = False
    last_black_line = None
    for (y, is_white_line) in lines:
        # First line: we are starting a box or not
        if y == 0:
            in_box = not is_white_line
            if in_box:
                start_of_box = y
                last_black_line = y
            continue
        
        if in_box and False:
            current_box_size = y - start_of_box
            if current_box_size > HARD_MAX_BLOC_HEIGHT:
                __parse_webtoon_block(image, start_of_box, width, y, split_images, is_black_background)
                last_black_line = None
                start_of_box = None
                in_box = False
                print "***" * 20, "Protection, split at", current_box_size
                continue
        
        # we already start
        # If black can continue a box or start a new one
        if not is_white_line:
            # we are a black line, so maybe we just continue the box
            if in_box:
                last_black_line = y
                continue
            # or we start a new one
            else:
                print ' - Starting a box at %s' % y
                in_box = True
                last_black_line = y
                start_of_box = y
                continue
        # Is a white line, we can close the box
        else:
            if not in_box:
                # TODO: do not allow a too big white part
                continue
            current_box_size = y - start_of_box
            # print "WHITE: current box size detecte", current_box_size
            # Close the box only if the last black if far ago
            # Of if the box is very high
            distance_from_last_black = y - last_black_line
            if distance_from_last_black > MIN_COLOR_HEIGHT or current_box_size > MAX_BOX_HEIGHT:
                __parse_webtoon_block(image, start_of_box, width, y, split_images, is_black_background)
                last_black_line = None
                start_of_box = None
                in_box = False
    
    # We did finish, if we was in a box, close it
    if in_box:
        __parse_webtoon_block(image, start_of_box, width, last_black_line, split_images, is_black_background)
    
    return split_images


def loadImage(source):
    try:
        return Image.open(source)
    except IOError:
        raise RuntimeError('Cannot read image file %s' % source)


def saveImage(image, target):
    try:
        image.save(target)
    except IOError:
        raise RuntimeError('Cannot write image file %s' % target)


# Look if the image is more width than hight, if not, means
# it's should not be split (like the front page of a manga,
# when all the inner pages are double)
def isSplitable(source):
    image = loadImage(source)
    try:
        widthImg, heightImg = image.size
        return widthImg > heightImg
    except IOError:
        raise RuntimeError('Cannot read image file %s' % source)


def convertImage(source, target, device, flags):
    try:
        size, palette = KindleData.Profiles[device]
    except KeyError:
        raise RuntimeError('Unexpected output device %s' % device)
    # Load image from source path
    image = loadImage(source)
    
    # Format according to palette
    
    # Webtoon is special, manually take order
    if flags & ImageFlags.Webtoon:
        converted_images = []  # we can have more than 1 results
        images = splitWebtoon(image)
        for image in images:
            image = formatImage(image)
            # if flags & ImageFlags.Orient:
            #    image = orientImage(image, size)
            if flags & ImageFlags.Resize:
                image = resizeImage(image, size)
            if flags & ImageFlags.Stretch:
                image = stretchImage(image, size)
            if flags & ImageFlags.Quantize:
                image = quantizeImage(image, palette)
            converted_images.append(image)
        
        return converted_images
    
    image = formatImage(image)
    
    # Apply flag transforms
    if flags & ImageFlags.SplitRight:
        image = splitRight(image)
    if flags & ImageFlags.SplitRightLeft:
        image = splitLeft(image)
    if flags & ImageFlags.SplitLeft:
        image = splitLeft(image)
    if flags & ImageFlags.SplitLeftRight:
        image = splitRight(image)
    
    # Auto crop the image, but before manage size and co, clean the source so
    if flags & ImageFlags.AutoCrop:
        image = autoCropImage(image)
    if flags & ImageFlags.Orient:
        image = orientImage(image, size)
    if flags & ImageFlags.Resize:
        image = resizeImage(image, size)
    if flags & ImageFlags.Stretch:
        image = stretchImage(image, size)
    if flags & ImageFlags.Frame:
        image = frameImage(image, tuple(palette[:3]), tuple(palette[-3:]), size)
    if flags & ImageFlags.Quantize:
        image = quantizeImage(image, palette)
    
    return [image]  # only one image if not webtoon
