"""One-time extraction of the reviewed static blocks; never used at runtime."""
import ast
import builtins
import copy
from pathlib import Path
import re
import subprocess
import symtable
import textwrap

root = Path(__file__).resolve().parents[1]
target = root / 'Gait-lab-Vicon-to-QTM'
source = subprocess.check_output(['git', 'show', 'HEAD:Gait-lab-Vicon-to-QTM/Py3_StaticMain.py'], cwd=root).decode('utf8')
lines = source.splitlines()
tree = ast.parse(source)
methods = {}
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in ('saveSubjectData', 'saveTransformationMatrices', 'saveResultsinC3D', 'savePdf'):
        methods[node.name] = node

def segment(start, end):
    return textwrap.dedent('\n'.join(lines[start - 1:end])) + '\n'

def changes(code, edits):
    rows = code.splitlines(keepends=True)
    for start, end, replacement in sorted(edits, reverse=True):
        indent = len(rows[start - 1]) - len(rows[start - 1].lstrip())
        rows[start - 1:end] = [(' ' * indent + replacement + '\n')]
    return ''.join(rows)

# Extract parameter loading, replacing field controls with plain dictionary values.
patient = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PatientInfo_Page')
patient_ui = next(n for n in patient.body if isinstance(n, ast.FunctionDef) and n.name == 'build_UI')
inputs = {}
for n in patient_ui.body:
    if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and isinstance(n.value.func.value, ast.Name) and n.value.func.value.id == 'tk' and n.value.func.attr in ('Entry', 'StringVar', 'IntVar'):
        name = ast.unparse(n.targets[0]); kind = n.value.func.attr
        default = next((k.value for k in n.value.keywords if k.arg == 'value'), ast.Constant(0 if kind == 'IntVar' else ''))
        inputs[name] = (kind, ast.unparse(default))

class InputTransform(ast.NodeTransformer):
    def key(self, node):
        name = ast.unparse(node)
        return ast.Subscript(value=ast.Name(id='inputs', ctx=ast.Load()), slice=ast.Constant(name), ctx=ast.Load()) if name in inputs else None
    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'get':
            key = self.key(node.func.value)
            if key is not None:
                return ast.copy_location(key, node)
        return self.generic_visit(node)
    def visit_Expr(self, node):
        call = node.value
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
            key = self.key(call.func.value)
            if key is not None and call.func.attr in ('set', 'insert', 'delete'):
                name = ast.unparse(call.func.value)
                if call.func.attr == 'delete':
                    value = ast.Constant('')
                else:
                    value = self.visit(call.args[-1])
                    conversion = 'int' if inputs[name][0] == 'IntVar' else 'str'
                    value = ast.Call(func=ast.Name(id=conversion, ctx=ast.Load()), args=[value], keywords=[])
                    if call.func.attr == 'insert':
                        value = ast.BinOp(left=value, op=ast.Add(), right=copy.deepcopy(key))
                key.ctx = ast.Store()
                return ast.copy_location(ast.Assign(targets=[key], value=value), node)
        return self.generic_visit(node)

patient_nodes = []
for n in patient_ui.body:
    if 357 <= n.lineno <= 567:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and ast.unparse(n.value.func.value) == 'tk':
            continue
        if any(isinstance(x, ast.Name) and x.id == 'tk' for x in ast.walk(n)):
            continue
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and n.value.func.attr in ('grid','pack','columnconfigure'):
            continue
        if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) in ('now', 'DateOptions', 'MonthOptions', 'YearOptions', 'DataCollectionYearOptions') or isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'set' or isinstance(n, ast.If) and 393 <= n.lineno <= 399 or isinstance(n, ast.Assign) and ast.unparse(n.targets[0]).endswith('Options') or isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == 'dob':
            patient_nodes.append(copy.deepcopy(n))
    elif 574 <= n.lineno <= 821:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript):
            continue
        patient_nodes.append(copy.deepcopy(n))

