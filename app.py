import os
import sys
import cv2
import numpy as np
from moviepy.editor import *
from elevenlabs import generate, set_api_key
import stable_whisper as whisper

# --- CONFIGURATION ---

ELEVENLABS_API_KEY = "ELEVEN_LABS_API_KEY" # Replace with your API key
INPUT_TEXT_FILE = "script.txt"
INPUT_BACKGROUND_FILE = "background.jpg"

# Final output video
OUTPUT_VIDEO_FILE = "final_short.mp4"
# Temporary files that will be created and then deleted
TEMP_SILENT_VIDEO_FILE = "temp_silent_video.mp4"
TEMP_SUBTITLED_VIDEO_FILE = "temp_subtitled_video.mp4"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 24
VOICE_NAME = "Jessica"  # Make sure this voice is in your ElevenLabs VoiceLab

# --- OPENCV FONT CONFIGURATION ---
FONT = cv2.FONT_HERSHEY_SCRIPT_COMPLEX
FONT_SIZE = 2.5
FONT_COLOR = (255, 255, 255)  # White (in BGR format for OpenCV)
FONT_THICKNESS = 3
SHADOW_COLOR = (0, 0, 0) # Black for outline/shadow
SHADOW_THICKNESS = 6

# --- SCRIPT LOGIC ---

def generate_narration(text, output_path="narration.mp3"):
    print("🎙️ Generating narration...")
    try:
        set_api_key(ELEVENLABS_API_KEY)
        audio = generate(text=text, voice=VOICE_NAME, model="eleven_multilingual_v2")
        with open(output_path, "wb") as f: f.write(audio)
        return output_path
    except Exception as e:
        print(f"🛑 Error during narration generation: {e}"); sys.exit(1)

def create_silent_base_video(duration, background_path, output_path):
    """Creates a SILENT video of the correct duration."""
    print("🎬 Creating silent base video...")
    background_clip = ImageClip(background_path).set_duration(duration)
    
    (w, h) = background_clip.size
    target_aspect = VIDEO_WIDTH / VIDEO_HEIGHT
    if (w / h) > target_aspect:
        background_clip = background_clip.crop(x_center=w/2, width=int(h * target_aspect))
    else:
        background_clip = background_clip.crop(y_center=h/2, height=int(w / target_aspect))
        
    background_clip = background_clip.resize(height=VIDEO_HEIGHT)
    
    background_clip.write_videofile(output_path, codec='libx264', fps=FPS, logger=None)
    print("   ✓ Silent base video created successfully.")

def get_word_timestamps(audio_path):
    print("✍️ Generating word timestamps...")
    model = whisper.load_model('base')
    result = model.transcribe(audio_path, regroup=False)
    word_info = [{'word': w.word.strip().upper(), 'start': w.start, 'end': w.end} for s in result.segments for w in s.words]
    print(f"   ✓ Found {len(word_info)} words.")
    return word_info

def draw_subtitles_on_video(input_video, output_video, word_timestamps):
    print("✏️ Drawing subtitles onto video using OpenCV...")
    video_capture = cv2.VideoCapture(input_video)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(output_video, fourcc, FPS, (VIDEO_WIDTH, VIDEO_HEIGHT))

    frame_count = 0
    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret: break
        current_time = frame_count / FPS
        active_word = None
        for word in word_timestamps:
            if word['start'] <= current_time < word['end']:
                active_word = word['word']
                break
        if active_word:
            text_size, _ = cv2.getTextSize(active_word, FONT, FONT_SIZE, FONT_THICKNESS)
            text_x = (VIDEO_WIDTH - text_size[0]) // 2
            text_y = (VIDEO_HEIGHT + text_size[1]) // 2
            cv2.putText(frame, active_word, (text_x, text_y), FONT, FONT_SIZE, SHADOW_COLOR, SHADOW_THICKNESS, cv2.LINE_AA)
            cv2.putText(frame, active_word, (text_x, text_y), FONT, FONT_SIZE, FONT_COLOR, FONT_THICKNESS, cv2.LINE_AA)
        video_writer.write(frame)
        frame_count += 1
    
    video_capture.release()
    video_writer.release()
    print("   ✓ Subtitles drawn successfully.")

def main():
    print("--- 🎬 Starting YouTube Shorts Generator (OpenCV Edition) ---")
    if ELEVENLABS_API_KEY == "YOUR_ELEVENLABS_API_KEY": sys.exit("🛑 Set API Key")
    
    # Step 1: Generate Narration
    with open(INPUT_TEXT_FILE, 'r', encoding='utf-8') as f: script_text = f.read()
    narration_audio_path = generate_narration(script_text)
    narration_duration = AudioFileClip(narration_audio_path).duration
    
    # Step 2: Create a temporary SILENT video with the background
    create_silent_base_video(narration_duration, INPUT_BACKGROUND_FILE, TEMP_SILENT_VIDEO_FILE)
    
    # Step 3: Get the word timestamps
    word_timestamps = get_word_timestamps(narration_audio_path)
    
    # Step 4: Use OpenCV to draw subtitles on the silent video
    draw_subtitles_on_video(TEMP_SILENT_VIDEO_FILE, TEMP_SUBTITLED_VIDEO_FILE, word_timestamps)

    # Step 5: THE FINAL ASSEMBLY - Combine the subtitled video with the original audio
    print("🔊 Combining final video and audio...")
    subtitled_clip = VideoFileClip(TEMP_SUBTITLED_VIDEO_FILE)
    original_audio = AudioFileClip(narration_audio_path)
    final_video = subtitled_clip.set_audio(original_audio)
    final_video.write_videofile(OUTPUT_VIDEO_FILE, codec='libx264', audio_codec='aac', fps=FPS, logger='bar')
    print("   ✓ Final video and audio combined successfully.")

    # Step 6: Cleanup  temporary files
    print("🧹 Cleaning up temporary files...")
    if os.path.exists(narration_audio_path): os.remove(narration_audio_path)
    if os.path.exists(TEMP_SILENT_VIDEO_FILE): os.remove(TEMP_SILENT_VIDEO_FILE)
    if os.path.exists(TEMP_SUBTITLED_VIDEO_FILE): os.remove(TEMP_SUBTITLED_VIDEO_FILE)

    print(f"\n--- ✅ VICTORY AT LAST! Your video is ready: {OUTPUT_VIDEO_FILE} ---")

if __name__ == "__main__":
    main()