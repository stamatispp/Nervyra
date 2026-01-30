"""Nervyra launcher.

This file stays small on purpose. The application logic lives in `nervyra.app`.
"""

import resources_rc  # noqa: F401  (Qt resources, provides :/icons/icon.ico)

from nervyra.app import main

if __name__ == "__main__":
    main()