# The legacy helper loops over variables; these are dictionary keys now.
patient_tree = ast.Module(body=patient_nodes, type_ignores=[])
patient_code = ast.unparse(ast.fix_missing_locations(InputTransform().visit(patient_tree)))
for name in sorted(inputs, key=len, reverse=True):
    # Bare control references occur only in the two population loops.
    patient_code = re.sub(r'(?<![\w.\'\"])' + re.escape(name) + r'(?![\w\'\"])', repr(name), patient_code)
patient_code = patient_code.replace('variable.set(getattr(self, name))', 'inputs[variable] = str(getattr(self, name))')
patient_code = patient_code.replace('widget.insert(0, val)', 'inputs[widget] = str(val) + inputs[widget]')
patient_code = patient_code.replace('self.parent._headless', 'True')
initial = 'inputs = {\n' + ''.join(f'    {name!r}: {value},\n' for name, (_, value) in inputs.items()) + '}\n'
save_subject = textwrap.dedent(segment(methods['saveSubjectData'].lineno, methods['saveSubjectData'].end_lineno))
save_subject = ast.unparse(ast.fix_missing_locations(InputTransform().visit(ast.parse(save_subject))))

def presentation_to_data(code):
    t = ast.parse(code)
    edits = []
    for n in ast.walk(t):
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute):
            call = n.value; owner = ast.unparse(call.func.value); action = call.func.attr
            if owner in ('ErrorMessagesLabel', 'ErrorMessagesText'):
                replacement = 'warnings.append(str(' + ast.unparse(call.args[-1]) + ').strip())' if action == 'insert' else 'pass'
                edits.append((n.lineno, n.end_lineno, replacement))
            elif isinstance(call.func.value, ast.Name) and action in ('configure', 'config', 'place', 'place_forget'):
                edits.append((n.lineno, n.end_lineno, 'pass'))
            elif isinstance(call.func.value, ast.Name) and action == 'insert':
                edits.append((n.lineno, n.end_lineno, f'report[{owner!r}] = str({ast.unparse(call.args[-1])})'))
        elif isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript) and isinstance(n.targets[0].value, ast.Name) and isinstance(n.targets[0].slice, ast.Constant) and n.targets[0].slice.value in ('text', 'fg', 'bg'):
            owner = n.targets[0].value.id
            edits.append((n.lineno, n.end_lineno, f'report[{owner!r}] = {ast.unparse(n.value)}' if n.targets[0].slice.value == 'text' else 'pass'))
    code = changes(code, edits)
    code = re.sub(r'self.HasTrajectory\(([^,]+), ([^)]+)\)', r'(\2 in fields)', code)
    return code

imports = '''"""Static calibration equations extracted unchanged from Py3_StaticMain at e6b06a1.

Each stage takes one per-run state dictionary and returns its calculated values.
There are no widgets, event loops, or live QTM calls in these stages.
"""
import os
import datetime
from pathlib import Path
import numpy as np
from numpy import array, nan
import Py3_MathModules as math
import Py3_GaitModules as gait
from static_calibration_parameters import normalize_processing_measurements, write_setting, qtm_measurement_to_meters, persisted_measurement_to_meters
MILLIMETERS_PER_METER = 1000.0
'''
known = set(dir(builtins)) | {'os','datetime','Path','np','array','nan','math','gait','normalize_processing_measurements','write_setting','qtm_measurement_to_meters','persisted_measurement_to_meters','MILLIMETERS_PER_METER'}

def function(name, body, return_state=True):
    stub = 'def ' + name + '(state):\n' + textwrap.indent(body, '    ')
    table = symtable.symtable(stub, 'extracted', 'exec').get_children()[0]
    def globals_in(tab):
        return {x.get_name() for x in tab.get_symbols() if x.is_global() and x.is_referenced()} | set().union(*(globals_in(x) for x in tab.get_children()), set())
    bindings = sorted(globals_in(table) - known)
    binding_code = ''.join(f'if {key!r} in state: {key} = state[{key!r}]\n' for key in bindings)
    ending = '\nreturn {name: value for name, value in locals().items() if name != "state" and not callable(value)}\n' if return_state else ''
    return f'\n\ndef {name}(state):\n' + textwrap.indent(binding_code + body + ending, '    ')

