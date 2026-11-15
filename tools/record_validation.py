"""Record successful per-configuration CTest reports and matching module hashes.

Optional standard-library maintenance tool. Run builds with -AsmTests first;
normal builds and CPack do not require Python.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--preset', default='vs2026-x64')
parser.add_argument('--output', type=Path, default=ROOT/'docs/build-validation.json')
args = parser.parse_args()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def imports(path):
    data = path.read_bytes()
    nt = struct.unpack_from('<I', data, 60)[0]
    optional = nt + 24
    section_start = optional + struct.unpack_from('<H', data, nt+20)[0]
    sections = []
    for index in range(struct.unpack_from('<H', data, nt+6)[0]):
        virtual_size, rva, raw_size, raw = struct.unpack_from('<IIII', data, section_start+40*index+8)
        sections.append((rva, max(virtual_size, raw_size), raw))
    def offset(rva):
        for start, size, raw in sections:
            if start <= rva < start+size:
                return raw+rva-start
        raise ValueError(f'Unmapped import RVA: {rva:x}')
    at = offset(struct.unpack_from('<I', data, optional+120)[0])
    result = []
    while any(data[at:at+20]):
        name = offset(struct.unpack_from('<I', data, at+12)[0])
        result.append(data[name:data.index(0, name)].decode('ascii'))
        at += 20
    return result

matrix = [('PROXY', args.preset, c) for c in ('Release', 'Debug', 'RelWithDebInfo')]
matrix += [('RESHADE', args.preset+'-reshade', c) for c in ('Release', 'Debug')]
matrix += [(mode, args.preset+'-'+mode.lower(), 'Release') for mode in ('ASI', 'PLUGIN')]
builds = []
for loader, preset, configuration in matrix:
    folder = ROOT/'out/build'/preset/'bin'/configuration
    validation = folder/'validation'
    meta = json.loads((validation/'proxy-symbols.json').read_text(encoding='utf-8-sig'))
    module = folder/meta['module_name']
    digest = sha(module)
    if digest != meta['dll_sha256']:
        raise RuntimeError(f'Module/metadata hash mismatch: {module}')
    dependencies = imports(module)
    if not {name.upper() for name in dependencies} <= {'KERNEL32.DLL','USER32.DLL'}:
        raise RuntimeError(f'Unexpected native dependencies: {dependencies}')
    suite = ET.parse(validation/'ctest.xml').getroot()
    cases = suite.findall('.//testcase')
    expected = {'runtime', 'presets', 'classifier', 'generated_assets', 'compiled_assembly',
                'forwarding' if loader == 'PROXY' else 'plugin_loader'}
    if {case.attrib['name'] for case in cases} != expected or any(
            case.find('failure') is not None or case.find('error') is not None or
            case.find('skipped') is not None or case.get('status') != 'run' for case in cases):
        raise RuntimeError(f'Missing/failed/skipped CTest suites: {validation}')
    log = (validation/'ctest.log').read_text(encoding='utf-8')
    runtime = re.search(r'NATIVE_PROXY_TESTS_PASS (\d+); (\d+) hooks', log)
    if not runtime or 'PRESET_TESTS_PASS' not in log:
        raise RuntimeError(f'Native test success markers absent: {validation}')
    classifier = json.loads((validation/'classifier.json').read_text())
    assembly = json.loads((validation/'compiled-assembly.json').read_text())
    if classifier['status'] != 'pass' or assembly['status'] != 'pass' or assembly['dll_sha256'] != digest:
        raise RuntimeError(f'Classifier/assembly result mismatch: {validation}')
    builds.append(dict(loader=loader, preset=preset, configuration=configuration,
        module=module.name, dll_sha256=digest, imports=dependencies, config_rva=meta['symbols']['g_config']['rva'],
        config_size=meta['config_size'], hooks=len(meta['hooks']), categories=len(meta['categories']),
        ctest_suites=len(cases), suite_names=sorted(expected), runtime_scenarios=int(runtime[1]),
        classifier_cases=classifier['case_count'], compiled_wrapper_cases=assembly['wrapper_execution_cases'],
        compiled_forwarder_cases=assembly['forwarder_execution_cases'],
        junit_sha256=sha(validation/'ctest.xml'), log_sha256=sha(validation/'ctest.log')))

inputs = {}
for name in ('src', 'include', 'generated', 'data', 'config', 'cmake'):
    for path in sorted((ROOT/name).rglob('*')):
        if path.is_file():
            inputs[path.relative_to(ROOT).as_posix()] = sha(path)
for name in ('CMakeLists.txt', 'CMakePresets.json'):
    inputs[name] = sha(ROOT/name)
report = dict(version='1.2.0', recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    location='linked repository working tree', builds=builds, native_input_hashes=inputs,
    scope='Fresh local helper-process CTest and linked assembly results; no live 1.2 game/loader/FPS validation.',
    not_run=['separate VS2022 installation', 'remote GitHub Actions (disabled by request)',
             'live 1.2 gameplay, GPU lifetime, ReShade/ASI and FPS checks'])
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'report':str(args.output), 'builds':len(builds), 'suites_passed':sum(b['ctest_suites'] for b in builds)}))
