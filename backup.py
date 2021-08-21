import tkinter as tk
from tkinter import filedialog
import shutil
import os.path
import time
import datetime
from subprocess import Popen, PIPE
from threading import Thread
from PIL import Image
from PIL.ExifTags import TAGS


def mv(src, dest):
    num = 1
    if os.path.exists(dest):
        parts = list(os.path.splitext(dest))
        filename = parts[0]
        while os.path.exists(dest):
            parts[0] = '{}-{}'.format(filename, num)
            dest = ''.join(parts)
            num += 1
    shutil.move(src, dest)


def get_exif_data(filename):
    """Get embedded EXIF data from image file.
    Source: <a href="http://www.endlesslycurious.com/2011/05/11/extracting-image-">
        http://www.endlesslycurious.com/2011/05/11/extractexif-data-with-python/</a>
    """
    ret = {}
    try:
        img = Image.open(filename)
        if hasattr(img, '_getexif'):
            exif_info = img._getexif()
            if exif_info is not None:
                for tag, value in list(exif_info.items()):
                    decoded = TAGS.get(tag, tag)
                    ret[decoded] = value
    except IOError:
        print('IOERROR ' + filename)
    return ret


def get_m_timestamp(filename):
    modified = os.path.getmtime(filename)
    accessed = os.path.getatime(filename)
    created = os.path.getctime(filename)
    t = min(modified, accessed, created)
    return datetime.datetime.fromtimestamp(t)


def get_timestamp(filename):
    exif_info = get_exif_data(filename)
    if 'DateTimeOriginal' in exif_info:
        datestring = exif_info['DateTimeOriginal']
        return datetime.datetime.strptime(datestring, '%Y:%m:%d %H:%M:%S')
    else:
        return datetime.datetime.fromtimestamp((os.path.getctime(filename)))


def get_size(f):
    ps = Popen('du -sh {}'.format(f), shell=True, stdout=PIPE, stderr=PIPE)
    output = ps.stdout.readlines()[0].strip()
    size = output.split()[0]
    return size


def progress(source, target):
    print('calculating progress')
    while True:
        time.sleep(10)
        if os.path.exists(source) and os.path.exists(target):
            print('{}/{}'.format(get_size(target), get_size(source)))
        else:
            pass


def get_original_filename(path):
    return os.path.split(os.path.splitext(path)[0])[-1]


def should_ignore(cur_dir, items):
    items_to_ignore = []
    if 'cache' in items:
        items_to_ignore.append('cache')
    thumbnails = [x for x in items if x.endswith('.thumbnail')]
    if thumbnails:
        items_to_ignore.extend(thumbnails)
    return items_to_ignore


def get_defaults():
    default_arguments = {}
    default_dest = '/media/fruitschen/新加卷/小树照片temp'
    if os.path.exists(default_dest):
        default_arguments.update({
            'default_dest': default_dest,
        })
    possible_default_froms = [
        '/media/fruitschen/EOS_DIGITAL/DCIM/100CANON',
    ]
    for i in range(10):
        phone = '/run/user/1000/gvfs/mtp:host=%5Busb%3A003%2C00{}%5D/内部存储/DCIM/Camera'.format(i)
        possible_default_froms.append(phone)
    for default_from in possible_default_froms:
        if os.path.exists(default_from):
            default_arguments.update({
                'default_from': default_from,
            })
    return default_arguments


