<<<<<<< HEAD
# NEW EXPERIMENT: AUTO-MOTION Arm Studio (curl + tricep pushdown)

**This branch's `main.py` now runs a right-arm bicep-curl / tricep-pushdown
prototype**, not the original shoulder-press demonstration described below.
It includes a redesigned live webcam dashboard, right-arm joint metrics,
repetition tracking, and updated Arduino OLED packets.

Start on Mac: `.venv/bin/python main.py --exercise curl --side right --camera 0`
(or `--exercise pushdown`). **1** = curl, **2** = pushdown, **C** = calibrate,
**R** = reset reps, **Q** = quit. For improved tracking use `--debug-tracking`; an optional `--model full` is also supported (see setup guide). See [`docs/ARM_STUDIO_SETUP.md`](docs/ARM_STUDIO_SETUP.md)
for full setup, model and Arduino instructions, experimental thresholds,
and important limits on real-world accuracy.

---

# AUTO-MOTION Tuesday Starter Kit — ECE 198
=======
Automotion and FROM-PAL Integration. This GitHub is mostly for Automotion, as Graham made the FROM-PAL separately. 
>>>>>>> origin/main

Roles:
Karthik: coverting what the camera saw into good form, bad form, etc.
Manbir: operating and measuring things with the AI camera
Rivan: taking the good form, bad form, etc. from Karthik's code and displaying it into the OLED. 

Graham: did FROM-PAL
