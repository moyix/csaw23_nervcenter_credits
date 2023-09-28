#!/usr/bin/env python3

import sys
import srt
import argparse
import subprocess
import shutil
import os
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import timedelta
from collections import namedtuple
import numpy as np
from tqdm import tqdm
import shlex

TERMWIDTH = 100
FRAME_HEIGHT = 75

# A global variable, for my sins
keep_pngs = False

TimelineEntry = namedtuple('TimelineEntry', ['start', 'end', 'img', 'extra'])

def CreditSubtitle(start, end, role, name, **kwargs):
    content = f"LIST:{role},{name}"
    proprietary = json.dumps(
        {"gravity": ["center", "center"],
            "offset": ["+0-8", "+0+8"],
            "fill": ["gold", "white"],
            "stroke": ["black", "black"],
            "size": [12, 12],
            "font": ["Helvetica-Neue-Bold", "Helvetica-Neue-Bold"],} | kwargs
    )
    return srt.Subtitle(None, start, end, content, proprietary)

# Test subtitle data
test_subs = [
    srt.Subtitle(None, start=timedelta(seconds=2), end=timedelta(seconds=6),content='IMG:cards/mess.png'),
    srt.Subtitle(None, start=timedelta(seconds=6), end=timedelta(seconds=8), content='AND'),
    srt.Subtitle(None, start=timedelta(seconds=8), end=timedelta(seconds=13.5), content='IMG:cards/osiris.png'),
    srt.Subtitle(None, start=timedelta(seconds=15), end=timedelta(seconds=21),
                 content='LIST:NERV Center,C A ’ 3 FINALS, S W 2  FINALS,FINALS',
                 proprietary=json.dumps(
                     {"gravity": ["north", "south", "south", "south"],
                      "offset": ["+0-2", "+0+2", "+4+2", "+28+2"],
                      "fill": ["red", "green", "purple", "white"],
                      "stroke": ["white", "none", "none", "black"],
                      "size": [13,14,14,14],
                      "font": ["Arial-Black", "Iosevka-Heavy","Iosevka-Heavy","Iosevka-Heavy"],})),
    CreditSubtitle(timedelta(seconds=23), timedelta(seconds=27), 'Design & Code', '@moyix', size=[12, 14], offset=["+0-8", "+0+10"]),
    CreditSubtitle(timedelta(seconds=28), timedelta(seconds=32), 'Play Testing', 'OSIRIS Lab'),
    CreditSubtitle(timedelta(seconds=33), timedelta(seconds=37), 'Crypto Consult', 'Sylvain Pelissier'),
    CreditSubtitle(timedelta(seconds=38), timedelta(seconds=42), 'Crypto Consult', 'Marco Macchetti'),
    CreditSubtitle(timedelta(seconds=43), timedelta(seconds=47), 'Crypto Consult', 'Tommaso\nGagliardoni',
                   offset=["+0-16", "+0+8"], size=[12, 13]),
    CreditSubtitle(timedelta(seconds=47.8), timedelta(seconds=51.5), 'Inspiration', 'Flip Feng Shui\nUSENIX’16', offset=["+0-22", "+0+8"]),
    CreditSubtitle(timedelta(seconds=53), timedelta(seconds=57), 'Inspiration', 'RedHat Bugzilla\n892977\n(QEMU)', offset=["+0-22", "+0+8"]),
    srt.Subtitle(None, start=timedelta(seconds=60), end=timedelta(seconds=65),content='IMG:cards/hearts.png'),
    srt.Subtitle(None, start=timedelta(seconds=85), end=timedelta(seconds=90),content='IMG:cards/gideon.png'),
]

def parse_karaoke_time(ts):
    # ts: 0:00:01.02
    #     h:mm:ss.hs
    h, m, s = ts.split(':')
    return timedelta(hours=int(h), minutes=int(m), seconds=float(s))

