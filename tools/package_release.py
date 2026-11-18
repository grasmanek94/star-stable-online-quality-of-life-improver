"""Collect matching CPack runtime/source archives into a local release bundle.

Build all four Release adapters with -Package, then create the CPack source ZIP.
Python is optional for this collector; normal build/install/CPack need no Python.
"""
from pathlib import Path, PurePosixPath
import argparse
import configparser
import hashlib
import json
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.search(r'project\(SSOVisibility\s+VERSION\s+(\d+\.\d+\.\d+(?:\.\d+)?)',
                    (ROOT/'CMakeLists.txt').read_text()).group(1)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--configuration', choices=('Release','Debug','RelWithDebInfo'), default='Release')
parser.add_argument('--source', type=Path, default=ROOT/f'out/packages/source/SSO-Visibility-Proxy-{VERSION}-source.zip')
parser.add_argument('--output', type=Path, default=ROOT/'out/releases'/VERSION)
args = parser.parse_args()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check_ini(data):
    ini = configparser.ConfigParser()
    ini.optionxform = str
    ini.read_string(data.decode('utf-8-sig'))
    if ini['General'].getint('DefaultPreset') != 8:
        raise RuntimeError('Unexpected default preset in package')

documentation = ('JOURNAL.md','ARCHITECTURE.md','LOADER_ADAPTERS.md','IMPLEMENTATION_STATUS.md',
                 'REQUEST_HISTORY.md','SESSION_HANDOFF.md','PE_METADATA.md','BUILD_VALIDATION.md','build-validation.json',
                 'updates/2026-11-18-client-647.md','updates/client-647-file-audit.json')
source = args.source.read_bytes()
with zipfile.ZipFile(args.source) as archive:
    if archive.testzip():
        raise RuntimeError('Source ZIP CRC failure')
    names = archive.namelist()
    if any('/out/' in n or '/.git/' in n or n.lower().endswith(('.exe','.dll','.pdb','.etl','.i64')) for n in names):
        raise RuntimeError('Build, repository-private or binary artifact in source ZIP')
    for required in ('CMakeLists.txt','config/SSOVisibility.ini','docs/IMPLEMENTATION_STATUS.md',
                     'docs/REQUEST_HISTORY.md','docs/SESSION_HANDOFF.md','tools/package_release.py',
                     'cmake/VersionResources.cmake','cmake/GenerateVersionResource.cmake',
                     'cmake/version.rc.in','tools/verify_pe_metadata.ps1','docs/PE_METADATA.md'):
        if not any(n.endswith('/'+required) for n in names):
            raise RuntimeError(f'Required source/handoff missing: {required}')
    source_documentation = {}
    for name in documentation:
        matches = [n for n in names if n.endswith('/docs/'+name)]
        if len(matches) != 1:
            raise RuntimeError(f'Missing/ambiguous source documentation: {name}')
        source_documentation[name] = archive.read(matches[0])
args.output.mkdir(parents=True, exist_ok=True)
shutil.copyfile(args.source, args.output/args.source.name)
manifest = dict(version=VERSION, configuration=args.configuration, default_preset=8,
    source_archive=dict(filename=args.source.name, sha256=sha(source)), adapters={}, live_1_2_verified=False,
    reference_client=json.loads((ROOT/'data/client-layout.json').read_text())['reference_client'], pe_version_gate=False)
bundle = args.output/f'SSO-Visibility-{VERSION}-all-loaders.zip'
with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
    target.writestr('README.md', f'# SSO Visibility {VERSION}\n\nChoose ONE adapter folder. Read its README.md and LOADER_ADAPTERS.md.\n'
        'Put SSOVisibility.ini beside the chosen module. Default8 hides remote riders/horses/pets.\n'
        'F5 enables, F6 restores, F7 reloads INI; Ctrl+Numpad0 all filters,1–9 presets.\n'
        'New1.2 live gameplay/loader/FPS validation remains pending. No third-party loader is bundled.\n'
        'Builds, hashes and isolated checks: docs/BUILD_VALIDATION.md. Request/repair handoff: docs/SESSION_HANDOFF.md.\n')
    for loader, filename in [('PROXY','opengl32.dll'),('RESHADE','SSOVisibility.addon64'),
                              ('ASI','SSOVisibility.asi'),('PLUGIN','SSOVisibility.dll')]:
        path = ROOT/'out/packages'/loader/args.configuration/f'SSO-Visibility-Proxy-{VERSION}-{loader}-win64.zip'
        with zipfile.ZipFile(path) as archive:
            if archive.testzip():
                raise RuntimeError(f'Runtime ZIP CRC failure: {loader}')
            prefix = PurePosixPath(path.stem)
            files = {PurePosixPath(n).relative_to(prefix).as_posix():n for n in archive.namelist() if not n.endswith('/')}
            required = {filename,'SSOVisibility.ini','README.md','LOADER_ADAPTERS.md',
                        'IMPLEMENTATION_STATUS.md','validation/proxy-symbols.json','read-proxy-state.ps1'}
            if not required <= files.keys() or any(n.startswith('..') for n in files):
                raise RuntimeError(f'Runtime package contents differ: {loader}')
            meta = json.loads(archive.read(files['validation/proxy-symbols.json']).decode('utf-8-sig'))
            binary = archive.read(files[filename])
            if sha(binary) != meta['dll_sha256'] or meta['module_name'] != filename:
                raise RuntimeError(f'Runtime module/metadata mismatch: {loader}')
            if len(meta['hooks']) != 21 or len(meta['categories']) != 14 or meta['config_size'] != 368:
                raise RuntimeError(f'Unexpected runtime layout: {loader}')
            check_ini(archive.read(files['SSOVisibility.ini']))
            for relative, member in files.items():
                target.writestr(loader+'/'+relative, archive.read(member))
        shutil.copyfile(path, args.output/path.name)
        manifest['adapters'][loader] = dict(module=filename, module_sha256=sha(binary),
            archive=path.name, archive_sha256=sha(path.read_bytes()))
    # Use the source snapshot, preserving unrelated uncommitted working-tree notes.
    for name, contents in source_documentation.items():
        target.writestr('docs/'+name, contents)
    target.writestr('manifest.json', json.dumps(manifest, indent=2)+'\n')
manifest['bundle'] = dict(filename=bundle.name, sha256=sha(bundle.read_bytes()))
(args.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
with zipfile.ZipFile(bundle) as archive:
    if archive.testzip():
        raise RuntimeError('Combined ZIP CRC failure')
print(json.dumps({'directory':str(args.output), 'bundle':bundle.name, 'source':args.source.name, 'adapters':4}))
