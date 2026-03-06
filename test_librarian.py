import os
import sys

# Load env config
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.librarian import librarian
import sys

# Patch librarian's _call to print stuff
old_run = librarian.run
librarian.run("事故データを探して")
response = librarian.run("事故データを探して")
print("Librarian Response:")
print(response)

