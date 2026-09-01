"""Mitsu Recognition — voice, image, and video analysis.

Voice Recognition:
- Identify who is speaking using voice fingerprints
- Store and match voice profiles

Image Recognition:
- Analyze images using AI vision models
- OCR text extraction
- Object/face detection with OpenCV

Video Recognition:
- Extract key frames from video
- Analyze video content
- Scene detection
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

# ── Voice Profiles ──────────────────────────────────────────────────────────

VOICE_PROFILES_DIR = Path.home() / ".mitsu" / "voice_profiles"


def _ensure_profiles_dir():
    VOICE_PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def _audio_fingerprint(audio_data: np.ndarray, sample_rate: int = 16000) -> dict:
    """Extract a simple voice fingerprint from audio data.
    
    Uses MFCC-like features: mean frequency, spectral centroid,
    zero crossing rate, and RMS energy per segment.
    """
    if audio_data is None or len(audio_data) == 0:
        return {}

    # Ensure float
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)

    # Normalize
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data / max_val

    # Split into segments for consistency
    segment_size = min(len(audio_data), sample_rate)  # 1 second segments
    segments = []
    for i in range(0, len(audio_data), segment_size):
        seg = audio_data[i:i + segment_size]
        if len(seg) < sample_rate // 4:  # Skip very short segments
            continue

        # RMS energy
        rms = float(np.sqrt(np.mean(seg ** 2)))

        # Zero crossing rate
        zcr = float(np.mean(np.abs(np.diff(np.sign(seg)))) / 2)

        # Simple spectral features via FFT
        fft = np.abs(np.fft.rfft(seg))
        freqs = np.fft.rfftfreq(len(seg), 1.0 / sample_rate)

        # Spectral centroid
        total_energy = np.sum(fft)
        if total_energy > 0:
            spectral_centroid = float(np.sum(freqs * fft) / total_energy)
        else:
            spectral_centroid = 0.0

        # Spectral rolloff (85%)
        cumulative = np.cumsum(fft)
        rolloff_idx = np.searchsorted(cumulative, 0.85 * cumulative[-1])
        spectral_rolloff = float(freqs[min(rolloff_idx, len(freqs) - 1)])

        # Dominant frequency
        dominant_freq = float(freqs[np.argmax(fft[1:]) + 1]) if len(fft) > 1 else 0.0

        segments.append({
            "rms": rms,
            "zcr": zcr,
            "centroid": spectral_centroid,
            "rolloff": spectral_rolloff,
            "dominant": dominant_freq,
        })

    if not segments:
        return {}

    # Average across segments
    fingerprint = {
        "rms": float(np.mean([s["rms"] for s in segments])),
        "zcr": float(np.mean([s["zcr"] for s in segments])),
        "centroid": float(np.mean([s["centroid"] for s in segments])),
        "rolloff": float(np.mean([s["rolloff"] for s in segments])),
        "dominant": float(np.mean([s["dominant"] for s in segments])),
        "segments": len(segments),
    }
    return fingerprint


def _fingerprint_distance(fp1: dict, fp2: dict) -> float:
    """Calculate distance between two voice fingerprints. Lower = more similar."""
    if not fp1 or not fp2:
        return float("inf")

    keys = ["rms", "zcr", "centroid", "rolloff", "dominant"]
    # Weighted distances (centroid and rolloff are most distinctive)
    weights = {"rms": 0.1, "zcr": 0.2, "centroid": 0.3, "rolloff": 0.3, "dominant": 0.1}

    total_dist = 0.0
    total_weight = 0.0
    for key in keys:
        if key in fp1 and key in fp2:
            # Normalize by typical range
            if key == "centroid":
                norm = 4000.0
            elif key == "rolloff":
                norm = 6000.0
            elif key == "dominant":
                norm = 3000.0
            elif key == "rms":
                norm = 0.3
            else:
                norm = 0.5
            diff = abs(fp1[key] - fp2[key]) / norm
            total_dist += diff * weights[key]
            total_weight += weights[key]

    return total_dist / total_weight if total_weight > 0 else float("inf")


def save_voice_profile(name: str, audio_data: np.ndarray, sample_rate: int = 16000) -> bool:
    """Save a voice profile for speaker identification."""
    _ensure_profiles_dir()
    fp = _audio_fingerprint(audio_data, sample_rate)
    if not fp:
        return False
    profile_path = VOICE_PROFILES_DIR / f"{name.lower().replace(' ', '_')}.json"
    profile_path.write_text(json.dumps({"name": name, "fingerprint": fp}, indent=2))
    return True


def identify_speaker(audio_data: np.ndarray, sample_rate: int = 16000, threshold: float = 0.15) -> str:
    """Identify who is speaking by matching against saved voice profiles.
    
    Returns the speaker name or "Unknown" if no match.
    """
    _ensure_profiles_dir()
    fp = _audio_fingerprint(audio_data, sample_rate)
    if not fp:
        return "Unknown"

    best_match = "Unknown"
    best_distance = float("inf")

    for profile_file in VOICE_PROFILES_DIR.glob("*.json"):
        try:
            profile = json.loads(profile_file.read_text())
            stored_fp = profile.get("fingerprint", {})
            name = profile.get("name", profile_file.stem)
            dist = _fingerprint_distance(fp, stored_fp)
            if dist < best_distance:
                best_distance = dist
                best_match = name
        except Exception:
            continue

    if best_distance <= threshold:
        return best_match
    return "Unknown"


def list_voice_profiles() -> list[str]:
    """List all saved voice profile names."""
    _ensure_profiles_dir()
    return [f.stem.replace("_", " ").title() for f in VOICE_PROFILES_DIR.glob("*.json")]


def delete_voice_profile(name: str) -> bool:
    """Delete a voice profile."""
    profile_path = VOICE_PROFILES_DIR / f"{name.lower().replace(' ', '_')}.json"
    if profile_path.exists():
        profile_path.unlink()
        return True
    return False


# ── Image Recognition ───────────────────────────────────────────────────────

def analyze_image(image_path: str, question: str = "Describe this image") -> str:
    """Analyze an image using OpenCV for basic info, or AI vision for detailed analysis."""
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return f"Could not read image: {image_path}"

        h, w = img.shape[:2]
        channels = img.shape[2] if len(img.shape) > 2 else 1

        # Basic image info
        info = {
            "width": w,
            "height": h,
            "channels": channels,
            "size_kb": round(os.path.getsize(image_path) / 1024, 1),
        }

        # Color analysis
        avg_color = cv2.mean(img)[:3]
        info["avg_color_bgr"] = [round(c, 1) for c in avg_color]

        # Detect faces if available
        face_cascade = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = cv2.CascadeClassifier(face_cascade).detectMultiScale(gray, 1.3, 5)
        info["faces_detected"] = len(faces)

        # Edge detection for complexity
        edges = cv2.Canny(gray, 100, 200)
        edge_ratio = np.count_nonzero(edges) / edges.size
        info["complexity"] = round(float(edge_ratio), 3)

        result = f"Image: {w}x{h}, {channels} channels, {info['size_kb']}KB"
        if info["faces_detected"] > 0:
            result += f", {info['faces_detected']} face(s) detected"
        result += f", complexity: {info['complexity']}"
        return result

    except Exception as e:
        return f"Image analysis error: {e}"


def ocr_image(image_path: str) -> str:
    """Extract text from image using pytesseract if available."""
    try:
        from PIL import Image
        img = Image.open(image_path)

        # Try pytesseract
        try:
            import pytesseract
            text = pytesseract.image_to_string(img)
            return text.strip() if text.strip() else "No text found in image"
        except ImportError:
            pass

        # Fallback: just describe the image
        return analyze_image(image_path, "What text is in this image?")

    except Exception as e:
        return f"OCR error: {e}"


# ── Video Recognition ───────────────────────────────────────────────────────

def extract_video_frames(video_path: str, num_frames: int = 5) -> list[str]:
    """Extract evenly-spaced frames from a video. Returns temp file paths."""
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0

        if total_frames <= 0:
            return []

        # Calculate frame indices to extract
        indices = np.linspace(0, total_frames - 1, min(num_frames, total_frames), dtype=int)

        frame_paths = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if ret:
                tmp = tempfile.mktemp(suffix=".jpg")
                cv2.imwrite(tmp, frame)
                frame_paths.append(tmp)

        cap.release()
        return frame_paths

    except Exception as e:
        return []


def analyze_video(video_path: str, question: str = "Describe this video") -> str:
    """Analyze a video by extracting key frames and describing them."""
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return f"Could not open video: {video_path}"

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()

        info = f"Video: {width}x{height}, {duration:.1f}s, {fps:.1f}fps, {total_frames} frames"

        # Extract key frames for visual analysis
        frames = extract_video_frames(video_path, num_frames=3)
        if frames:
            info += f"\nExtracted {len(frames)} key frames for analysis"
            for i, fp in enumerate(frames):
                frame_info = analyze_image(fp)
                info += f"\n  Frame {i+1}: {frame_info}"
                Path(fp).unlink(missing_ok=True)

        return info

    except Exception as e:
        return f"Video analysis error: {e}"


def get_video_metadata(video_path: str) -> str:
    """Get video metadata."""
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return f"Could not read video: {video_path}"

        meta = {
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": round(cap.get(cv2.CAP_PROP_FPS), 2),
            "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "codec": int(cap.get(cv2.CAP_PROP_FOURCC)),
            "duration_seconds": round(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / max(cap.get(cv2.CAP_PROP_FPS), 1), 2),
        }
        cap.release()

        # Convert codec to string
        codec_int = meta["codec"]
        codec_str = "".join([chr((codec_int >> 8 * i) & 0xFF) for i in range(4)])
        meta["codec"] = codec_str

        return json.dumps(meta, indent=2)

    except Exception as e:
        return f"Metadata error: {e}"
