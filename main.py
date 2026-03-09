"""
Council - Entry Point
Run: python main.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from ui.app import launch

if __name__ == "__main__":
    launch()
