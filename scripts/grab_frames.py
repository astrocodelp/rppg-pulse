import subprocess
import imageio_ffmpeg

ff = imageio_ffmpeg.get_ffmpeg_exe()
for t in (8, 30, 55, 70, 80):
    subprocess.run([ff, "-y", "-loglevel", "error", "-ss", str(t),
                    "-i", "demo_video/rppg_pulse_demo.mp4",
                    "-frames:v", "1", f"verify/frame_{t}.png"], check=True)
print("frames saved")
