# Application-wide constants shared across modules.
import os

# Master verbosity switch. False (default): only errors surface to the Text Commands
# palette / stdout; the file log (PerfectPrintGears.log) still records everything.
# True: full verbosity to the palette too (for development).
DEBUG = False

ADDIN_NAME = os.path.basename(os.path.dirname(__file__))
COMPANY_NAME = 'NorthstarData'
