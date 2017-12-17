from io import BytesIO
import urllib
import requests, json, time, os, codecs, sys, ConfigParser, datetime
from PIL import Image, ImageFont, ImageDraw, ImageEnhance, ImageFilter
from pprint import pprint
from posttoig import uploadPhoto, loginIG
from classification_api import call_api
prod = True
recent_ids_path = "./recent_ids.txt"
config = ConfigParser.ConfigParser()
config.read("config.txt")

def get_last_posts(count, prod=False):
   

    if prod:
        # https://api.instagram.com/v1/users/self/media/recent/?access_token=
        url = 'https://api.instagram.com/v1/users/self/media/recent'
        querystring = {
            'access_token': config.get('IGAPI', 'access_token'),
            'count': str(count)
            # 'min_id': ""
        }
        html = requests.get(url, params=querystring).text
        data = json.loads(html)
        with open('test_data.json', 'w') as outfile:
            json.dump(data, outfile)
    else:

        html = open("test_data.json", "r").read()
        data = json.loads(html)

    data =  data["data"]

    out = list()
    # type_to_query
    for post in data:
        o = dict()

        id = post["id"]
        o["id"] = id
        type = post["type"]
        o["type"] = type
        ts = post["created_time"]
        o["created_time"] = ts
        cap = None if post["caption"] == None else post["caption"]["text"]
        o["caption"] = cap
        
        urls = list()
        if type == "carousel":
            #for now I skip this
            continue
            for obj in post["carousel_media"]:
                url = obj["images"]["standard_resolution"]["url"]
                urls.append(url)
        elif type == "video":
            #for now I skip this
            continue
            url = post["videos"]["standard_resolution"]["url"]
            urls.append(url)
        elif type == "image":
            url = post["images"]["standard_resolution"]["url"]
            urls.append(url)

        o["urls"] = urls
        out.append(o)
        if len(out) >= count: break
    return out

def add_classifications(posts):
    urls = [a["urls"][0] for a in posts]
    req_data = dict()
    req_data["urls"] = urls

    # API_ENDPOINT = config.get("CLASSIFICATION", "ip")
     
    # r = requests.post(url = API_ENDPOINT, data=json.dumps(req_data))
    response = call_api(req_data)
    # print r
    
    # response = json.loads(r.text)
    # pprint(response)
    for i, p in enumerate(posts, 0):
       p["pred"] = response[i]["pred"]
       p["img_resize"] = response[i]["img_resize"]
    return posts

def download_img(url, out_path, w=None, h=None):
    f = BytesIO(urllib.urlopen(url).read())
    im = Image.open(f)
    local_filename = url.split('/')[-1]
    base = ".".join(local_filename.split('.')[:-1])
    ext = "." + local_filename.split('.')[-1]

    local_filename = os.path.join(out_path, local_filename)
    if w != None:
        # local_filename = '.'.join(local_filename.split('.')[:-1]) + "_resized." + local_filename.split('.')[-1]
        local_filename = os.path.join(out_path, base + "_resized" + ext)
        im = im.resize((w, h))
    else:
        local_filename = os.path.join(out_path, base + "_orig" + ext)
    im.save(local_filename)
    return local_filename, base, ext

def paint_background(path, color):
    source_img = Image.open(path)
    return Image.new('RGBA', source_img.size, color)

def save_rgba(rgba, path, square=False):
    if not square:
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[3]) # 3 is the alpha channel
    else: 
        factor = 1.2
        img_w = rgba.size[0]
        img_h = rgba.size[1]
        size = int(factor * img_w if img_w > img_h else factor * img_h)
        background = Image.new("RGB", (size, size), (255, 255, 255))
        bg_w, bg_h = background.size
        offset = ((bg_w - img_w) / 2, (bg_h - img_h) / 2)
        background.paste(rgba, offset, mask=rgba.split()[3])
    background.save(path, 'JPEG', quality=100)

def translate(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)

