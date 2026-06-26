import os
import adsk.core
import adsk.fusion

from ...lib import fusionAddInUtils as futil
from ... import config
from ...core import gear_math, sketch_builder, settings

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_generateGears'
CMD_NAME = 'Generate Perfect Print Gears'
CMD_DESC = 'Generate a matched Perfect Print wheel + pinion as sketches'
IS_PROMOTED = True
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

ATTR_GROUP = 'PerfectPrintGears'
ATTR_NAME = 'Settings'

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
    if control:
        control.deleteMe()
    if cmd_def:
        cmd_def.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME}: command_created')
    inputs = args.command.commandInputs

    design = adsk.fusion.Design.cast(app.activeProduct)
    s = settings.defaults()
    if design:
        attr = design.attributes.itemByName(ATTR_GROUP, ATTR_NAME)
        if attr:
            s = settings.from_json(attr.value)

    # Target component (single selection); defaults to the active component on execute.
    sel = inputs.addSelectionInput('target', 'Target component',
                                   'Component to draw the gear sketches into')
    sel.addSelectionFilter('Occurrences')
    sel.addSelectionFilter('RootComponents')
    sel.setSelectionLimits(0, 1)

    inputs.addIntegerSpinnerCommandInput('wheelTeeth', 'Wheel teeth', 6, 2000, 1, int(s['wheel_teeth']))
    inputs.addIntegerSpinnerCommandInput('pinionTeeth', 'Pinion teeth', 6, 2000, 1, int(s['pinion_teeth']))

    inputs.addValueInput('module', 'Module (mm)', 'mm',
                         adsk.core.ValueInput.createByReal(s['module_mm'] * 0.1))

    # Feature width: switchable absolute / percent.
    wmode = inputs.addButtonRowCommandInput('widthMode', 'Tooth width mode', False)
    wmode.listItems.add('Absolute', not s['width_is_percent'])
    wmode.listItems.add('Percent', s['width_is_percent'])
    fw = inputs.addValueInput('featureWidth', 'Feature width', 'mm',
                              adsk.core.ValueInput.createByReal(s['feature_width_mm'] * 0.1))
    fwp = inputs.addValueInput('featureWidthPct', 'Feature width %', '',
                               adsk.core.ValueInput.createByReal(s['feature_width_pct']))
    fw.isVisible = not s['width_is_percent']
    fwp.isVisible = s['width_is_percent']

    # Clearance: switchable absolute / percent.
    cmode = inputs.addButtonRowCommandInput('clearanceMode', 'Clearance mode', False)
    cmode.listItems.add('Absolute', not s['clearance_is_percent'])
    cmode.listItems.add('Percent', s['clearance_is_percent'])
    cl = inputs.addValueInput('clearance', 'Clearance', 'mm',
                              adsk.core.ValueInput.createByReal(s['clearance_mm'] * 0.1))
    clp = inputs.addValueInput('clearancePct', 'Clearance %', '',
                               adsk.core.ValueInput.createByReal(s['clearance_pct']))
    cl.isVisible = not s['clearance_is_percent']
    clp.isVisible = s['clearance_is_percent']

    # Advanced group.
    adv = inputs.addGroupCommandInput('advanced', 'Advanced')
    adv.isExpanded = False
    a = adv.children
    a.addValueInput('addendumFactor', 'Addendum factor', '',
                    adsk.core.ValueInput.createByReal(s['addendum_factor']))
    a.addValueInput('dedendumFactor', 'Dedendum factor', '',
                    adsk.core.ValueInput.createByReal(s['dedendum_factor']))
    a.addIntegerSpinnerCommandInput('resolution', 'Resolution (steps)', 8, 200, 1, int(s['resolution']))

    inputs.addTextBoxCommandInput('errMsg', '', '', 2, True).isFullWidth = True

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    inputs = args.inputs
    changed = args.input
    if changed.id == 'widthMode':
        is_pct = inputs.itemById('widthMode').selectedItem.name == 'Percent'
        inputs.itemById('featureWidth').isVisible = not is_pct
        inputs.itemById('featureWidthPct').isVisible = is_pct
    elif changed.id == 'clearanceMode':
        is_pct = inputs.itemById('clearanceMode').selectedItem.name == 'Percent'
        inputs.itemById('clearance').isVisible = not is_pct
        inputs.itemById('clearancePct').isVisible = is_pct


