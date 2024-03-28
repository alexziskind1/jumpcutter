from pytube import YouTube
import subprocess
from scipy.io import wavfile
import numpy as np
import os
import argparse
import math

# Downloads a video from YouTube and renames it to avoid spaces in the filename
def downloadFile(url):
    name = YouTube(url).streams.first().download()
    newname = name.replace(' ', '_')
    os.rename(name, newname)
    return newname

# Calculates the maximum volume within a given audio sample
def getMaxVolume(s):
    maxv = float(np.max(s))
    minv = float(np.min(s))
    return max(maxv, -minv)

# Creates a directory for temporary files
def createPath(s):
    try:
        if not os.path.exists(s):
            os.mkdir(s)
    except OSError:
        print(f"Creation of the directory {s} failed.")
        exit(1)

# Deletes the directory used for temporary files
def deletePath(s):
    try:
        if os.path.exists(s):
            for root, dirs, files in os.walk(s, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(s)
    except OSError as e:
        print(f"Deletion of the directory {s} failed: {e.strerror}")

# Main function to process the video
def main(input_file, output_file_base, silent_threshold, frame_rate, frame_quality):
    TEMP_FOLDER = "TEMP"
    createPath(TEMP_FOLDER)

    # Extract audio from the video
    command = f"ffmpeg -i \"{input_file}\" -q:a 0 -map a {TEMP_FOLDER}/audio.wav -y"
    subprocess.call(command, shell=True)

    # Read the audio data
    try:
        sampleRate, audioData = wavfile.read(f"{TEMP_FOLDER}/audio.wav")
    except FileNotFoundError:
        print(f"Error: {TEMP_FOLDER}/audio.wav not found. Check if the ffmpeg command executed correctly.")
        exit(1)

    maxAudioVolume = getMaxVolume(audioData)

    samplesPerFrame = sampleRate / frame_rate
    audioFrameCount = int(math.ceil(len(audioData) / samplesPerFrame))

    hasLoudAudio = np.zeros((audioFrameCount))

    for i in range(audioFrameCount):
        start = int(i * samplesPerFrame)
        end = min(int((i + 1) * samplesPerFrame), len(audioData))
        audioChunk = audioData[start:end]
        maxChunkVolume = getMaxVolume(audioChunk) / maxAudioVolume
        if maxChunkVolume >= silent_threshold:
            hasLoudAudio[i] = 1

    chunks = [[0, 0, 0]]
    for i in range(1, len(hasLoudAudio)):
        if hasLoudAudio[i] != hasLoudAudio[i - 1]:
            chunks.append([chunks[-1][1], i, hasLoudAudio[i - 1]])
    chunks.append([chunks[-1][1], audioFrameCount, hasLoudAudio[-1]])
    chunks = chunks[1:]

    for i, chunk in enumerate(chunks):
        if chunk[2]:
            start_time = chunk[0] / frame_rate
            end_time = chunk[1] / frame_rate
            output_file = f"{output_file_base}_segment_{i}.mp4"
            #command = f"ffmpeg -i \"{input_file}\" -ss {start_time} -to {end_time} -c copy \"{output_file}\" -y"
            #command = f"ffmpeg -i \"{input_file}\" -ss {start_time} -to {end_time} -c copy -copyts \"{output_file}\" -y"
            command = f"ffmpeg -i \"{input_file}\" -ss {start_time} -to {end_time} -c:v libx264 -c:a aac \"{output_file}\" -y"


            subprocess.call(command, shell=True)

    deletePath(TEMP_FOLDER)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exports segments of a video where audio is detected into separate files.")
    parser.add_argument('--input_file', type=str, required=True, help="The video file you want to process")
    parser.add_argument('--output_file_base', type=str, required=True, help="Base name for the output files")
    parser.add_argument('--silent_threshold', type=float, default=0.03, help="The volume threshold under which audio is considered silent")
    parser.add_argument('--frame_rate', type=float, default=30, help="Frame rate of the video")
    parser.add_argument('--frame_quality', type=int, default=3, help="Quality of frames to be extracted. 1 is highest, 31 is lowest")

    args = parser.parse_args()

    main(args.input_file, args.output_file_base, args.silent_threshold, args.frame_rate, args.frame_quality)
