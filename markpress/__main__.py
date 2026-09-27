"""Allow running MarkPress with `python -m markpress`."""
import sys

from markpress.cli import main

sys.exit(main())
