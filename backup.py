# coding: utf-8
from gooey import Gooey, GooeyParser
import time
import shutil
import os.path
import datetime
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
        if hasattr( img, '_getexif' ):
            exifinfo = img._getexif()
            if exifinfo != None:
                for tag, value in exifinfo.items():
                    decoded = TAGS.get(tag, tag)
                    ret[decoded] = value
    except IOError:
        print 'IOERROR ' + filename
    return ret

def get_timestamp(filename):
    exif_info = get_exif_data(filename)
    if 'DateTimeOriginal' in exif_info:
        datestring = exif_info['DateTimeOriginal']
        return datetime.datetime.strptime(datestring, '%Y:%m:%d %H:%M:%S')
    else:
        return datetime.datetime.fromtimestamp((os.path.getctime(filename)))


@Gooey
def main():
    parser = GooeyParser(description="My Cool GUI Program!")
    parser.add_argument('source', widget="DirChooser")
    parser.add_argument('target', widget="DirChooser")
    args = parser.parse_args()
    source = args.source
    target = args.target
    temp_target_dir = os.path.join(target, 'temp_backup')
    print 'Backup in progress'
    shutil.copytree(source, temp_target_dir)
    print 'Backup done. '
    print 'Processing files'

    results_by_month = {}

    for root, dirs, files in os.walk(temp_target_dir):
        photos = filter(lambda x: '.jpg' in x.lower(), files)
        for f in photos:
            photo_path = os.path.join(root, f)
            timestamp = get_timestamp(photo_path)
            desired_filename = 'IMG_{}.jpg'.format(timestamp.strftime('%Y-%m-%d-%H%M%S'))
            file_month = timestamp.strftime('%Y-%m')
            file_date = timestamp.strftime('%Y-%m-%d')
            result = {
                'file': photo_path,
                'created': get_timestamp(photo_path),
                'file_date': file_date,
                'desired_filename': desired_filename,
            }
            if file_month in results_by_month:
                pass
            else:
                results_by_month[file_month] = []
            results_by_month[file_month].append(result)

    photos_count = 0
    for month, results in results_by_month.items():
        print 'Processing for {}'.format(month)
        print '{} files'.format(len(results))
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
            photos_count += 1

    os.rename(temp_target_dir, temp_target_dir.replace('temp_backup', 'backup_{}'.format(datetime.datetime.now().strftime('%Y-%m-%d-%H%M'))))

    print 'Done processing photos'
    print '{} photos'.format(photos_count)

if __name__ == '__main__':
    main()