def parse_karaoke_text(text):
    # Karaoke text looks like:
    #   "{\k77}Za{\k73}n{\k59}ko{\k59}ku {\k35}na {\k38}Te{\k33}n{\k45}shi {\k30}no {\k29}Yo{\k30}u {\k57}ni..."
    # Each {\kXX} means that the following section of text should be highlighted for XX hundredths of a second.
    # We want to parse this into a list of (text, duration) tuples.
    # For the above example, we would return:
    #   [('Za', timedelta(milliseconds=770)), ('n', timedelta(milliseconds=730)), ...]

    # Split the text into sections
    sections = text.split('{\\k')
    # Remove the first section, which is empty
    sections = sections[1:]
    # Parse each section
    parsed = []
    for section in sections:
        # Split the section into the text and the duration
        duration, text = section.split('}')
        # Parse the duration
        duration = timedelta(milliseconds=int(duration)*10)
        # Add to the list
        parsed.append((text, duration))

    return parsed

# Take a parsed karaoke text and return a list of (start, end, text) tuples,
# where text is the full text to be displayed at that time, with the appropriate
# section highlighted using ANSI escape codes.
STYLE_RESET = '\033[0m'
STYLE_HIGHLIGHT = '\033[7m'
STYLE_BOLD = '\033[1m'
def karaoke_to_subtitles(karaoke, start):
    subtitles = []
    for i in range(len(karaoke)):
        before_text = ''.join([t for t, _ in karaoke[:i]])
        text, duration = karaoke[i]
        after_text = ''.join([t for t, _ in karaoke[i+1:]])
        # Highlight the current text
        text = STYLE_BOLD + text + STYLE_RESET
        # Combine the text
        full_text = before_text + text + after_text
        # Add the karaoke entry
        subtitles.append(TimelineEntry(start, start+duration, None, {'karaoke': full_text}))
        # Move the start time forward
        start += duration
    return subtitles

