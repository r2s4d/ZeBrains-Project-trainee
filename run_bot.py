#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple bot launcher with correct import paths.
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now import and run bot
from bot.bot import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main()) 