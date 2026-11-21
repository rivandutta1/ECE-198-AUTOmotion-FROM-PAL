
Python 3.11.x	
Visual Studio Code	
Python Extension (Microsoft)	
MediaPipe Pose Landmarker Lite model	
MediaPipe Model

VS Code and its extension are recommended for development, but aren't strictly necessary to run the program. macOS Terminal works too.
Python libraries to install
They also need these Python packages:
- MediaPipe — AI body landmark detection.
- OpenCV — Webcam capture, processing, and visualization.
- NumPy — Numerical operations.
- pySerial — Communication with Arduino (for eventual hardware integration).
- pytest — Automated testing (not required for normal operation).
They can install the dependencies using the project's requirements.txt:

put 
python main.py -help
to start program 