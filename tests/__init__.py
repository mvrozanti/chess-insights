import os
import sys
import pytest

current_directory = os.path.dirname(os.path.realpath(__file__ ))
project_root = os.path.abspath(os.path.join(current_directory, ".."))
sys.path.insert(0, project_root)
project_src = os.path.abspath(os.path.join(current_directory, "../src"))
sys.path.insert(0, project_src)
