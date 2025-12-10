"""
Feature engineering for distraction detection.

This script transforms raw database logs into ML-ready features.

WORKFLOW:
1. Load gaze_logs, tab_logs, labels from SQLite
2. Create 30-second windows sliding every 5 seconds
3. For each window:
   - Compute 11 gaze features (eye position, blinks, head pose)
   - Compute 13+ browser features (domain, keypresses, tab switches)
   - Assign label (focused/distracted) based on user labels in that window
4. Output features.csv for model training

EXAMPLE:
  If you have data from 14:30:00 to 14:35:00 (5 minutes):
  - Creates windows: [14:30:00-14:30:30], [14:30:05-14:30:35], ...
  - Each window = 1 row in features.csv
  - Total: ~60 windows (300 seconds / 5 second slide)
  - Only windows with labels are kept
"""

import pandas as pd
import numpy as np
import sys
import os
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import get_gaze_logs, get_tab_logs, get_labels


class FeatureEngineer:
    """Main class for feature engineering."""

    def __init__(self, window_size_sec: int = 30, slide_sec: int = 5):
        """
        Initialize feature engineer.

        Args:
            window_size_sec: Window size (default: 30 seconds per blueprint)
            slide_sec: How far to slide window (default: 5 seconds per blueprint)
        """
        self.window_size = window_size_sec
        self.slide = slide_sec

    def load_data(self) -> tuple:
        """
        Load all data from SQLite database.

        Returns:
            (gaze_df, tab_df, label_df) as pandas DataFrames
        """
        print("📊 Loading data from database...")

        # Get data from database
        gaze_data = get_gaze_logs()
        tab_data = get_tab_logs()
        label_data = get_labels()

        # Convert to DataFrames for easier manipulation
        gaze_df = pd.DataFrame(gaze_data)
        tab_df = pd.DataFrame(tab_data)
        label_df = pd.DataFrame(label_data)

        print(f"  ✓ Gaze logs: {len(gaze_df):,} frames")
        print(f"  ✓ Tab logs: {len(tab_df):,} entries")
        print(f"  ✓ Labels: {len(label_df)} (focused: {(label_df['label']=='focused').sum()}, "
              f"distracted: {(label_df['label']=='distracted').sum()})")

        return gaze_df, tab_df, label_df

    def compute_gaze_features(self, window_gaze: pd.DataFrame) -> Dict:
        """
        Compute 11 gaze features from gaze data in a window.

        FEATURES COMPUTED:
        - eye_off_center_mean: How far eyes are from screen center (average)
        - eye_off_center_std: Stability of gaze
        - eye_off_center_max: Maximum deviation
        - blink_rate: Blinks per minute
        - blink_ratio: Percentage of frames with blink
        - head_pitch_mean: Up/down head angle (average)
        - head_pitch_std: Head movement variability
        - head_yaw_mean: Left/right head angle (average)
        - head_yaw_std: Head turning variability
        - head_distance_mean: Distance from camera
        - head_distance_std: Leaning in/out variability

        Args:
            window_gaze: DataFrame with gaze data for this 30s window

        Returns:
            Dictionary with 11 gaze features
        """
        # Handle empty windows (no face detected)
        if len(window_gaze) == 0:
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

        # EYE POSITION FEATURES (3 features)
        # Higher = looking away from screen more
        eye_off_center_mean = window_gaze['eye_off_center'].mean()
        eye_off_center_std = window_gaze['eye_off_center'].std()
        eye_off_center_max = window_gaze['eye_off_center'].max()

        # BLINK FEATURES (2 features)
        # Too few blinks = zoning out, too many = tired
        total_blinks = window_gaze['blink'].sum()
        blink_rate = total_blinks / (self.window_size / 60)  # Blinks per minute
        blink_ratio = window_gaze['blink'].mean()  # % of frames with eyes closed

        # HEAD POSE FEATURES (4 features)
        # Looking down = engaged, looking up/around = distracted
        head_pitch_mean = window_gaze['head_pitch'].mean()
        head_pitch_std = window_gaze['head_pitch'].std()
        head_yaw_mean = window_gaze['head_yaw'].mean()
        head_yaw_std = window_gaze['head_yaw'].std()

        # DISTANCE FEATURES (2 features)
        # Leaning in = engaged, leaning back = disengaged
        head_distance_mean = window_gaze['head_distance'].mean()
        head_distance_std = window_gaze['head_distance'].std()

        return {
            'eye_off_center_mean': eye_off_center_mean,
            'eye_off_center_std': eye_off_center_std,
            'eye_off_center_max': eye_off_center_max,
            'blink_rate': blink_rate,
            'blink_ratio': blink_ratio,
            'head_pitch_mean': head_pitch_mean,
            'head_pitch_std': head_pitch_std,
            'head_yaw_mean': head_yaw_mean,
            'head_yaw_std': head_yaw_std,
            'head_distance_mean': head_distance_mean,
            'head_distance_std': head_distance_std,
        }

    def compute_tab_features(self, window_tabs: pd.DataFrame,
                            top_domains: List[str]) -> Dict:
        """
        Compute 13+ browser features from tab data in a window.

        FEATURES COMPUTED:
        - tab_switch_rate: How many different tabs per minute
        - keypress_rate: How many keypresses per minute
        - idle_ratio: Percentage of time idle
        - domain_* (one-hot): Which domain is active (github, youtube, etc.)

        Args:
            window_tabs: DataFrame with tab data for this 30s window
            top_domains: List of top N domains for one-hot encoding

        Returns:
            Dictionary with 13+ browser features
        """
        # Handle empty windows (no tab data)
        if len(window_tabs) == 0:
            features = {
                'tab_switch_rate': 0,
                'keypress_rate': 0,
                'idle_ratio': 0,
            }
            # One-hot encoded domains (all zeros except 'other')
            for domain in top_domains:
                features[f'domain_{domain}'] = 0
            features['domain_other'] = 1
            return features

        # TAB SWITCHING (1 feature)
        # More switching = less focused
        unique_domains = window_tabs['domain'].nunique()
        tab_switch_rate = unique_domains / (self.window_size / 60)

        # KEYBOARD ACTIVITY (1 feature)
        # More typing = more engaged (usually)
        total_keypresses = window_tabs['keypress_count'].sum()
        keypress_rate = total_keypresses / (self.window_size / 60)

        # IDLE STATE (1 feature)
        # Idle = away from computer
        idle_ratio = (window_tabs['idle_state'] == 'idle').mean()

        # DOMAIN ONE-HOT ENCODING (10+ features)
        # Which website are you on? youtube vs github vs twitter
        most_common_domain = window_tabs['domain'].mode()[0] if len(window_tabs) > 0 else 'other'

        features = {
            'tab_switch_rate': tab_switch_rate,
            'keypress_rate': keypress_rate,
            'idle_ratio': idle_ratio,
        }

        # One-hot encode the domain
        for domain in top_domains:
            features[f'domain_{domain}'] = 1 if domain == most_common_domain else 0
        features['domain_other'] = 1 if most_common_domain not in top_domains else 0

        return features

    def label_window(self, start_time: float, end_time: float,
                     label_df: pd.DataFrame) -> Optional[str]:
        """
        Determine label for a 30-second window based on user labels.

        LABELING RULE (from blueprint):
        - If >15 seconds marked as 'distracted' → label = 'distracted'
        - If >15 seconds marked as 'focused' → label = 'focused'
        - Otherwise → no label (window is discarded)

        Args:
            start_time: Window start timestamp
            end_time: Window end timestamp
            label_df: DataFrame with user labels

        Returns:
            'focused', 'distracted', or None
        """
        # Get all labels that fall in this window
        window_labels = label_df[
            (label_df['timestamp'] >= start_time) &
            (label_df['timestamp'] < end_time)
        ]

        # No labels in this window? Skip it
        if len(window_labels) == 0:
            return None

        # Simple heuristic: each label represents the state for the entire window
        # (In reality, you might press Ctrl+Shift+D once and stay distracted)
        distracted_count = (window_labels['label'] == 'distracted').sum()
        focused_count = (window_labels['label'] == 'focused').sum()

        # Estimate seconds for each state
        # Rough approximation: divide window equally among labels
        distracted_seconds = (distracted_count / len(window_labels)) * self.window_size
        focused_seconds = (focused_count / len(window_labels)) * self.window_size

        # Apply >15 second rule
        if distracted_seconds > 15:
            return 'distracted'
        elif focused_seconds > 15:
            return 'focused'
        else:
            return None

    def generate_features(self, top_n_domains: int = 10) -> pd.DataFrame:
        """
        Main method: Generate feature matrix from database.

        WORKFLOW:
        1. Load gaze, tab, label data
        2. Find time range of data
        3. Get top N domains for one-hot encoding
        4. Slide 30s window every 5s across time range
        5. For each window:
           - Extract gaze features (11)
           - Extract tab features (13+)
           - Determine label (focused/distracted/none)
           - Only keep windows with labels
        6. Return DataFrame with all features + labels

        Args:
            top_n_domains: How many top domains to one-hot encode (default: 10)

        Returns:
            DataFrame with columns:
            - window_start, window_end
            - 11 gaze features
            - 13+ tab features
            - label (focused/distracted)
        """
        # STEP 1: Load data
        gaze_df, tab_df, label_df = self.load_data()

        if len(label_df) == 0:
            raise ValueError("❌ No labels found! Press Ctrl+Shift+F/D during study sessions first.")

        # STEP 2: Determine time range
        min_time = min(
            gaze_df['timestamp'].min(),
            tab_df['timestamp'].min() if len(tab_df) > 0 else float('inf'),
            label_df['timestamp'].min()
        )
        max_time = max(
            gaze_df['timestamp'].max(),
            tab_df['timestamp'].max() if len(tab_df) > 0 else 0,
            label_df['timestamp'].max()
        )

        duration_hours = (max_time - min_time) / 3600
        print(f"\n⏱️  Time range: {max_time - min_time:.0f} seconds ({duration_hours:.2f} hours)")

        # STEP 3: Get top domains for one-hot encoding
        if len(tab_df) > 0:
            top_domains = tab_df['domain'].value_counts().head(top_n_domains).index.tolist()
            print(f"🌐 Top {len(top_domains)} domains: {top_domains}")
        else:
            top_domains = []
            print("⚠️  No tab data - browser features will be zeros")

        # STEP 4: Generate windows
        windows = []
        window_start = min_time

        print(f"\n🔄 Generating windows (size={self.window_size}s, slide={self.slide}s)...")

        while window_start < max_time:
            window_end = window_start + self.window_size

            # Get data in this window
            window_gaze = gaze_df[
                (gaze_df['timestamp'] >= window_start) &
                (gaze_df['timestamp'] < window_end)
            ]

            window_tabs = tab_df[
                (tab_df['timestamp'] >= window_start) &
                (tab_df['timestamp'] < window_end)
            ] if len(tab_df) > 0 else pd.DataFrame()

            # STEP 5: Get label for this window
            label = self.label_window(window_start, window_end, label_df)

            # Only include windows with labels (skip unlabeled periods)
            if label is not None:
                # Compute all features
                gaze_features = self.compute_gaze_features(window_gaze)
                tab_features = self.compute_tab_features(window_tabs, top_domains)

                # Combine everything into one row
                window_features = {
                    'window_start': window_start,
                    'window_end': window_end,
                    **gaze_features,  # Add all 11 gaze features
                    **tab_features,   # Add all 13+ tab features
                    'label': label
                }

                windows.append(window_features)

            # Move to next window
            window_start += self.slide

        print(f"✓ Generated {len(windows)} labeled windows")

        # STEP 6: Convert to DataFrame
        if len(windows) == 0:
            print("\n⚠️  No labeled windows generated!")
            print("   This means your labels are too sparse or short.")
            print("   Try labeling more frequently during study sessions.")
            return pd.DataFrame()

        features_df = pd.DataFrame(windows)

        # Print statistics
        print(f"\n📈 Label distribution:")
        print(features_df['label'].value_counts())
        print(f"\n📊 Feature count: {len(features_df.columns) - 3} features")
        print(f"   (excluding window_start, window_end, label)")

        return features_df


def main():
    """
    Main function: Generate features from database and save to CSV.

    Run this after collecting labels to prepare data for model training.
    """
    print("=" * 60)
    print("DIALED - Feature Engineering Pipeline")
    print("=" * 60)
    print()

    # Create feature engineer (30s windows, 5s slide per blueprint)
    engineer = FeatureEngineer(window_size_sec=30, slide_sec=5)

    try:
        # Generate features
        features_df = engineer.generate_features(top_n_domains=10)

        if len(features_df) == 0:
            print("\n❌ No features generated.")
            print("   Collect more labels and try again!")
            return

        # Save to CSV
        output_path = "features/features.csv"
        features_df.to_csv(output_path, index=False)

        print(f"\n✅ SUCCESS!")
        print(f"   Features saved to: {output_path}")
        print(f"   Rows (windows): {len(features_df)}")
        print(f"   Columns: {len(features_df.columns)}")
        print(f"\n🎯 Ready for model training!")
        print(f"   Next step: python models/train.py")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
