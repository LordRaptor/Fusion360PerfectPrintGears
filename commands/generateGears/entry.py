import os
import math
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
    futil.log(f'{CMD_NAME}: command_created START')
    cmd = args.command
    # Attach handlers FIRST so the command stays functional even if building an
    # input later fails -- and so we can see the failure instead of a dead dialog.
    futil.add_handler(cmd.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(cmd.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(cmd.validateInputs, command_validate, local_handlers=local_handlers)
    futil.add_handler(cmd.destroy, command_destroy, local_handlers=local_handlers)
    try:
        _build_inputs(cmd.commandInputs)
        futil.log(f'{CMD_NAME}: command_created OK')
    except Exception:
        futil.handle_error('command_created/_build_inputs', show_message_box=True)


def _build_inputs(inputs):
    """Build the dialog inputs, logging each step so a failure points at the line."""
    design = adsk.fusion.Design.cast(app.activeProduct)
    s = settings.defaults()
    if design:
        attr = design.attributes.itemByName(ATTR_GROUP, ATTR_NAME)
        if attr:
            s = settings.from_json(attr.value)
    futil.log(f'build: settings = {s}')

    futil.log('build: target')
    sel = inputs.addSelectionInput('target', 'Target component',
                                   'Component to draw the gear sketches into')
    sel.addSelectionFilter('Occurrences')
    sel.addSelectionFilter('RootComponents')
    sel.setSelectionLimits(0, 1)

    futil.log('build: teeth')
    inputs.addIntegerSpinnerCommandInput('wheelTeeth', 'Wheel teeth', 6, 2000, 1, int(s['wheel_teeth']))
    inputs.addIntegerSpinnerCommandInput('pinionTeeth', 'Pinion teeth', 6, 2000, 1, int(s['pinion_teeth']))

    futil.log('build: module')
    inputs.addValueInput('module', 'Module (mm)', 'mm',
                         adsk.core.ValueInput.createByReal(s['module_mm'] * 0.1))

    futil.log('build: toothFraction')
    inputs.addValueInput('toothFraction', 'Tooth fraction', '',
                         adsk.core.ValueInput.createByReal(s['tooth_fraction']))

    futil.log('build: featureWidthInfo')
    # Feature width is DERIVED -> a disabled value field (info only), not editable.
    fwi = inputs.addValueInput('featureWidthInfo', 'Feature width (mm)', 'mm',
                               adsk.core.ValueInput.createByReal(0.0))
    fwi.isEnabled = False

    futil.log('build: clearance')
    # Text-list dropdown (a button row would require a per-item icon resource).
    cmode = inputs.addDropDownCommandInput(
        'clearanceMode', 'Clearance mode',
        adsk.core.DropDownStyles.TextListDropDownStyle)
    cmode.listItems.add('Absolute', not s['clearance_is_percent'])
    cmode.listItems.add('Percent', s['clearance_is_percent'])
    cl = inputs.addValueInput('clearance', 'Clearance', 'mm',
                              adsk.core.ValueInput.createByReal(s['clearance_mm'] * 0.1))
    clp = inputs.addValueInput('clearancePct', 'Clearance %', '',
                               adsk.core.ValueInput.createByReal(s['clearance_pct']))
    cl.isVisible = not s['clearance_is_percent']
    clp.isVisible = s['clearance_is_percent']

    futil.log('build: thickness')
    inputs.addValueInput('thickness', 'Thickness (mm)', 'mm',
                         adsk.core.ValueInput.createByReal(s['thickness_mm'] * 0.1))

    futil.log('build: advanced')
    adv = inputs.addGroupCommandInput('advanced', 'Advanced')
    adv.isExpanded = False
    a = adv.children
    a.addValueInput('addendumFactor', 'Addendum factor', '',
                    adsk.core.ValueInput.createByReal(s['addendum_factor']))
    a.addValueInput('dedendumFactor', 'Dedendum factor', '',
                    adsk.core.ValueInput.createByReal(s['dedendum_factor']))
    a.addIntegerSpinnerCommandInput('resolution', 'Tip spline points', 3, 40, 1, int(s['resolution']))

    futil.log('build: errMsg')
    inputs.addTextBoxCommandInput('errMsg', '', '', 2, True).isFullWidth = True

    futil.log('build: update feature width display')
    _update_feature_width_display(inputs)
    futil.log('build: inputs done')


def _update_feature_width_display(inputs):
    """Recompute the derived feature width into the disabled value field (mm->cm)."""
    try:
        module_mm = inputs.itemById('module').value / 0.1
        tf = inputs.itemById('toothFraction').value
        fw = tf * math.pi * module_mm
        inputs.itemById('featureWidthInfo').value = fw * 0.1
    except Exception:
        pass


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    inputs = args.inputs
    changed = args.input
    if changed.id in ('module', 'toothFraction'):
        _update_feature_width_display(inputs)
    elif changed.id == 'clearanceMode':
        is_pct = inputs.itemById('clearanceMode').selectedItem.name == 'Percent'
        inputs.itemById('clearance').isVisible = not is_pct
        inputs.itemById('clearancePct').isVisible = is_pct


def _read_inputs(inputs):
    """Collect dialog values into a gear_math.GearInputs (all mm). Raises ValueError."""
    module_mm = inputs.itemById('module').value / 0.1          # cm -> mm
    tooth_fraction = inputs.itemById('toothFraction').value
    # Feature width is derived; clearance-as-percent uses it as the basis.
    feature_width_mm = tooth_fraction * math.pi * module_mm

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
        tooth_fraction=tooth_fraction,
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
        'tooth_fraction': inputs.itemById('toothFraction').value,
        'clearance_is_percent': inputs.itemById('clearanceMode').selectedItem.name == 'Percent',
        'clearance_mm': inputs.itemById('clearance').value / 0.1,
        'clearance_pct': inputs.itemById('clearancePct').value,
        'thickness_mm': inputs.itemById('thickness').value / 0.1,
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
        thickness_mm = inputs.itemById('thickness').value / 0.1
        sketch_builder.build_pair(target, pair, thickness_mm)
        _persist_settings(inputs)
        futil.log(f'{CMD_NAME}: generated {pair.wheel.teeth}T / {pair.pinion.teeth}T')
    except Exception:
        futil.handle_error('command_execute', show_message_box=True)


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