def _read_inputs(inputs):
    """Collect dialog values into a gear_math.GearInputs (all mm). Raises ValueError."""
    module_mm = inputs.itemById('module').value / 0.1          # cm -> mm
    circular_pitch = 3.141592653589793 * module_mm

    width_is_pct = inputs.itemById('widthMode').selectedItem.name == 'Percent'
    feature_width_mm = settings.resolve_length(
        width_is_pct,
        abs_mm=inputs.itemById('featureWidth').value / 0.1,
        pct=inputs.itemById('featureWidthPct').value,
        basis_mm=circular_pitch)

    clr_is_pct = inputs.itemById('clearanceMode').selectedItem.name == 'Percent'
    clearance_mm = settings.resolve_length(
        clr_is_pct,
        abs_mm=inputs.itemById('clearance').value / 0.1,
        pct=inputs.itemById('clearancePct').value,
        basis_mm=feature_width_mm)

    adv = inputs.itemById('advanced').children
    return gear_math.GearInputs(
        wheel_teeth=inputs.itemById('wheelTeeth').value,
        pinion_teeth=inputs.itemById('pinionTeeth').value,
        module_mm=module_mm,
        feature_width_mm=feature_width_mm,
        clearance_mm=clearance_mm,
        addendum_factor=adv.itemById('addendumFactor').value,
        dedendum_factor=adv.itemById('dedendumFactor').value,
        resolution=adv.itemById('resolution').value,
    )


def command_validate(args: adsk.core.ValidateInputsEventArgs):
    inputs = args.inputs
    err = inputs.itemById('errMsg')
    try:
        gi = _read_inputs(inputs)
        gear_math.validate_inputs(gi)
        err.text = ''
        args.areInputsValid = True
    except ValueError as e:
        err.text = str(e)
        args.areInputsValid = False


def _resolve_target(inputs):
    design = adsk.fusion.Design.cast(app.activeProduct)
    sel = inputs.itemById('target')
    if sel.selectionCount == 1:
        entity = sel.selection(0).entity
        if isinstance(entity, adsk.fusion.Occurrence):
            return entity.component
        return entity  # a Component (root)
    return design.activeComponent


def _persist_settings(inputs):
    design = adsk.fusion.Design.cast(app.activeProduct)
    s = settings.defaults()
    s.update({
        'wheel_teeth': inputs.itemById('wheelTeeth').value,
        'pinion_teeth': inputs.itemById('pinionTeeth').value,
        'module_mm': inputs.itemById('module').value / 0.1,
        'width_is_percent': inputs.itemById('widthMode').selectedItem.name == 'Percent',
        'feature_width_mm': inputs.itemById('featureWidth').value / 0.1,
        'feature_width_pct': inputs.itemById('featureWidthPct').value,
        'clearance_is_percent': inputs.itemById('clearanceMode').selectedItem.name == 'Percent',
        'clearance_mm': inputs.itemById('clearance').value / 0.1,
        'clearance_pct': inputs.itemById('clearancePct').value,
        'addendum_factor': inputs.itemById('advanced').children.itemById('addendumFactor').value,
        'dedendum_factor': inputs.itemById('advanced').children.itemById('dedendumFactor').value,
        'resolution': inputs.itemById('advanced').children.itemById('resolution').value,
    })
    attr = design.attributes.itemByName(ATTR_GROUP, ATTR_NAME)
    if attr:
        attr.value = settings.to_json(s)
    else:
        design.attributes.add(ATTR_GROUP, ATTR_NAME, settings.to_json(s))


def command_execute(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    try:
        gi = _read_inputs(inputs)
        pair = gear_math.build_gear_pair(gi)
        target = _resolve_target(inputs)
        sketch_builder.build_pair(target, pair)
        _persist_settings(inputs)
        futil.log(f'{CMD_NAME}: generated {pair.wheel.teeth}T / {pair.pinion.teeth}T')
    except Exception:
        futil.handle_error('command_execute', show_message_box=True)


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
