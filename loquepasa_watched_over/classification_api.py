from io import BytesIO
import os, shutil, time
import urllib
from PIL import Image
import pyyolo

darknet_path = '../darknet'
datacfg = 'cfg/coco.data'
cfgfile = 'cfg/yolo.cfg'
weightfile = '../weights/yolo.weights'
thresh = 0.24
hier_thresh = 0.5
pyyolo.init(darknet_path, datacfg, cfgfile, weightfile)

api_dir_path = "api"

def download_file(url, path_to_data, i, w, h, resize):
    local_filename = os.path.join(path_to_data, "temp"+str(i)+".jpg")
    try:
        f = BytesIO(urllib.urlopen(url).read())
        im = Image.open(f)
        size = w,h
        if resize == True:
            im.thumbnail(size, Image.ANTIALIAS)
        im.save(local_filename)
    except Exception as e:
	print "[Error] while downloading image\n\tsrc:",url,"\n\tError:", e
        return None, (0,0)
    return local_filename, im.size

def download_images(data, path_to_client_data, w=640, h=640):
    image_data_object = dict()
    resize = True
    try:
        if data["resize"] == 0: resize = False
    except:
        pass
    urls = data["urls"]
    # print "[Downloading]...", len(urls), "urls"
    err_count = 0
    for i, url in enumerate(urls, 0):
        image_data_object[i] = dict()
        local_path, size = download_file(url, path_to_client_data, i, w, h, resize)
        if local_path == None: err_count += 1
        image_data_object[i]["url"] = url
        image_data_object[i]["path"] = local_path
        image_data_object[i]["img_resize"] = {"w": size[0], "h":size[1]}
    print "[+] Downloaded", len(urls) - err_count, "/", len(urls), "images"
    return image_data_object, len(urls) - err_count

def call_api(data):
    print data
    print "-"*10
    timestamp = str(int(time.time()))
    outdir = api_dir_path+"/"+timestamp
    os.makedirs(outdir)
    image_data, num_valid_images = download_images(data, outdir)
    print image_data
    print "num_valid_images", num_valid_images
    print "-"*10

    out = list()
    err_count = 0
    for idx in image_data:
        img_data = image_data[idx]
        out.append(dict())
        o = out[-1] 
        o["url"] = img_data["url"]
        o["img_resize"] = img_data["img_resize"]
        if img_data["path"] == None:
           o["pred"] = None
           continue
        try:
            o["pred"] = pyyolo.test(img_data["path"], thresh, hier_thresh, 0)
            if len(o["pred"]) == 0:
                o["pred"] = None
        except Exception as e:
            o["pred"] = None
            err_count += 1
            print "[ERROR] while classifiying image\n\tsrc:", o["url"], "\n\tError:", e
    print "[+] Classified", num_valid_images - err_count, "/", num_valid_images, "images"
    shutil.rmtree(outdir) 
    print "[+] Deleted downloaded images."
    print "[+] Returning predictions..."
    return out
