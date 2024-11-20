from flask import Flask, render_template, request
import os
import math
import moviepy.editor as mp
import azure.cognitiveservices.speech as speechsdk
import json
import configparser

app = Flask(__name__)

# Load configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Load credentials from JSON file
with open(config['azure']['credentials_path'], 'r') as f:
    credentials = json.load(f)

AZURE_SPEECH_KEY = credentials['subscription_key']
AZURE_SPEECH_REGION = credentials['region']

# Create the upload folder if it doesn't exist
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def create_speech_recognizer(audio_path, language_code):
    """Create a speech recognizer with the given audio path and language."""
    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
        speech_config.speech_recognition_language = language_code
        audio_config = speechsdk.AudioConfig(filename=audio_path)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        return recognizer, None
    except Exception as e:
        return None, f"Error creating speech recognizer: {e}"

def transcribe_chunk_azure(audio_path, language_code):
    """Transcribe a chunk of audio using Azure Speech Service for the given language."""
    try:
        recognizer, error = create_speech_recognizer(audio_path, language_code)
        if recognizer is None:
            return error

        # Use 'recognize_once_async' for non-blocking transcription
        result = recognizer.recognize_once_async().get()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            return "No match found."
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speechsdk.CancellationDetails.from_result(result)
            return f"Speech Recognition canceled: {cancellation_details.reason}. Error: {cancellation_details.error_details}"
        else:
            return f"Speech recognition failed. Reason: {result.reason}"
    except Exception as e:
        return f"Error transcribing audio: {e}"

def extract_audio_from_video(video_path):
    """Extract audio from the video and return the audio path."""
    try:
        video = mp.VideoFileClip(video_path)
        audio_path = os.path.join(UPLOAD_FOLDER, "temp_audio.wav")
        video.audio.write_audiofile(audio_path, codec='pcm_s16le')  # Ensure PCM encoding
        return audio_path, None
    except Exception as e:
        return None, f"Error extracting audio from video: {e}"

def transcribe_audio_in_chunks(audio_path, chunk_length=30, language_code="en-US"):
    """Transcribe an audio file in chunks and return the full transcription with timestamps."""
    try:
        video = mp.AudioFileClip(audio_path)
        audio_duration = video.duration
        chunks = math.ceil(audio_duration / chunk_length)

        transcription = ""
        for i in range(chunks):
            start_time = i * chunk_length
            end_time = min((i + 1) * chunk_length, audio_duration)
            chunk_audio_path = os.path.join(UPLOAD_FOLDER, f"chunk_{i}.wav")

            # Extract the chunk and save it as a separate audio file
            video.subclip(start_time, end_time).write_audiofile(chunk_audio_path, codec='pcm_s16le')

            # Transcribe the chunk
            chunk_transcription = transcribe_chunk_azure(chunk_audio_path, language_code)
            formatted_start = format_timestamp(start_time)
            formatted_end = format_timestamp(end_time)

            # Format the transcription with timestamps
            transcription += f"[{formatted_start} - {formatted_end}] {chunk_transcription}\n"

            # Remove the temporary chunk file
            os.remove(chunk_audio_path)

        return transcription
    except Exception as e:
        return f"Error processing audio: {e}"

def format_timestamp(seconds):
    """Convert seconds to hh:mm:ss format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_transcribe', methods=['GET', 'POST'])
def video_transcribe():
    if request.method == 'POST':
        video_file = request.files.get('video_file')
        selected_language = request.form.get('language')  # Get the selected language from the form

        if video_file:
            video_path = os.path.join(UPLOAD_FOLDER, video_file.filename)
            video_file.save(video_path)

            # Pass the selected language to the transcription function
            transcription = transcribe_audio_in_chunks(video_path, language_code=selected_language)

            return render_template('video_transcribe.html', transcription=transcription, filename=video_file.filename)
        else:
            return render_template('video_transcribe.html', error="No video file uploaded.")
    return render_template('video_transcribe.html')

@app.route('/audio_transcribe', methods=['GET', 'POST'])
def audio_transcribe():
    if request.method == 'POST':
        audio_file = request.files.get('audio_file')
        selected_language = request.form.get('language')  # Get the selected language from the form

        if audio_file:
            audio_path = os.path.join(UPLOAD_FOLDER, audio_file.filename)
            audio_file.save(audio_path)

            # Pass the selected language to the transcription function
            transcription = transcribe_audio_in_chunks(audio_path, language_code=selected_language)

            return render_template('audio_transcribe.html', transcription=transcription, filename=audio_file.filename)
        else:
            return render_template('audio_transcribe.html', error="No audio file uploaded.")
    return render_template('audio_transcribe.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

if __name__ == '__main__':
    app.run(debug=True)
