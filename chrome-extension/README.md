# Dialed Chrome Extension

Browser activity tracker for the Dialed study-session distraction classifier.

## Installation

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select this `chrome-extension` folder
5. The extension icon should appear in your toolbar

## What it tracks

- Active tab domain and title (every 2 seconds)
- Keyboard activity (keypress count)
- Idle state (active, idle, or locked)

## Data Privacy

- All data is sent to `http://localhost:8000` only
- Nothing is sent to external servers
- You can disable the extension anytime from `chrome://extensions/`

## Backend Setup

The extension requires the FastAPI backend to be running:

```bash
python backend/app.py
```

If the backend is not running, the extension will fail silently.

## Testing

Click the extension icon to see connection status.
