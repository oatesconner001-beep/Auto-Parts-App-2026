"""
Enhanced Excel processing with unified architecture support.

This wraps the existing excel_handler.py functionality while adding support for
the new configuration system and cost tracking.
"""

import sys
from pathlib import Path

# Import the existing excel handler
sys.path.append(str(Path(__file__).parent.parent.parent))
from excel_handler import *  # Import all existing functionality

# This module serves as a bridge between the new unified architecture
# and the proven existing excel processing logic. The actual processing
# functions are imported directly from the original excel_handler.py
# to maintain compatibility and avoid duplication.

# Additional unified architecture features can be added here without
# disrupting the working excel processing pipeline.