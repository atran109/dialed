"""
Real-time distraction detection demo.

Loads trained model and predicts distraction every 2 seconds
based on last 30 seconds of gaze data.

USAGE:
  python demo_live.py

CONTROLS:
  Ctrl+C to stop
"""

import time
import sys
import os
import numpy as np
import pandas as pd
import joblib
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.database import get_gaze_logs, get_tab_logs


class LivePredictor:
    """Real-time distraction predictor."""

    def __init__(self):
        """Load model and configuration."""
        print("📂 Loading model...")

        self.model = joblib.load("models/model.pkl")

        with open("models/feature_config.json", 'r') as f:
            self.config = json.load(f)

        self.feature_names = self.config['feature_names']

        print(f"  ✓ Model loaded (AUC: {self.config['metrics']['roc_auc']:.3f})")
        print(f"  ✓ Features: {len(self.feature_names)}")

        # Extract top domains from config
        self.top_domains = [
            feat.replace('domain_', '')
            for feat in self.feature_names
            if feat.startswith('domain_') and feat != 'domain_other'
        ]

    def compute_gaze_features(self, gaze_df):
        """Compute gaze features from recent data."""
        if len(gaze_df) == 0:
            return {
                'eye_off_center_mean': 0,
                'eye_off_center_std': 0,
                'eye_off_center_max': 0,
                'blink_rate': 0,
                'blink_ratio': 0,
                'head_pitch_mean': 0,
                'head_pitch_std': 0,
                'head_yaw_mean': 0,
                'head_yaw_std': 0,
                'head_distance_mean': 0,
                'head_distance_std': 0,
            }

        return {
            'eye_off_center_mean': gaze_df['eye_off_center'].mean(),
            'eye_off_center_std': gaze_df['eye_off_center'].std(),
            'eye_off_center_max': gaze_df['eye_off_center'].max(),
            'blink_rate': gaze_df['blink'].sum() / 0.5,
            'blink_ratio': gaze_df['blink'].mean(),
            'head_pitch_mean': gaze_df['head_pitch'].mean(),
            'head_pitch_std': gaze_df['head_pitch'].std(),
            'head_yaw_mean': gaze_df['head_yaw'].mean(),
            'head_yaw_std': gaze_df['head_yaw'].std(),
            'head_distance_mean': gaze_df['head_distance'].mean(),
            'head_distance_std': gaze_df['head_distance'].std(),
        }

    def compute_tab_features(self, tab_df):
        """Compute browser features from recent data."""
        if len(tab_df) == 0:
            features = {
                'tab_switch_rate': 0,
                'keypress_rate': 0,
                'idle_ratio': 0,
            }
            for domain in self.top_domains:
                features[f'domain_{domain}'] = 0
            features['domain_other'] = 1
            return features

        unique_domains = tab_df['domain'].nunique()
        tab_switch_rate = unique_domains / 0.5
        total_keypresses = tab_df['keypress_count'].sum()
        keypress_rate = total_keypresses / 0.5
        idle_ratio = (tab_df['idle_state'] == 'idle').mean()

        most_common_domain = tab_df['domain'].mode()[0] if len(tab_df) > 0 else 'other'

        features = {
            'tab_switch_rate': tab_switch_rate,
            'keypress_rate': keypress_rate,
            'idle_ratio': idle_ratio,
        }

        for domain in self.top_domains:
            features[f'domain_{domain}'] = 1 if domain == most_common_domain else 0
        features['domain_other'] = 1 if most_common_domain not in self.top_domains else 0

        return features

    def predict(self):
        """
        Get prediction based on last 30 seconds of data.

        Returns:
            (prob_distracted, state_str, features_dict)
        """
        # Get recent data (last 30 seconds)
        now = time.time()
        start_time = now - 30

        recent_gaze = get_gaze_logs(start_time=start_time, end_time=now)
        recent_tabs = get_tab_logs(start_time=start_time, end_time=now)

        if len(recent_gaze) == 0:
            return None, "NO_DATA", {}

        # Convert to DataFrames
        gaze_df = pd.DataFrame(recent_gaze)
        tab_df = pd.DataFrame(recent_tabs) if len(recent_tabs) > 0 else pd.DataFrame()

        # Compute features
        gaze_features = self.compute_gaze_features(gaze_df)
        tab_features = self.compute_tab_features(tab_df)

        # Combine features in correct order
        all_features = {**gaze_features, **tab_features}
        feature_values = [all_features.get(name, 0) for name in self.feature_names]

        # Handle NaN
        feature_values = np.nan_to_num(feature_values, nan=0.0)

        # Predict
        prob_distracted = self.model.predict_proba([feature_values])[0][1]

        # Determine state
        if prob_distracted > 0.6:
            state = "DISTRACTED"
        else:
            state = "FOCUSED"

        return prob_distracted, state, all_features

    def run(self, interval_sec=2):
        """
        Run live prediction loop.

        Args:
            interval_sec: How often to predict (default: 2 seconds)
        """
        print("\n" + "=" * 60)
        print("🎯 REAL-TIME DISTRACTION DETECTION")
        print("=" * 60)
        print()
        print("Watching your behavior...")
        print("(Analyzing last 30 seconds of gaze + browser data)\n")
        print("Press Ctrl+C to stop\n")
        print("-" * 60)

        try:
            while True:
                prob, state, features = self.predict()

                if state == "NO_DATA":
                    print("⏳ Waiting for data... (is gaze service running?)")
                else:
                    # Color-coded output
                    if state == "DISTRACTED":
                        icon = "🔴"
                        color = "\033[91m"  # Red
                    else:
                        icon = "🟢"
                        color = "\033[92m"  # Green

                    reset = "\033[0m"

                    # Main status line
                    print(f"{color}{icon} {state:12s}{reset} | "
                          f"Confidence: {prob:.1%} | "
                          f"Eyes off: {features.get('eye_off_center_mean', 0):.2f} | "
                          f"Distance: {features.get('head_distance_mean', 0):.2f}")

                time.sleep(interval_sec)

        except KeyboardInterrupt:
            print("\n\n" + "=" * 60)
            print("Demo stopped. Thanks for watching!")
            print("=" * 60)


def main():
    """Run live demo."""
    try:
        predictor = LivePredictor()
        predictor.run(interval_sec=2)

    except FileNotFoundError:
        print("\n❌ Error: Model not found!")
        print("   Run this first: python models/train.py")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