def parse_karaoke(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    karaoke = [l.strip().split(',') for l in lines]
    karaoke = [(parse_karaoke_time(start), parse_karaoke_time(end), parse_karaoke_text(text)) for start, end, text in karaoke]
    output = []
    for i in range(len(karaoke)):
        start, end, text = karaoke[i]
        output.extend(karaoke_to_subtitles(text, start))
        if i < len(karaoke)-1:
            output.append(TimelineEntry(end, karaoke[i+1][0], None, {'karaoke': None}))

    return output

# Returns the part of the convert command that generates the text
def maketext(subtitle='', font='Helvetica-Neue-Bold', size=12, gravity='center', offset='+0+0', alpha=1.0,
                fill='white', stroke='black', strokewidth=2, **kwargs):
    text_command = [
            '(', '-size', f'{TERMWIDTH}x{FRAME_HEIGHT}', 'xc:none',
            '-font', font, '-pointsize', str(size), '-gravity', gravity,
            '-fill', fill, '-stroke', stroke, '-strokewidth', str(strokewidth),
            '-annotate', offset, subtitle, '-stroke', 'none', '-annotate', offset, subtitle,
            '-evaluate', 'multiply', str(alpha), ')'
    ]
    return text_command

# Takes a dict whose values are lists (all the same length) and returns a list of dicts
def demux_dict(d):
    demuxed_count = max([len(v) for v in d.values() if isinstance(v, list)])
    # They have to all be the same length - check that
    for v in d.values():
        if isinstance(v, list) and len(v) != demuxed_count:
            raise ValueError(f"Values in dict must all be the same length. Got {d}")
    dicts = [ {} for _ in range(demuxed_count) ]
    for k in d:
        if not isinstance(d[k], list):
            d[k] = [d[k]] * demuxed_count
        for dest_dict, val in zip(dicts, d[k]):
            dest_dict[k] = val
    return dicts

# Add a subtitle to an image
def add_subtitle(img, output, **kwargs):
    if kwargs['subtitle'].startswith('LIST:'):
        kwargs['subtitle'] = kwargs['subtitle'][5:].split(',')
        dicts = demux_dict(kwargs)
    else:
        dicts = [kwargs]
    cmd = ['convert', img]
    for d in dicts:
        cmd += maketext(**d) + ['-composite']
    cmd += ['-gravity', 'center', output]
    subprocess.run(cmd, check=True)

# Compose two images together. The second image is multiplied by alpha before compositing.
def compose_images(img1, img2, output, gravity='center', alpha=1.0, **kwargs):
    subprocess.run([
        'convert', img1, '-colorspace', 'RGB', '(', img2, '-evaluate', 'multiply', str(alpha), ')',
        '-gravity', gravity, '-composite', output
        ], check=True)

def img_gentxt(img, output, extra):
    with open(output, 'w') as f:
        # Run image gen and wait for it to finish
        f.write('\033[H')
        f.flush()
    with open(output, 'a') as f:
        p = subprocess.run(['./genimg.sh', img], stdout=f, check=True)
        f.flush()
    with open(output, 'a') as f:
        k = extra.get('karaoke', None)
        if not k: k = ' '*TERMWIDTH
        # String length without ANSI escape codes
        length = len(k) - k.count('\033[')*4
        # Center to exactly TERMWIDTH characters.
        left_pad = (TERMWIDTH - length) // 2
        right_pad = TERMWIDTH - length - left_pad
        line = ' '*left_pad + k + ' '*right_pad
        f.write('\n' + line + '\n')

def render_subtitle(img, output, extra):
    subtitle = extra.get('subtitle', None)
    if subtitle is None:
        shutil.copy(img, output)
    elif subtitle.startswith('IMG:'):
        compose_images(img, subtitle[4:], output, **extra)
    else:
        add_subtitle(img, output, **extra)
    # replace extension with .txt
    txt = os.path.splitext(output)[0] + '.txt'
    img_gentxt(output, txt, extra)
    # Remove the image
    if not keep_pngs: os.remove(output)

def combine_timeline_extras(timeline1, timeline2):
    combined = []
    i, j = 0, 0  # Pointers for tl1 and tl2

    while j < len(timeline2):
        t2 = timeline2[j]
        # t2.start, t2.end, t2.img, t2.extra = timeline2[j]

        # If the subtitle list is exhausted, or the current subtitle starts after the frame ends
        if i == len(timeline1) or timeline1[i][0] > t2.end:
            combined.append(t2)
            j += 1  # Move to next frame
        # If the current subtitle ends before the frame starts
        elif timeline1[i].end < t2.start:
            i += 1  # Move to next subtitle
        # If there's an overlap
        else:
            # Combine the extras
            extra = {**timeline1[i].extra, **t2.extra}
            combined.append(TimelineEntry(t2.start, t2.end, t2.img, extra))
            j += 1  # Move to next frame, but keep subtitle pointer same

    return combined

# Takes in a timeline of (start, end, img, extra) tuples and adds fade in/out,
# returning a new timeline of (start, end, img, extra + {'alpha': a}) tuples.
# fade_in and fade_out are in percentage of the subtitle duration.
def add_fade_in_out(timeline, fade_in=0.1, fade_out=0.1):
    def process_run(run):
        tlframes = []
        run_start = run[0].start
        run_end = run[-1].end
        run_duration = run_end - run_start
        fade_in_end = run_start + run_duration * fade_in
        fade_out_start = run_end - run_duration * fade_out
        fade_in_frames = [ frame for frame in run if frame.start < fade_in_end ]
        middle_frames = [ frame for frame in run if frame.start >= fade_in_end and frame.end <= fade_out_start ]
        fade_out_frames = [ frame for frame in run if frame.end > fade_out_start ]
        # Linearly interpolate alpha over the fade in/out frames
        fade_in_alphas = np.linspace(0.0, 1.0, len(fade_in_frames))
        fade_out_alphas = np.linspace(1.0, 0.0, len(fade_out_frames))
        for frame, alpha in zip(fade_in_frames, fade_in_alphas):
            frame.extra['alpha'] = alpha
            tlframes.append(frame)
        for frame in middle_frames:
            frame.extra['alpha'] = 1.0
            tlframes.append(frame)
        for frame, alpha in zip(fade_out_frames, fade_out_alphas):
            frame.extra['alpha'] = alpha
            tlframes.append(frame)
        # print(f"Processed run: {run_start} - {run_end} with {len(run)} frames, text: {repr(run_subtitle)}")
        return tlframes

    new_timeline = []
    # Collect runs where the subtitle is the same
    run = []
    for t in timeline:
        subtitle = t.extra.get('subtitle', None)
        run_subtitle = run[-1].extra.get('subtitle', None) if len(run) > 0 else None
        run_alpha = run[-1].extra.get('alpha', None) if len(run) > 0 else None
        if len(run) == 0 or run_subtitle == subtitle:
            run.append(t)
        else:
            # Process the run
            if run_subtitle is None or run_alpha is not None: # No subtitle, or already has alpha
                new_timeline.extend(run)
            elif run_alpha is None: # Fade in/out
                new_timeline.extend(process_run(run))
            # Start a new run
            run = [t]

    # Process the last run
    run_subtitle = run[-1].extra.get('subtitle', None)
    run_alpha = run[-1].extra.get('alpha', None)
    if run_subtitle is None or run_alpha is not None: # No subtitle, or already has alpha
        new_timeline.extend(run)
    else:
        new_timeline.extend(process_run(run))

    return new_timeline

def test_karaoke_display(karaoke):
    import time
    CLEAR_SCREEN = b'\033[H\033[2J\033[3J'
    MOVE_HOME = b'\033[H'
    HIDE_CURSOR = b'\033[?25l'
    SHOW_CURSOR = b'\033[?25h'
    sys.stdout.buffer.write(CLEAR_SCREEN) ; sys.stdout.buffer.write(HIDE_CURSOR) ; sys.stdout.buffer.flush()
    for st, ed, k in karaoke:
        sys.stdout.buffer.write(MOVE_HOME) ; sys.stdout.buffer.flush()
        duration = ed - st
        if k is not None:
            # String length without ANSI escape codes
            length = len(k) - k.count('\033[')*4
            # Center to exactly TERMWIDTH characters.
            left_pad = (TERMWIDTH - length) // 2
            right_pad = TERMWIDTH - length - left_pad
            line = '|' + ' '*left_pad + k + ' '*right_pad + '|'
            assert left_pad + length + right_pad == TERMWIDTH
            print(line, end='', flush=True)
        else:
            print('|' + ' '*TERMWIDTH + '|', end='', flush=True)
        time.sleep(duration.total_seconds())
    sys.stdout.buffer.write(SHOW_CURSOR) ; sys.stdout.buffer.write(CLEAR_SCREEN) ; sys.stdout.buffer.flush()

def dump_timeline(timeline):
    for start, end, img, extra in timeline:
        print(f"{start} - {end}: {img} {extra}")

def subs2timeline(subs, extra):
    timeline = []
    for s in subs:
        tle = TimelineEntry(s.start, s.end, None, {'subtitle': s.content})
        tle.extra.update(extra)
        if s.proprietary: tle.extra.update(json.loads(s.proprietary))

        timeline.append(tle)
    return timeline

def timeline2subs(timeline):
    subs = []
    for t in timeline:
        text = t.extra.get('subtitle', None)
        if text is not None: del t.extra['subtitle']
        subs.append(srt.Subtitle(None, t.start, t.end, text, json.dumps(t.extra)))
    return subs

def main():
    global keep_pngs
    parser = argparse.ArgumentParser(description='Add subtitles to a sequence of images')
    parser.add_argument('images', nargs='*', help='images to add subtitles to')
    parser.add_argument('-s', '--subtitles', default=None, help='subtitle file (SRT format)')
    parser.add_argument('-f', '--font', default='Helvetica-Neue-Bold', help='font to use')
    parser.add_argument('-z', '--size', type=int, default=12, help='font size')
    parser.add_argument('-g', '--gravity', default='center', help='gravity')
    parser.add_argument('-o', '--offset', default='+0+0', help='offset')
    parser.add_argument('-O', '--output', default='out', help='output directory')
    parser.add_argument('-r', '--rate', type=float, default=23.98, help='frame rate')
    parser.add_argument('-k', '--karaoke', default=None, help='load karaoke file')
    parser.add_argument('--keep-pngs', action='store_true', help='keep the PNGs after rendering')
    parser.add_argument('--rm', action='store_true', help='remove output directory if it exists')
    parser.add_argument('--from', default=None, dest='start_time', help='start time (HH:MM:SS)')
    parser.add_argument('--to', default=None, dest='end_time', help='end time (HH:MM:SS)')
    parser.add_argument('-e', '--export', default=None, help='export subtitles to an SRT file')
    args = parser.parse_args()

    keep_pngs = args.keep_pngs

    default_extra = {
        'font': args.font,
        'size': args.size,
        'gravity': args.gravity,
        'offset': args.offset,
    }

    # Parse the subtitles
    if args.subtitles is not None:
        with open(args.subtitles, 'r') as f:
            subs = list(srt.parse(f.read()))
            subs = subs2timeline(subs, default_extra)
    else:
        subs = subs2timeline(test_subs, default_extra)

    if args.export is not None:
        with open(args.export, 'w') as f:
            f.write(srt.compose(timeline2subs(subs)))
        sys.exit(0)

    # Make sure any images referenced in the subs exist
    for s in subs:
        if s.extra.get('subtitle', None) is None:
            continue
        if s.extra['subtitle'].startswith('IMG:'):
            img = s.extra['subtitle'][4:]
            if not os.path.exists(img):
                raise ValueError(f"Image {img} referenced in subtitle does not exist")

    # Build a timeline of the frames
    time_per_frame = timedelta(seconds=1/args.rate)
    # timeline: tuples of (start_time, end_time, img)
    timeline = []
    for i, img in enumerate(args.images):
        timeline.append(TimelineEntry(i*time_per_frame, (i+1)*time_per_frame, img, {}))

    print(f"Video length: {timeline[-1].end}")

    # Parse the karaoke file
    if args.karaoke is not None:
        karaoke = parse_karaoke(args.karaoke)
        # test_karaoke_display(karaoke)
        # sys.exit(0)

    # Determine which subtitle to show for each frame
    timeline = combine_timeline_extras(subs, timeline)

    # Add fade in/out
    timeline = add_fade_in_out(timeline)

    # Add karaoke
    if args.karaoke is not None:
        timeline = combine_timeline_extras(karaoke, timeline)

    # Trim the timeline
    if args.start_time is not None:
        timeline = [t for t in timeline if t.end >= parse_karaoke_time(args.start_time)]
    if args.end_time is not None:
        timeline = [t for t in timeline if t.start < parse_karaoke_time(args.end_time)]

    # Set up output directory
    if args.rm:
        shutil.rmtree(args.output)
    os.makedirs(args.output, exist_ok=True)

    # Render the subtitles in parallel
    with ProcessPoolExecutor() as executor:
        futures = []
        for t in timeline:
            output = os.path.join(args.output, os.path.basename(t.img))
            futures.append(executor.submit(render_subtitle, t.img, output, t.extra))
        for f in tqdm(as_completed(futures), total=len(futures), desc='Rendering', unit=' frames'):
            f.result()

if __name__ == '__main__':
    main()

