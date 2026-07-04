import os
import json
import adsk.core

from ...lib import fusionAddInUtils as futil
from ... import config
from ...core import gear_train

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_calcGearTrain'
CMD_NAME = 'Gear Train Calculator'
CMD_DESC = 'Find compound clock gear trains that hit an exact target ratio'
IS_PROMOTED = False
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

PALETTE_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_gearTrainPalette'
PALETTE_NAME = 'Gear Train Calculator'
# htmlFileURL: a local path to the palette HTML (Qt web browser). MUST use forward
# slashes -- Fusion prepends file:/// and URL-encodes the path, and Windows backslashes
# would become %5C, giving ERR_INVALID_URL.
PALETTE_URL = os.path.join(ICON_FOLDER, 'palette.html').replace('\\', '/')

local_handlers = []


def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_DESC, ICON_FOLDER)
    futil.add_handler(cmd_def.commandCreated, command_created)
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.addCommand(cmd_def)
    control.isPromoted = IS_PROMOTED


def stop():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.itemById(CMD_ID)
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    palette = ui.palettes.itemById(PALETTE_ID)
    if control:
        control.deleteMe()
    if cmd_def:
        cmd_def.deleteMe()
    if palette:
        palette.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    # This launcher command has no inputs -- it only surfaces the palette. Palettes are
    # deleted on workspace switch, so always re-fetch (never cache the reference) and
    # create-if-missing. Attach the incomingFromHTML handler only when we create it.
    futil.log(f'{CMD_NAME}: command_created START')
    try:
        palette = ui.palettes.itemById(PALETTE_ID)
        if palette is None:
            palette = ui.palettes.add(
                PALETTE_ID, PALETTE_NAME, PALETTE_URL,
                True,   # isVisible
                True,   # showCloseButton
                True,   # isResizable
                420, 600,   # width, height
                True,   # useNewWebBrowser (ignored; Qt browser is always used now)
            )
            palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
            futil.add_handler(palette.incomingFromHTML, palette_incoming,
                              local_handlers=local_handlers)
            futil.log(f'{CMD_NAME}: palette created')
        palette.isVisible = True
    except Exception:
        futil.handle_error('command_created', show_message_box=True)


def palette_incoming(args: adsk.core.HTMLEventArgs):
    """Handle the 'search' message from the palette: parse the query, run the pure
    engine, and push results (or an error) back to the HTML."""
    try:
        if args.action != 'search':
            return
        data = json.loads(args.data)
        query = gear_train.TrainQuery(
            target_num=int(data['target_num']),
            target_den=int(data['target_den']),
            min_stages=int(data['min_stages']),
            max_stages=int(data['max_stages']),
            teeth_min=int(data['teeth_min']),
            teeth_max=int(data['teeth_max']),
            direction=str(data.get('direction', 'any')),
            coaxial=bool(data.get('coaxial', False)),
        )
        payload = json.dumps(gear_train.result_to_dict(gear_train.search(query)))
    except Exception:
        futil.handle_error('palette_incoming')
        payload = json.dumps({'trains': [], 'truncated': False, 'warnings': [],
                              'error': 'Could not read the query. Check the input fields.'})
    palette = ui.palettes.itemById(PALETTE_ID)
    if palette:
        palette.sendInfoToHTML('results', payload)
