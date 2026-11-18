"""Collect minimal player ZIPs and a buildable source ZIP.

Build the four Release adapters with -Package. Use --create-source in a Git
checkout to archive committed build files, or supply a minimal CPack source ZIP.
Python/Git are maintenance tools; the native build and CPack need neither.
"""
from pathlib import Path, PurePosixPath
import argparse
import configparser
import hashlib
import io
import json
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.search(r'project\(SSOVisibility\s+VERSION\s+(\d+\.\d+\.\d+(?:\.\d+)?)',
                    (ROOT/'CMakeLists.txt').read_text()).group(1)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--configuration', choices=('Release','Debug','RelWithDebInfo'), default='Release')
parser.add_argument('--preset', default='vs2026-x64', help='Base build preset for private verification metadata')
parser.add_argument('--source', type=Path, default=ROOT/f'out/packages/source/SSO-Visibility-Proxy-{VERSION}-source.zip')
parser.add_argument('--create-source', action='store_true', help='Create the source ZIP from committed Git build files')
parser.add_argument('--output', type=Path, default=ROOT/'out/releases'/VERSION)
args = parser.parse_args()

SOURCE_DIRS = {'cmake','config','data','generated','include','src','tests','tools'}
SOURCE_FILES = {'CMakeLists.txt','CMakePresets.json','build.cmd','README.md','README-DEVELOPERS.md',
                '.editorconfig','.gitattributes','.gitignore'}
ADAPTERS = [('PROXY','opengl32.dll',''),('RESHADE','SSOVisibility.addon64','-reshade'),
            ('ASI','SSOVisibility.asi','-asi'),('PLUGIN','SSOVisibility.dll','-plugin')]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def source_member(name):
    p = PurePosixPath(name)
    return (not p.is_absolute() and '..' not in p.parts and
            (p.parts[0] in SOURCE_DIRS or name in SOURCE_FILES or
             (len(p.parts)==1 and p.name.upper().startswith(('LICENSE','COPYING')))) and
            not any(part in {'__pycache__','out','.git'} for part in p.parts) and
            p.suffix.lower() not in {'.pyc','.log','.exe','.dll','.asi','.addon64','.pdb','.etl','.i64'})

def check_ini(data):
    ini = configparser.ConfigParser()
    ini.optionxform = str
    ini.read_string(data.decode('utf-8-sig'))
    if ini['General'].getint('DefaultPreset') != 8:
        raise RuntimeError('Unexpected default preset in package')

if args.create_source:
    committed = subprocess.check_output(['git','archive','--format=zip','HEAD'], cwd=ROOT)
    args.source.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(committed)) as source, zipfile.ZipFile(args.source,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as target:
        for name in source.namelist():
            if not name.endswith('/') and source_member(name):
                target.writestr(f'SSO-Visibility-Proxy-{VERSION}-source/'+name,source.read(name))

source_bytes = args.source.read_bytes()
with zipfile.ZipFile(args.source) as archive:
    if archive.testzip():
        raise RuntimeError('Source ZIP CRC failure')
    names = [n for n in archive.namelist() if not n.endswith('/')]
    prefix = '' if 'CMakeLists.txt' in names else names[0].split('/')[0]+'/'
    files = {n.removeprefix(prefix):n for n in names}
    if any(not n.startswith(prefix) for n in names) or not all(source_member(n) for n in files):
        raise RuntimeError('Source ZIP contains unrelated docs, research, AI notes or binary/build files')
    required = {'CMakeLists.txt','CMakePresets.json','build.cmd','README.md','README-DEVELOPERS.md',
                'config/SSOVisibility.ini','data/client-layout.json','generated/layout_specs.inc',
                'cmake/VersionResources.cmake','cmake/GenerateVersionResource.cmake','cmake/version.rc.in',
                'tools/write_metadata.ps1','tools/verify_pe_metadata.ps1','tools/package_release.py'}
    if not required <= files.keys():
        raise RuntimeError(f'Required source files missing: {sorted(required-files.keys())}')
    reference = json.loads(archive.read(files['data/client-layout.json']))['reference_client']
    # Verify against the tested tree when its optional local report is present.
    validation = ROOT/'docs/build-validation.json'
    if validation.is_file():
        report = json.loads(validation.read_text())
        for name,digest in report['native_input_hashes'].items():
            if name not in files or sha(archive.read(files[name]).replace(b'\r\n',b'\n')) != digest:
                raise RuntimeError(f'Source ZIP differs from tested native input: {name}')

args.output.mkdir(parents=True, exist_ok=True)
shutil.copyfile(args.source,args.output/args.source.name)
manifest = dict(version=VERSION, configuration=args.configuration, default_preset=8,
    source_archive=dict(filename=args.source.name,sha256=sha(source_bytes)), adapters={},
    live_1_2_verified=False, reference_client=reference, pe_version_gate=False,
    runtime_contents='chosen module and SSOVisibility.ini only')
bundle = args.output/f'SSO-Visibility-{VERSION}-all-loaders.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as target:
    for loader,filename,suffix in ADAPTERS:
        path = ROOT/'out/packages'/loader/args.configuration/f'SSO-Visibility-Proxy-{VERSION}-{loader}-win64.zip'
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if archive.testzip() or len(names)!=2 or set(names)!={filename,'SSOVisibility.ini'}:
                raise RuntimeError(f'Runtime ZIP must contain exactly the module and INI: {loader}')
            # Private build metadata stays beside the build, outside player ZIPs.
            folder = ROOT/'out/build'/(args.preset+suffix)/'bin'/args.configuration
            meta = json.loads((folder/'validation/proxy-symbols.json').read_text(encoding='utf-8-sig'))
            binary = archive.read(filename)
            if sha(binary)!=meta['dll_sha256'] or meta['module_name']!=filename:
                raise RuntimeError(f'Runtime module/metadata mismatch: {loader}')
            if len(meta['hooks'])!=21 or len(meta['categories'])!=14 or meta['config_size']!=368:
                raise RuntimeError(f'Unexpected runtime layout: {loader}')
            check_ini(archive.read('SSOVisibility.ini'))
            target.writestr(loader+'/'+filename,binary)
            target.writestr(loader+'/SSOVisibility.ini',archive.read('SSOVisibility.ini'))
        shutil.copyfile(path,args.output/path.name)
        manifest['adapters'][loader] = dict(module=filename,module_sha256=sha(binary),
            archive=path.name,archive_sha256=sha(path.read_bytes()))
manifest['bundle'] = dict(filename=bundle.name,sha256=sha(bundle.read_bytes()))
(args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
with zipfile.ZipFile(bundle) as archive:
    if archive.testzip() or len(archive.namelist())!=8:
        raise RuntimeError('Combined ZIP must contain exactly four module/INI pairs')
print(json.dumps({'directory':str(args.output),'bundle':bundle.name,'source':args.source.name,
                  'adapters':4,'files_per_runtime_zip':2,'files_in_bundle':8}))
