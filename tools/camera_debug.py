from camera import Camera
import cv2
import os
import time
from PIL import Image

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def _save_png(name, arr):
    path = os.path.join(OUT_DIR, name)
    try:
        img = Image.fromarray(arr)
        img.save(path)
        print('WROTE', path)
    except Exception as e:
        print('ERR save', path, e)


def main():
    cam = Camera()
    try:
        cam.start()
    except Exception as e:
        print('No se pudo iniciar cam.start():', e)
        return

    # Try to get raw sample from backend if available
    raw = None
    try:
        if getattr(cam, 'backend', None) == 'picamera2' and hasattr(cam, 'cap'):
            try:
                raw = cam.cap.capture_array()
            except Exception as e:
                print('cap.capture_array() failed:', e)
        else:
            # Try direct opencv capture
            cap = cv2.VideoCapture(0)
            ok, frm = cap.read()
            cap.release()
            if ok:
                raw = frm
    except Exception as e:
        print('Error leyendo raw:', e)

    read_frame = None
    try:
        read_frame = cam.read()
    except Exception as e:
        print('cam.read() failed:', e)

    # Simulate the conversion that main_view does (BGR->RGB)
    sim_display = None
    if read_frame is not None:
        try:
            sim_display = cv2.cvtColor(read_frame, cv2.COLOR_BGR2RGB)
        except Exception:
            try:
                sim_display = read_frame[..., ::-1]
            except Exception:
                sim_display = None

    # Save files (multiple variants to let you inspect)
    if raw is not None:
        # If Picamera2, raw is likely RGB
        if getattr(cam, 'backend', None) == 'picamera2':
            _save_png('debug_sample_raw_asrgb.png', raw)
            _save_png('debug_sample_raw_assumedbgr.png', raw[..., ::-1])
        else:
            _save_png('debug_sample_raw_assumedbgr.png', raw)
            _save_png('debug_sample_raw_assumedrgb.png', raw[..., ::-1])

    if read_frame is not None:
        _save_png('debug_camera_read_asreported.png', read_frame)
        try:
            _save_png('debug_camera_read_swapped.png', read_frame[..., ::-1])
        except Exception:
            pass

    if sim_display is not None:
        _save_png('debug_sim_display.png', sim_display)

    print('Done. Revisa las imágenes en el directorio del proyecto:')
    for fn in [
        'debug_sample_raw_asrgb.png', 'debug_sample_raw_assumedbgr.png',
        'debug_camera_read_asreported.png', 'debug_camera_read_swapped.png', 'debug_sim_display.png']:
        p = os.path.join(OUT_DIR, fn)
        if os.path.exists(p):
            print('-', p)

    cam.stop()

if __name__ == '__main__':
    main()
