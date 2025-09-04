import os
from flask import Flask, render_template, request, send_from_directory, jsonify
import cv2
import numpy as np
from moviepy import VideoFileClip

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, "static", "uploads")
OUTPUT_FOLDER = os.path.join(APP_ROOT, "static", "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 600  # ~600MB limit (adjust as needed)


def cartoonize_frame(img):
    """
    Simple cartoon effect:
    - bilateral filter for smoothing while keeping edges
    - edge detection via median blur + adaptive threshold
    - combine color and edge mask
    """
    # Convert to smaller size for speed? (skip here to preserve quality)
    # 1) Apply bilateral filter multiple times
    color = img.copy()
    for _ in range(2):
        color = cv2.bilateralFilter(color, d=9, sigmaColor=75, sigmaSpace=75)

    # 2) Convert to grayscale and apply median blur
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.medianBlur(gray, 7)

    # 3) Edge detection (adaptive threshold)
    edges = cv2.adaptiveThreshold(gray_blur, 255,
                                  cv2.ADAPTIVE_THRESH_MEAN_C,
                                  cv2.THRESH_BINARY, blockSize=9, C=2)

    # 4) Convert edges to color and bitwise-and with color image
    edges_color = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    cartoon = cv2.bitwise_and(color, edges_color)

    # Optional: enhance colors a bit (increase saturation)
    hsv = cv2.cvtColor(cartoon, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    s = cv2.add(s, 15)  # increase saturation
    final_hsv = cv2.merge((h, s, v))
    cartoon = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
    return cartoon


def process_video(input_path, output_path):
    """Read video, process frame-by-frame, and write output."""
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError("Could not open input video.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # mp4
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Process the frame
        cartoon = cartoonize_frame(frame)
        out.write(cartoon)
        idx += 1

    cap.release()
    out.release()

    # Optional: re-encode with moviepy to ensure proper mp4 container / audio kept
    try:
        clip = VideoFileClip(output_path)
        # If input had audio, try to preserve from original input
        # But MoviePy will re-encode the existing video if needed
        clip.write_videofile(output_path.replace(".mp4", "_final.mp4"),
                             codec="libx264", audio_codec="aac", verbose=False, logger=None)
        clip.close()
        # Replace output path
        os.remove(output_path)
        os.rename(output_path.replace(".mp4", "_final.mp4"), output_path)
    except Exception:
        # If re-encoding fails, keep the raw OpenCV output.
        pass

    return output_path


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("video")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = file.filename
    # sanitize filename loosely
    base, ext = os.path.splitext(filename)
    safe_base = "".join(c for c in base if c.isalnum() or c in (" ", "_", "-")).rstrip()
    ext = ext if ext else ".mp4"
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{safe_base}{ext}")
    file.save(upload_path)

    output_name = f"{safe_base}_cartoon.mp4"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_name)

    try:
        processed = process_video(upload_path, output_path)
    except Exception as e:
        return jsonify({"error": "Processing failed", "details": str(e)}), 500

    # Return URL to processed file
    url = f"/static/outputs/{os.path.basename(processed)}"
    return jsonify({"success": True, "url": url})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
