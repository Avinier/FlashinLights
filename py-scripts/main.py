import pyaudio
import numpy as np

import serial
import time

# Constants
FORMAT = pyaudio.paInt16  # Audio format (16-bit PCM)
CHANNELS = 1  # Number of audio channels (1 for mono, 2 for stereo)
RATE = 44100  # Sample rate (samples per second)
CHUNK_SIZE = 1024  # Number of frames per buffer

# Initialize PyAudio
p = pyaudio.PyAudio()

# Initialize PySerial for communication with Arduino
ser = serial.Serial('COM3', 9600)
time.sleep(2)

# Open a stream for microphone input
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE)

print("Listening...")

def beat_detect(audio, sample_rate):
    audio_fft = np.abs((np.fft.fft(audio)[0:int(len(audio) / 2)]) / len(audio))
    freqs = np.fft.fftfreq(len(audio), 1/sample_rate)[:len(audio)//2]

    # Frequency Ranges for each important audio group (adjust the ranges based on your preferences)
    sub_bass_indices = np.where((freqs >= 20) & (freqs <= 60))[0]
    bass_indices = np.where((freqs >= 60) & (freqs <= 250))[0]
    low_midrange_indices = np.where((freqs >= 250) & (freqs <= 500))[0]
    midrange_indices = np.where((freqs >= 500) & (freqs <= 2000))[0]
    upper_midrange_indices = np.where((freqs >= 2000) & (freqs <= 4000))[0]
    presence_indices = np.where((freqs >= 4000) & (freqs <= 6000))[0]
    brilliance_indices = np.where((freqs >= 6000) & (freqs <= 20000))[0]

    sub_bass = np.max(audio_fft[sub_bass_indices])
    bass = np.max(audio_fft[bass_indices])
    low_midrange = np.max(audio_fft[low_midrange_indices])
    midrange = np.max(audio_fft[midrange_indices])
    upper_midrange = np.max(audio_fft[upper_midrange_indices])
    presence = np.max(audio_fft[presence_indices])
    brilliance = np.max(audio_fft[brilliance_indices])

    global sub_bass_max, bass_max, low_midrange_max, midrange_max, upper_midrange_max, presence_max, brilliance_max
    global sub_bass_beat, bass_beat, low_midrange_beat, midrange_beat, upper_midrange_beat, presence_beat, brilliance_beat
    sub_bass_max = max(sub_bass_max, sub_bass)
    bass_max = max(bass_max, bass)
    low_midrange_max = max(low_midrange_max, low_midrange)
    midrange_max = max(midrange_max, midrange)
    upper_midrange_max = max(upper_midrange_max, upper_midrange)
    presence_max = max(presence_max, presence)
    brilliance_max = max(brilliance_max, brilliance)

    if sub_bass >= sub_bass_max * 0.9 and not sub_bass_beat:
        sub_bass_beat = True
        print("Sub Bass Beat: ", sub_bass)
    elif sub_bass < sub_bass_max * 0.3:
        sub_bass_beat = False

    if bass >= bass_max * 0.9 and not bass_beat:
        bass_beat = True
        print("Bass Beat: ", bass_beat)
    elif bass < bass_max * 0.3:
        bass_beat = False

    if low_midrange >= low_midrange_max * 0.9 and not low_midrange_beat:
        low_midrange_beat = True
        print("Low Midrange Beat: ", low_midrange)
    elif low_midrange < low_midrange_max * 0.3:
        low_midrange_beat = False

    if midrange >= midrange_max * 0.9 and not midrange_beat:
        midrange_beat = True
        print("Midrange Beat: ", midrange)
    elif midrange < midrange_max * 0.3:
        midrange_beat = False

    if upper_midrange >= upper_midrange_max * 0.9 and not upper_midrange_beat:
        upper_midrange_beat = True
        print("Upper Midrange Beat: ", upper_midrange)
    elif upper_midrange < upper_midrange_max * 0.3:
        upper_midrange_beat = False

    if presence >= presence_max * 0.9 and not presence_beat:
        presence_beat = True
        print("Presence Beat: ", presence)
    elif presence < presence_max * 0.3:
        presence_beat = False

    if brilliance >= brilliance_max * 0.9 and not brilliance_beat:
        brilliance_beat = True
        print("Brilliance Beat: ", brilliance)
    elif brilliance < brilliance_max * 0.3:
        brilliance_beat = False

    primary_freq = freqs[np.argmax(audio_fft)]
    print("Primary Frequency: ", primary_freq)

def scale_to_byte(value):
    # Scale the value to the 0-255 range
    return int((value / sub_bass_max) * 255)

try:
    while True:
        # Read audio data from the stream
        data = stream.read(CHUNK_SIZE)

        # Convert the binary data to a NumPy array
        audio_array = np.frombuffer(data, dtype=np.int16)

        sub_bass_max = bass_max = low_midrange_max = midrange_max = upper_midrange_max = presence_max = brilliance_max = 0
        sub_bass_beat = bass_beat = low_midrange_beat = midrange_beat = upper_midrange_beat = presence_beat = brilliance_beat = False

        beat_detect(audio_array, RATE)

        sub_bass_value = scale_to_byte(sub_bass_beat)
        bass_value = scale_to_byte(bass_beat)
        low_midrange_value = scale_to_byte(low_midrange_beat)
        midrange_value = scale_to_byte(midrange_beat)
        upper_midrange_value = scale_to_byte(upper_midrange_beat)
        presence_value = scale_to_byte(presence_beat)
        brilliance_value = scale_to_byte(brilliance_beat)

        # Create a string with scaled beat values
        beat_info = f"SubBass:{sub_bass_value};Bass:{bass_value};LowMidrange:{low_midrange_value};Midrange:{midrange_value};UpperMidrange:{upper_midrange_value};Presence:{presence_value};Brilliance:{brilliance_value}"

        # Send the string to Arduino
        ser.write(beat_info.encode())

except KeyboardInterrupt:
    # Stop the stream and close the PyAudio instance when interrupted
    print("Stopping...")
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Stream closed.")