def process_classifications(posts, out_path):
    loginIG()
    for p in posts:
        print p

        # also download original image:
        resized_orig_path, base, ext = download_img(p["urls"][0], out_path)
        
        resized_orig_path, base, ext = download_img(p["urls"][0], out_path, p["img_resize"]["w"], p["img_resize"]["h"])

        im = Image.open(resized_orig_path)

        im = im.filter(ImageFilter.GaussianBlur(16))
        im.save(os.path.join( out_path, base +"_blur" + ext))
       
        

        black_draw = paint_background(resized_orig_path, "black")
        tmp = Image.new('RGBA', im.size, (0,0,0,255))
        
        new_caption = list()

        if p["pred"] != None:

            draw = ImageDraw.Draw(tmp)
            max_contains = 0
            for x in range(im.size[0]):
                for y in range(im.size[1]):
                    rect_contains_count = 0
                    for pred in p["pred"]:
                        pl, pr, pt, pb = pred["left"], pred["right"], pred["top"], pred["bottom"]
                        if x > pl and x < pr and y > pt and y < pb:
                            rect_contains_count += 1
                    if rect_contains_count > max_contains:
                        max_contains = rect_contains_count

            min_opacity = 50
            max_opacity = 230
        
            for x in range(im.size[0]):
                for y in range(im.size[1]):
                    rect_contains_count = 0
                    for pred in p["pred"]:
                        pl, pr, pt, pb = pred["left"], pred["right"], pred["top"], pred["bottom"]
                        if x > pl and x < pr and y > pt and y < pb:
                            rect_contains_count += 1
                    if rect_contains_count > 0:
                        opacity = int(translate(rect_contains_count, 0, max_contains, min_opacity, max_opacity) )
                        r,g,b = im.getpixel((x, y))
                        draw.point((x,y), fill=(r, g, b, opacity))

            # new_caption = list()
            for pred in p["pred"]:
                new_caption.append(pred["class"])
        
        try:
            new_caption = ", ".join(new_caption) 
            # print "NEW CAPTION:", new_caption
            
            # print "OLD CAPTION:", p["caption"]
            if p["caption"] == None: p["caption"] = ""
            cap_combined = ".\n'" + new_caption + "'\n.\n// [" + p["caption"] + "]\n// original image by @loquepasa\n// post from: " + str(datetime.datetime.fromtimestamp(  int(p["created_time"]) ).strftime('%Y-%m-%d'))
            # print "[+] Constructed the caption:\n"
            # print cap_combined
            # print "\n"
        except Exception as e:
            print "[-] Couldn't print the caption of this."
            print "[-] Error:", e
        
        writer = codecs.open(os.path.join(out_path, base + "_caption.txt"), "w", encoding='utf-8')
        writer.write(cap_combined)
        writer.close()



        tmp = Image.alpha_composite(black_draw, tmp)
        save_rgba(tmp, os.path.join(out_path, base + "_classified" + ext))

        try: 
            uploadPhoto(os.path.join(out_path, base + "_classified" + ext), cap_combined)
        except Exception as e:
            print "\n[ERROR WHILE UPLOADING]\n"
            print "\n", e
            sys.exit()
                
        last_id = p["id"]
        writer = open(recent_ids_path, "a")
        writer.write(str(last_id) + "\n")
        writer.close()
	
	time.sleep(5)
        
def get_new_posts_reverse_order(posts, recent_ids_path):
    seen_before = list()
    for line in open(recent_ids_path, "r"):
        line = line.strip()
        seen_before.append(line)
    # last_id = line.strip()
    out_posts = list()
    for post in posts:
        print post
        
        if post["id"].strip() in seen_before:
            print "breaking, have seen this id"
            break
        out_posts.insert(0, post)

    return out_posts
        

if __name__ == "__main__":
    print "\n"*2
    print "-"*10
    print "\n"*2
    print "[+] RUNNING", time.strftime("%c")
    print "\n"*2
    posts = get_last_posts(25, prod)
    pprint(posts)
    print "-"*40
    
    posts = get_new_posts_reverse_order(posts, recent_ids_path)
    pprint(posts)
    print "-"*40

    if len(posts) == 0:
        print "no new images"
        sys.exit()
    
    # print ""
    # pprint(urls)
    
    posts = add_classifications(posts)
    
    print "-"*40

    t = str(int(time.time()))
    o_path = "images/" + t
    os.makedirs(o_path)

    process_classifications(posts, o_path)
    
    # last_id = posts[-1]["id"]
    # writer = open(recent_ids_path, "a")
    # writer.write(str(last_id) + "\n")
    # writer.close()