parameter_module = imports.split('from static_calibration_parameters')[0].replace('import Py3_MathModules as math\nimport Py3_GaitModules as gait\n','')
parameter_module += '\nMILLIMETERS_PER_METER = 1000.0\n' + segment(77,110) + '\n'
parameter_module += function('populate_clinical_inputs', initial + patient_code + '\nreturn inputs\n', False)
save_node = ast.parse(save_subject).body[0]
save_body = '\n'.join(save_subject.splitlines()[1:])
save_body = textwrap.dedent(save_body)
parameter_module += function('save_clinical_inputs', save_body)
(target/'static_calibration_parameters.py').write_text(parameter_module,encoding='utf8')

module = imports
qa = presentation_to_data(segment(1314,2420))
qa += '\n' + segment(2425,2480)
start = qa.index('        f = open(DefaultStaticDataFileName,')
end = qa.index('        LeftASISMarkerPelvis = self.valueLeftASISMarkerPelvis', start)
qa = qa[:start] + '''        selected = [line for line in Path(DefaultStaticDataFileName).read_text().splitlines(True)
                    if line.split() and line.split()[0] in (
                        'self.valueLeftASISMarkerPelvis', 'self.valueRightASISMarkerPelvis')]
        exec(''.join(selected))
''' + qa[end:]
module += function('validate_static_markers',qa)
for name,start,end in [('load_calibration_markers',2739,3245),('compute_joint_centers_and_technical_systems',3250,3632),('compute_anatomical_systems_and_foot',3638,3778),('compute_transforms_and_posture',3784,4099)]:
    module += function(name,presentation_to_data(segment(start,end)))
# Keep the legacy posture descriptions as structured report values for PDF rendering.
module += function('format_calibration_report',presentation_to_data(segment(4107,4815)))
for old,new in [('saveTransformationMatrices','save_transformation_matrices'),('saveResultsinC3D','generate_modeled_markers')]:
    n=methods[old]
    body = textwrap.dedent('\n'.join(segment(n.lineno,n.end_lineno).splitlines()[1:]))+'\n'
    
    if old == 'saveResultsinC3D':
        body = body.replace('exec(open(StaticDataFileName).read())', 'exec(open(StaticDataFileName).read())\nnormalize_processing_measurements(self)')
    module += function(new,presentation_to_data(body))
(target/'static_calibration_calculations.py').write_text(module,encoding='utf8')

# PDF rendering keeps the existing layout and descriptions, but takes a destination.
n=methods['savePdf']; body=textwrap.dedent('\n'.join(segment(n.lineno,n.end_lineno).splitlines()[1:]))+'\n'
pdf_tree=ast.parse(body); edits=[]
for n in ast.walk(pdf_tree):
    if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='StaticResultsFilename' for x in ast.walk(n.targets[0])):
        edits.append((n.lineno,n.end_lineno,'StaticResultsFilename = destination'))
body=changes(body,edits)
body=re.sub(r'\b([A-Za-z]\w*)\.get\(\)',lambda m:f'report[{m.group(1)!r}]',body)
body=presentation_to_data(body).replace('SaveErrorMessagesLabel','unused_status')
# Replace only the final UI status block with a normal exception-propagating save.
body=body[:body.rfind('try:\n    StaticResultsPage.save()')]+'StaticResultsPage.save()\n'
pdf_imports='"""Original static PDF layout, rendered without a file dialog."""\nimport os\nfrom pathlib import Path\nimport numpy as np\nimport Py3_MathModules as math\nfrom reportlab.lib.pagesizes import letter\nfrom reportlab.pdfgen import canvas\nimport reportlab.lib.colors as reportlabColors\n'
known.update({'canvas','letter','reportlabColors'})
(target/'static_calibration_report.py').write_text(pdf_imports+function('save_calibration_report',body,False),encoding='utf8')
print('Extracted parameter, calculation, and report modules')
