from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from skinforge import __version__
from skinforge.ai import AIConfigurationError, create_plan
from skinforge.archive import ArchiveInspectionError, inspect_zip, validate_zip, write_report
from skinforge.bininspect import inspect_bin
from skinforge.wad import doctor as wadtools_doctor
from skinforge.wad import extract_wad
from skinforge.wad import install_wadtools
