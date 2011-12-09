import os, glob, tempfile, subprocess

import Image, ImageDraw 


def frame(filebase, frame_num, size=(100,50)):
    ''' A View that Returns a PNG Image generated using PIL'''
    im = Image.new('RGB', size)
    draw = ImageDraw.Draw(im)
    color = (0,255,0)
    top_left_pos = (10,10)
    text = "Frame #%d" % frame_num
    draw.text(top_left_pos, text, fill=color)
    
    filename = "%s%05d.png" % (filebase, frame_num)
    im.save(filename, "PNG")
    return filename

def create_images(frames, width, height):
    root = tempfile.mkdtemp()
    filebase = "%s/frame" % root
    for f in range(frames):
        filename = frame(filebase, f + 1, size=(width, height))
        print filename
    return filebase

def encode(filebase, bitrate, fps):
    output = "%s-video.mkv" % filebase
    args = ["ffmpeg",
            "-r", str(fps),
            "-b", str(bitrate),
            "-f", "image2",
            "-i", "%s%%05d.png" % filebase,
            output]
    
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    print output
    return output

def merge(video, audio_args, subtitle_args, output):
    try:
        os.unlink(output)
    except OSError:
        pass
    args = ["mkvmerge",
            "-o", output,
            video,
            ]
    extra_args = []
    if audio_args:
        extra_args.extend(audio_args)
    if subtitle_args:
        extra_args.extend(subtitle_args)
    if extra_args:
        args.extend(extra_args)
        print args
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        print stdout
        print stderr
    else:
        os.rename(video, output)

def get_audio(files, user_names, user_langs):
    args = []
    if files:
        names = ["Audio Track #%d" % (i+1) for i in range(len(files))]
        names[0:len(user_names)] = user_names
        langs = ["und" for i in range(len(files))]
        langs[0:len(user_langs)] = user_langs
        for file, name, lang in zip(files, names, langs):
            args.extend(["--track-name", "0:%s" % name, "--language", "0:%s" % lang, file])
        print args
    return args

def get_subtitles(files, user_names, user_langs):
    args = []
    if files:
        names = ["Subtitle #%d" % (i+1) for i in range(len(files))]
        names[0:len(user_names)] = user_names
        langs = ["und" for i in range(len(files))]
        langs[0:len(user_langs)] = user_langs
        for file, name, lang in zip(files, names, langs):
            args.extend(["--track-name", "0:%s" % name, "--language", "0:%s" % lang, file])
        print args
    return args

def clean(filebase):
    for name in glob.glob("%s*" % filebase):
        os.unlink(name)
    os.rmdir(os.path.dirname(filebase))


if __name__ == "__main__":
    from optparse import OptionParser

    usage="usage: %prog [options] file [files...]"
    parser=OptionParser(usage=usage, conflict_handler="resolve")
    parser.add_option("-f", action="store", type="int", dest="frames", default=100, help="Number of frames to encode")
    parser.add_option("-w", action="store", type="int", dest="width", default=100, help="Frame width")
    parser.add_option("-h", action="store", type="int", dest="height", default=50, help="Frame height")
    parser.add_option("-b", action="store", type="int", dest="bitrate", default=8000, help="Video bitrate")
    parser.add_option("-r", action="store", type="int", dest="fps", default=10, help="Frames per second")
    parser.add_option("-a", "--audio", action="append", dest="audio_files", default=[], help="Audio file to merge")
    parser.add_option("--an", action="append", dest="audio_names", default=[], help="Name of corresponding audio file")
    parser.add_option("--al", action="append", dest="audio_langs", default=[], help="Language (ISO639-1 or ISO639-2 code) of corresponding audio file")
    parser.add_option("-s", "--subtitle", action="append", dest="subtitle_files", default=[], help="Subtitle file to merge")
    parser.add_option("--sn", action="append", dest="subtitle_names", default=[], help="Name of corresponding subtitle file")
    parser.add_option("--sl", action="append", dest="subtitle_langs", default=[], help="Language (ISO639-1 or ISO639-2 code) of corresponding subtitle file")
    parser.add_option("-o", action="store", dest="output", default="output.mkv", help="Output filename")
    
    (options, args) = parser.parse_args()
    filebase = create_images(options.frames, options.width, options.height)
    video = encode(filebase, options.bitrate, options.fps)
    audio_args = get_audio(options.audio_files, options.audio_names, options.audio_langs)
    subtitle_args = get_subtitles(options.subtitle_files, options.subtitle_names, options.subtitle_langs)
    merge(video, audio_args, subtitle_args, options.output)
    clean(filebase)
