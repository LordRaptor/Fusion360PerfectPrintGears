import adsk.core

from . import commands
from .lib import fusionAddInUtils as futil


def run(context):
    try:
        futil.log('Perfect Print Gears: run() -- loading add-in')
        commands.start()
        futil.log('Perfect Print Gears: loaded, log file at ' + futil.LOG_FILE)

        # Display a message when the add-in is manually run.
        if not context['IsApplicationStartup']:
            app = adsk.core.Application.get()
            app.userInterface.messageBox(
                'The Perfect Print Gears add-in has loaded and added a '
                '"Generate Perfect Print Gears" command to the CREATE panel in the '
                'SOLID tab of the DESIGN workspace.\n\n'
                'Debug log: ' + futil.LOG_FILE,
                'Perfect Print Gears')

    except Exception:
        futil.handle_error('run', show_message_box=True)


def stop(context):
    try:
        futil.clear_handlers()
        commands.stop()
    except Exception:
        futil.handle_error('stop')