def do_backup(source, target, append_timestamp):
    temp_target_dir = os.path.join(target, 'temp_backup')
    print('Backup in progress')
    t = Thread(target=progress, args=(source, temp_target_dir))
    t.start()
    shutil.copytree(source, temp_target_dir, ignore=should_ignore)
    t.join(timeout=1)
    
    print('Backup done. ')
    print('Processing files')
    
    results_by_month = {}
    
    for root, dirs, files in os.walk(temp_target_dir):
        photos = [x for x in files if '.jpg' in x.lower()]
        for f in photos:
            photo_path = os.path.join(root, f)
            timestamp = get_timestamp(photo_path)
            original_filename = get_original_filename(photo_path)
            extra = ''
            if append_timestamp:
                extra = original_filename
            desired_filename = 'IMG_{}{}.jpg'.format(timestamp.strftime('%Y-%m-%d-%H%M%S'), extra)
            file_month = timestamp.strftime('%Y-%m')
            file_date = timestamp.strftime('%Y-%m-%d')
            result = {
                'file': photo_path,
                'type': 'photo',
                'created': get_timestamp(photo_path),
                'file_date': file_date,
                'desired_filename': desired_filename,
            }
            if file_month in results_by_month:
                pass
            else:
                results_by_month[file_month] = []
            results_by_month[file_month].append(result)
        
        video_formats = ['.avi', '.mp4', '.mts']
        videos = [x for x in files if os.path.splitext(x.lower())[1] in video_formats]
        for f in videos:
            video_path = os.path.join(root, f)
            ext = os.path.splitext(video_path)[-1]
            timestamp = get_m_timestamp(video_path)
            original_filename = get_original_filename(video_path)
            extra = ''
            if append_timestamp:
                extra = original_filename
            desired_filename = 'video_{}{}{}'.format(timestamp.strftime('%Y-%m-%d-%H%M%S'), extra, ext)
            file_month = timestamp.strftime('%Y-%m')
            file_date = timestamp.strftime('%Y-%m-%d')
            result = {
                'file': video_path,
                'type': 'video',
                'created': timestamp,
                'file_date': file_date,
                'desired_filename': desired_filename,
            }
            if file_month in results_by_month:
                pass
            else:
                results_by_month[file_month] = []
            results_by_month[file_month].append(result)
    
    photos_count = 0
    videos_count = 0
    for month, results in list(results_by_month.items()):
        month_photos_count = 0
        month_videos_count = 0
        print('Processing for {}'.format(month))
        print('{} files'.format(len(results)))
        month_dir = os.path.join(temp_target_dir, month)
        if not os.path.exists(month_dir):
            os.makedirs(month_dir)
        for result in results:
            file_date = result['file_date']
            date_dir = os.path.join(month_dir, file_date)
            if not os.path.exists(date_dir):
                os.makedirs(date_dir)
            desired_path = os.path.join(date_dir, result['desired_filename'])
            mv(result['file'], desired_path)
            if result['type'] == 'photo':
                photos_count += 1
                month_photos_count += 1
            if result['type'] == 'video':
                videos_count += 1
                month_videos_count += 1
        print('{} photos'.format(len(results)))
        print('{} videos'.format(len(results)))
        print()
    
    os.rename(temp_target_dir, temp_target_dir.replace('temp_backup', 'backup_{}'.format(
        datetime.datetime.now().strftime('%Y-%m-%d-%H%M'))))
    
    print('Done processing photos')
    print('{} photos in total'.format(photos_count))
    print('{} videos in total'.format(videos_count))


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.default_arguments = get_defaults()
        self.from_dir = self.default_arguments.get('default_from', '')
        self.dest_dir = self.default_arguments.get('default_dest', '')
        self.create_widgets()
    
    def create_widgets(self):
        
        self.from_dir_button = tk.Button(self)
        self.from_dir_button["text"] = "From:\n {}\n(click me to change)".format(self.from_dir, )
        self.from_dir_button["command"] = self.update_from_dir
        self.from_dir_button.pack(side="top")
        
        self.dest_dir_button = tk.Button(self)
        self.dest_dir_button["text"] = "To: \n{}\n(click me to change)".format(self.dest_dir, )
        self.dest_dir_button["command"] = self.update_dest_dir
        self.dest_dir_button.pack(side="top")
        
        self.append_timestamp_val = tk.BooleanVar()
        self.append_timestamp = False
        self.append_widget = tk.Checkbutton(
            self, text='append timestamp and keep original filename',
            command=self.append_timestamp_changed, variable=self.append_timestamp_val,
            onvalue=True, offvalue=False)
        self.append_widget.pack(side="top")
        
        self.backup_button = tk.Button(self, text='Backup', fg='blue', command=self.backup)
        self.backup_button.pack(side="top")
        
        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=self.master.destroy)
        self.quit.pack(side="top")
    
    def update_from_dir(self):
        value = filedialog.askdirectory(initialdir = self.from_dir, title = "From Directory")
        if value:
            self.from_dir = value
            self.from_dir_button["text"] = "From {}\n(click me to change)".format(self.from_dir, )
        
        print("From Directory Changed: {}!".format(self.from_dir))
    
    def update_dest_dir(self):
        value = filedialog.askdirectory(initialdir = self.dest_dir, title = "From Directory")
        if value:
            self.dest_dir = value
            self.dest_dir_button["text"] = "From {}\n(click me to change)".format(self.dest_dir, )
        
        print("To Directory Changed: {}!".format(self.dest_dir))
    
    def append_timestamp_changed(self):
        value = self.append_timestamp_val.get()
        self.append_timestamp = value
        print('append_timestamp_changed: {}'.format(value))
    
    def backup(self):
        do_backup(self.from_dir, self.dest_dir, self.append_timestamp)


if __name__ == '__main__':
    root = tk.Tk()
    app = Application(master=root)
    app.master.title("Backup")
    app.master.maxsize(1000, 400)
    app.mainloop()

