#!/usr/bin/env python3
"""
Author: Ollipop, Xllvr
"""
import tkinter as tk
from tkinter import filedialog
import re
import csv
import os
import json
import time
import argparse


#tag: (Pos[0], Bord[1], Name[2], Fontname[3], Fontsize[4], PrimaryColour[5], SecondaryColour[6], OutlineColour[7], BackColour[8], Bold[9], Italic[10], Underline[11],
#      StrikeOut[12], ScaleX[13], ScaleY[14], Spacing[15], Angle[16], BorderStyle[17], Outline[18], Shadow[19], Alignment[20], MarginL[21], MarginR[22], MarginV[23], Encoding[24])
STYLES = {}

#TODO could also make this configurable!
DELIM = ","
COMMENT_TAG = "comm"

AEGISCRIPT_TEMPLATE = '''[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{events}'''

def generateStyleLine(style):
    """Creates an Aegisub Style line from a styles dictionary value

    Args:
        style (tuple): Tuple containing the values for an Aegisub style, taken from our STYLES map

    Returns:
        string: Properly formatted Aegisub Style line
    """
    return "Style: " + ','.join(str(x) for x in style[2::])


def parseCsvRow(row):
    """Takes a parsed csv row from a dialogue file and converts it to an Aegisub dialogue line

    Args:
        row (list[string]): A row from the dialogue file, parsed by the csv reader

    Returns:
        string: A Dialogue line in the .ass dialogue format
    """
    #Check for comment tag, since comment formatting is a bit different
    comment_row = False
    if(row[0] == COMMENT_TAG):
        comment_row = True

    style_data = STYLES.get(row[0], STYLES.get("default"))
    pos = style_data[0]
    bord = style_data[1]
    style_name = style_data[2]

    try:
        #TODO Figure out a more elegant way to do this (accounting for )
        ts_format = row[1].count(":")
        if(ts_format == 1):
            csv_time = time.strptime(row[1], "%M:%S")
            #print(f"CSV time: {csv_time}")
        else:
            csv_time = time.strptime(row[1], "%H:%M:%S")
            #print(f"CSV time: {csv_time}")

        timestamp = time.strftime("%H:%M:%S.00", csv_time) #CSV files don't have sub-second precision, so don't bother with it
        #Yeah it's treating this like a date-time instead of an elapsed time. If you have timestamps in excess of 24 hours it might break...
        #So don't make clips in excess of 24 hours please 草
    except:
        print("Couldn't parse timestamp at row: " + ','.join(row))
        timestamp = "0:00:00.00" #Default to 0 if we can't parse it
    dialogue = row[2]

    if(not comment_row):
        return f"Dialogue: 1,{timestamp},{timestamp},{style_name},,0,0,0,,{{\\bord{bord}\pos({pos})\\3c&H000000&\}}{dialogue}"
    else:
        return f"Comment: 1,{timestamp},{timestamp},{style_name},,0,0,0,,{dialogue}"


def csvParser(fname, out_fn = ""):
    """Accepts a .csv file in the format of tag, timestamp, dialogue and writes the dialogue out to a complete Aegisub file

    Args:
        fname (string): the path to the csv file to be loaded, WITHOUT the extension
        [out_fn] (string): the path to the output file to write to
    """
    if(not out_fn):
        out_fn = f"{fname}_out.ass"

    dialogues = []
    styles_section = map(generateStyleLine, STYLES.values())
    template = AEGISCRIPT_TEMPLATE #TODO turn this into a class?

    with open(f"{fname}.csv", encoding = 'UTF-8') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=DELIM)
        dialogues = list(map(parseCsvRow, csv_reader))

    template = template.replace("{styles}", '\n'.join(styles_section))
    template = template.replace("{events}", '\n'.join(dialogues))

    with open(out_fn, mode = "w", encoding = 'UTF-8') as out_file:
        out_file.write(template)
    print(f"Successfully wrote Aegisub file to {out_fn}")


def generateLayer2(dialogue):
    """Generates a second layer for each dialogue event, with identical text and timestamp

    Args:
        dialogue (string): The layer 1 line of dialogue taken from the original Aegisub file

    Returns:
        string: The original layer 1 line of dialogue with the layer 2 line of dialogue appended to it
    """
    dialogue = dialogue.rstrip()
    layer2 = dialogue
    layer2 = layer2.replace("Dialogue: 1,", "Dialogue: 2,")
    layer2 = re.sub(r'\{.*(\\pos.+\)).+\}', r'{\1}', layer2)
    return dialogue + '\n' + layer2 + '\n'


def postProcessParser(fname, out_fn=""):
    """Accepts a .ass file with timestamps and adds a second text layer to each dialogue.
        This should only be used AFTER the timestampers have added their timestamps

    Args:
        fname (string): Full path to the .ass file WITHOUT the extension
        [out_fn] (string): Path to the output file to write to
    """
    if(not out_fn):
        out_fn = f"{fname}_processed.ass"

    with open (f"{fname}.ass", mode = 'r', encoding = 'UTF-8') as infile:
        processed_ass = infile.readlines()
    
    event_index = processed_ass.index("[Events]\n") + 2

    for i, event in enumerate(processed_ass[event_index:], event_index):
        if event.startswith("Dialogue"): #Let's ignore any lines that start with Comment, etc
            processed_ass[i] = generateLayer2(event)
        if event.isspace():
            break

    with open (out_fn, mode = 'w', encoding = 'UTF-8') as outfile:
        outfile.writelines(processed_ass)

    print(f"Successfully wrote Aegisfile to {out_fn}")


def main():
    input_fp = ""
    input_ext = ""

    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="Input .csv file or .ass file", default="", nargs='?')
    parser.add_argument("output_file", help="Output .ass file", default="", nargs='?')
    parser.add_argument("--style", "-s", help="Path to styles json file to use for parsing", default="./styles.json")
    args = parser.parse_intermixed_args()

    #If no input file is provided, use the file open dialogue to choose it
    if(not args.input_file):
        root = tk.Tk()
        root.withdraw()

        # Opens a dialog to ask for the file name using a directory search window
        # Change the . to the absolute/relative path
        # Or just delete the whole "initialdir='.'"
        # To open the file dialog in the root directory
        input_fp, input_ext = os.path.splitext(filedialog.askopenfilename(initialdir="."))
    else:
        input_fp, input_ext = os.path.splitext(args.input_file)


    with open(args.style, mode = 'r', encoding = 'UTF-8') as f:
        global STYLES
        STYLES = json.load(f)

    #If the file is a .csv, we run the preprocessing step to turn it into a .ass file
    if(input_ext == '.csv'):
        csvParser(input_fp, args.output_file)
    #If the file is a .ass file, we run postprocessing to add extra text layers
    elif(input_ext == '.ass'):
        postProcessParser(input_fp, args.output_file)
    else:
        print(f"Input file format {input_ext} is not recognized!")


if __name__ == "__main__":
    main()