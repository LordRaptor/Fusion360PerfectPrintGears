import os
import traceback
import adsk.core

app = adsk.core.Application.get()
ui = app.userInterface

try:
    from ... import config
    DEBUG = config.DEBUG
except Exception:
    DEBUG = False

# A plain-text log file next to the add-in folder -- easy to find and tail.
_ADDIN_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_FILE = os.path.join(_ADDIN_DIR, 'PerfectPrintGears.log')


def _text_palette():
    try:
        return ui.palettes.itemById('TextCommands')
    except Exception:
        return None


def log(message: str, level: adsk.core.LogLevels = adsk.core.LogLevels.InfoLogLevel,
        force_console: bool = False):
    """Log to a file next to the add-in (full verbosity -- the debugging record) and,
    for ERRORS only (or when DEBUG/force_console opt in), to the Text Commands palette
    and stdout. Fusion routes print() to the Text Commands palette, so gating print is
    what keeps that palette uncluttered. Robust: any sink failing must not break the
    others."""
    line = str(message)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass
    if DEBUG or force_console or level == adsk.core.LogLevels.ErrorLogLevel:
        print(line)
        pal = _text_palette()
        if pal:
            try:
                pal.isVisible = True
                pal.writeText(line)
            except Exception:
                pass
    try:
        if level == adsk.core.LogLevels.ErrorLogLevel:
            app.log(line, level, adsk.core.LogTypes.FileLogType)
        if DEBUG or force_console:
            app.log(line, level, adsk.core.LogTypes.ConsoleLogType)
    except Exception:
        pass


def handle_error(name: str, show_message_box: bool = False):
    tb = traceback.format_exc()
    log('===== Error =====', adsk.core.LogLevels.ErrorLogLevel)
    log(f'{name}\n{tb}', adsk.core.LogLevels.ErrorLogLevel)
    if show_message_box:
        try:
            ui.messageBox(f'{name}\n{tb}')
        except Exception:
            pass
