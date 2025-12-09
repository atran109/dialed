"""
Keyboard shortcut service for self-labeling focus state.
Ctrl+Shift+D = Distracted
Ctrl+Shift+F = Focused
"""

import sys
import os
import time
import signal
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from backend.database import insert_label, init_db, get_stats


class LabelService:
    """Service for capturing user-provided focus labels via keyboard shortcuts."""

    def __init__(self):
        """Initialize label service."""
        self.running = False
        self.current_keys = set()

        # Define shortcuts
        self.DISTRACTED_COMBO = {Key.ctrl_l, Key.shift_l, KeyCode.from_char('d')}
        self.FOCUSED_COMBO = {Key.ctrl_l, Key.shift_l, KeyCode.from_char('f')}

        # Alternative combos (right ctrl/shift)
        self.DISTRACTED_COMBO_R = {Key.ctrl_r, Key.shift_r, KeyCode.from_char('d')}
        self.FOCUSED_COMBO_R = {Key.ctrl_r, Key.shift_r, KeyCode.from_char('f')}

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Stats tracking
        self.distracted_count = 0
        self.focused_count = 0

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("\nReceived shutdown signal, stopping service...")
        self.stop()
        sys.exit(0)

    def _show_notification(self, label: str):
        """
        Show desktop notification (cross-platform).
        Falls back to console print if notifications unavailable.
        """
        message = f"Label recorded: {label.upper()}"

        # Try to use system notifications
        try:
            if sys.platform == "darwin":  # macOS
                os.system(f"""
                    osascript -e 'display notification "{message}" with title "Dialed"'
                """)
            elif sys.platform == "win32":  # Windows
                # Could use win10toast library here
                print(f"[NOTIFICATION] {message}")
            else:  # Linux
                os.system(f'notify-send "Dialed" "{message}"')
        except Exception:
            # Fallback to console
            print(f"[NOTIFICATION] {message}")

    def _record_label(self, label: str):
        """Record a label to the database."""
        try:
            timestamp = time.time()
            insert_label(timestamp, label)

            if label == "distracted":
                self.distracted_count += 1
            else:
                self.focused_count += 1

            print(f"\n[{time.strftime('%H:%M:%S')}] Label: {label.upper()} "
                  f"(D:{self.distracted_count} F:{self.focused_count})")

            self._show_notification(label)

        except Exception as e:
            print(f"ERROR recording label: {e}")

    def _check_combo(self, current_keys: set) -> bool:
        """Check if current keys match any shortcut combo."""
        # Normalize keys (handle both left and right modifiers)
        normalized = set()
        for key in current_keys:
            if key in [Key.ctrl_l, Key.ctrl_r]:
                normalized.add(Key.ctrl_l)
            elif key in [Key.shift_l, Key.shift_r]:
                normalized.add(Key.shift_l)
            else:
                normalized.add(key)

        # Check for distracted combo
        distracted_combo = {Key.ctrl_l, Key.shift_l, KeyCode.from_char('d')}
        if normalized == distracted_combo:
            return 'distracted'

        # Check for focused combo
        focused_combo = {Key.ctrl_l, Key.shift_l, KeyCode.from_char('f')}
        if normalized == focused_combo:
            return 'focused'

        return None

    def _on_press(self, key):
        """Handle key press events."""
        try:
            # Add key to current set
            self.current_keys.add(key)

            # Check if we have a matching combo
            label = self._check_combo(self.current_keys)
            if label:
                self._record_label(label)

        except Exception as e:
            print(f"Error in key press handler: {e}")

    def _on_release(self, key):
        """Handle key release events."""
        try:
            # Remove key from current set
            self.current_keys.discard(key)
        except Exception as e:
            print(f"Error in key release handler: {e}")

    def start(self):
        """Start the label service."""
        print("Starting label service...")
        print("\nKeyboard shortcuts:")
        print("  Ctrl+Shift+D = Distracted")
        print("  Ctrl+Shift+F = Focused")
        print("\nPress Ctrl+C to stop.\n")

        # Initialize database
        init_db()

        # Load existing stats
        stats = get_stats()
        if 'label_breakdown' in stats:
            self.distracted_count = stats['label_breakdown'].get('distracted', 0)
            self.focused_count = stats['label_breakdown'].get('focused', 0)
            print(f"Existing labels: D:{self.distracted_count} F:{self.focused_count}\n")

        self.running = True

        # Start keyboard listener
        with keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release) as listener:

            print("Service started. Listening for keyboard shortcuts...")

            try:
                listener.join()
            except KeyboardInterrupt:
                pass

        self.stop()

    def stop(self):
        """Stop the label service."""
        if not self.running:
            return

        print("\nStopping label service...")
        self.running = False

        print(f"Session stats: {self.distracted_count} distracted, {self.focused_count} focused")
        print("Service stopped successfully")


def main():
    """Run label service from command line."""
    service = LabelService()
    service.start()


if __name__ == "__main__":
    main()
