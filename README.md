# Dialed - Study Session Distraction Classifier

An ML-powered desktop application that detects when you're distracted during study sessions and automatically blurs your screen to help you refocus.

**Tech Stack:** Python, MediaPipe, OpenCV, FastAPI, Chrome Extension, LightGBM

## Project Goal

Classify focused vs distracted states using:
- **Webcam gaze tracking** (eye position, blink rate, head pose)
- **Browser activity** (active tabs, keypress rate, idle state)
- **Self-labeled focus scores** for training

Target: ROC-AUC ≥0.80, F1 ≥0.75

---

## Quick Start

### 1. Install Dependencies

```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Install Python packages
pip install -r requirements.txt
```

### 2. Run All Services

```bash
python run_all.py
```

This starts:
- FastAPI backend on http://localhost:8000
- Gaze tracking service (webcam)
- Label service (keyboard shortcuts)

### 3. Install Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle top-right)
3. Click "Load unpacked"
4. Select the `chrome-extension/` folder
5. Extension should appear in your toolbar

### 4. Start Collecting Data

**Label your focus state:**
- Press `Ctrl+Shift+F` when you're **focused**
- Press `Ctrl+Shift+D` when you're **distracted**

**Goal:** Collect at least one week of data (~2,000 labeled windows) before training.

---

## Project Structure

```
dialed/
├── backend/
│   ├── app.py              # FastAPI server
│   ├── database.py         # SQLite interface
│   └── __init__.py
├── services/
│   ├── gaze_service.py     # Webcam gaze tracking
│   └── label_service.py    # Keyboard shortcut listener
├── chrome-extension/
│   ├── manifest.json       # Extension config
│   ├── background.js       # Tab tracking
│   ├── content.js          # Keypress counting
│   └── popup.html          # Status popup
├── features/               # (TODO: Phase 2)
│   └── compute_features.py
├── models/                 # (TODO: Phase 3)
│   ├── train.py
│   └── evaluate.py
├── electron-app/           # (TODO: Phase 4)
├── data.db                 # SQLite database
├── requirements.txt
└── run_all.py             # Master launcher
```

---

## Components

### 1. Gaze Service ([services/gaze_service.py](services/gaze_service.py))

Tracks your face via webcam at 5-10 fps:

- Eye off-center ratio
- Blink frequency
- Head pitch/yaw
- Head distance from camera

**Run standalone:**
```bash
python services/gaze_service.py --fps 8 --preview
```

**Performance:** <25% CPU, <200MB RAM

### 2. Label Service ([services/label_service.py](services/label_service.py))

Background keyboard listener for self-labeling:

- `Ctrl+Shift+D` = Distracted
- `Ctrl+Shift+F` = Focused

**Run standalone:**
```bash
python services/label_service.py
```

### 3. Browser Tracker (Chrome Extension)

Logs every 2 seconds:
- Active tab domain and title
- Keypress count
- Idle state

**Privacy:** All data stays on localhost, nothing sent externally.

### 4. FastAPI Backend ([backend/app.py](backend/app.py))

HTTP API for data logging and predictions.

**Key endpoints:**
- `POST /log/tab` - Log browser activity
- `POST /log/gaze` - Log gaze data
- `POST /log/label` - Log focus labels
- `GET /stats` - Database statistics
- `POST /predict` - Get distraction probability (future)

**Run standalone:**
```bash
python backend/app.py
```

API docs: http://localhost:8000/docs

---

## Development Phases

### ✅ Phase 1: Data Collection (Current)

- [x] Webcam capture service
- [x] Browser context logger
- [x] Self-label shortcuts
- [x] SQLite database
- [ ] Collect 1 week of labeled data

### Phase 2: Feature Pipeline

- [ ] Compute 30s rolling window features
- [ ] One-hot encode top 30 domains
- [ ] Generate features.csv with ~2,000 rows

### Phase 3: Model Training

- [ ] Baseline heuristic classifier
- [ ] Train LightGBM model
- [ ] Achieve ROC-AUC ≥0.80

### Phase 4: Real-Time Stack

- [ ] Electron desktop app
- [ ] Screen blur overlay
- [ ] Tray icon (green/red focus indicator)

### Phase 5: Polish

- [ ] Cross-platform builds (dmg, exe, AppImage)
- [ ] Settings UI
- [ ] Daily focus report CSV export

---

## Database Schema

**gaze_logs:**
- timestamp, eye_off_center, blink, head_pitch, head_yaw, head_distance

**tab_logs:**
- timestamp, domain, title, idle_state, keypress_count

**labels:**
- timestamp, label (distracted/focused)

**View stats:**
```bash
python -c "from backend.database import get_stats; print(get_stats())"
```

---

## Troubleshooting

**Webcam not working:**
```bash
# Test camera access
python cam_test.py
```

**Backend not connecting:**
- Check http://localhost:8000/health
- Make sure no other service is using port 8000

**Chrome extension not logging:**
- Click extension icon to check backend status
- View extension console: `chrome://extensions/` → Details → Inspect views: background page

**Keyboard shortcuts not working:**
- Check if label service is running
- Try running: `python services/label_service.py` standalone

---

## Data Privacy

- All data is stored locally in `data.db`
- No external network requests
- Webcam frames are processed and discarded immediately (only landmarks stored)
- You can disable webcam tracking anytime

---

## Next Steps

1. **Collect data for 1 week** - Use the app during study sessions
2. **Label frequently** - Try to label every few minutes
3. **Aim for balance** - Get roughly equal focused/distracted labels
4. **Check stats daily:**
   ```bash
   curl http://localhost:8000/stats
   ```

Once you have ~2,000 labeled data points, we'll move to Phase 2: Feature Engineering!

---

## Contributing

This is a portfolio project. Feel free to fork and adapt for your own use case.

## License

MIT