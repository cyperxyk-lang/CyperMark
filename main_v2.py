"""
CyperMark v2 — точка входа для новой версии GUI (CustomTkinter)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# CLI режим (тот же, что и в v1)
if "--cli" in sys.argv:
    from main import cli_mode
    args = [a for a in sys.argv[1:] if a != "--cli"]
    cli_mode(args)
else:
    # GUI v2
    from gui_v2 import CyperMarkV2
    app = CyperMarkV2()
    app.mainloop()
