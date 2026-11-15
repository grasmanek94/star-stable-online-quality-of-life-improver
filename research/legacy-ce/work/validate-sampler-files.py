"""Validate this table's restricted AA directive subset against the original PE.

This is a static model, not an invocation of the Cheat Engine assembler.
"""
from pathlib import Path
import re,json,xml.etree.ElementTree as ET

R=Path(__file__).resolve().parents[1];O=R/'outputs'
raw=Path(r'C:\Users\Rafal\Desktop\StarStableOnline\Star Stable Online\client\SSOClient.exe').read_bytes()
import struct,hashlib
assert hashlib.sha256(raw).hexdigest()=='3cec805521c70b64f1a33c5a0efa67679b8112dacbe9594ab1b47301b4d3de8d'
pe=struct.unpack_from('<I',raw,0x3c)[0];opt=pe+24
sections=[]
for i in range(struct.unpack_from('<H',raw,pe+6)[0]):
    off=opt+struct.unpack_from('<H',raw,pe+20)[0]+i*40
    va,size,fo=struct.unpack_from('<III',raw,off+12)
    sections.append((va,size,fo))
def original(address):
    if address<struct.unpack_from('<I',raw,opt+60)[0]:return raw[address]
    for va,size,fo in sections:
        if va<=address<va+size:return raw[fo+address-va]
    raise AssertionError(f'Unmapped RVA {address:x}')
def run(script,enable,changes):
    changes=dict(changes);symbols={};active=False;checks=[];writes=[];location=None
    def address(value):
        if value in symbols:return symbols[value]
        m=re.fullmatch(r'SSOClient\.exe\+([0-9A-F]+)',value)
        assert m,value
        return int(m[1],16)
    for line in script.splitlines():
        line=line.strip()
        if not line or line.startswith('//'):continue
        m=re.fullmatch(r'define\((\w+),([^,]+)\)',line)
        if m:
            symbols[m[1]]=address(m[2]);continue
        if line.startswith('['):
            assert line in ['[ENABLE]','[DISABLE]']
            active=line==('[ENABLE]' if enable else '[DISABLE]');continue
        if not active:continue
        m=re.fullmatch(r'assert\(([^,]+),([0-9A-F ]+)\)',line)
        if m:
            assert not writes,'Assertion after writes'
            checks.append((address(m[1]),bytes.fromhex(m[2])));continue
        if line.endswith(':'):
            location=address(line[:-1]);continue
        m=re.fullmatch(r'db ([0-9A-F]{2})',line)
        assert m and location is not None,line
        writes.append((location,int(m[1],16)));location+=1
    assert len(checks)>=3 and writes
    for start,expected in checks:
        actual=bytes(changes.get(start+i,original(start+i)) for i in range(len(expected)))
        if actual!=expected:raise ValueError(f'Assertion mismatch at {start:x}')
    for at,value in writes:
        if value==original(at):changes.pop(at,None)
        else:changes[at]=value
    return changes,checks

root=ET.parse(O/'Star-Stable-sampler-loop-test.CT').getroot()
entries=root.findall('./CheatEntries/CheatEntry')
assert len(entries)==3
assert root.find('LuaScript') is None
reports=[]
for i,entry in enumerate(entries):
    assert entry.find('Active') is None
    script=entry.findtext('AssemblerScript')
    expected=({0x6842a4:0xeb,0x684a06:0xeb} if i==0 else {0x6842a4 if i==1 else 0x684a06:0xeb})
    enabled,checks=run(script,True,{})
    assert enabled==expected
    disabled,_=run(script,False,enabled)
    assert disabled=={}
    for bad in [{checks[0][0]:original(checks[0][0])^1},{checks[1][0]:original(checks[1][0])^1},{checks[-1][0]+10:original(checks[-1][0]+10)^1},enabled]:
        try:run(script,True,bad)
        except ValueError:pass
        else:raise AssertionError('Failed to reject changed build/context/state')
    if i==0:assert script==(O/'Star-Stable-sampler-loop-test.cea').read_text()
    reports.append({'variant':entry.findtext('Description').strip('"'),'changed_rvas':[hex(x) for x in enabled],'enable_only_expected_bytes':True,'disable_restores_original':True,'mismatched_timestamp_image_size_context_and_state_rejected':True})
report={'status':'pass','method':'Static interpretation of only define/assert/db directives used by the delivered scripts; not the CE assembler','variants':reports,'table_contains_lua':False,'entries_start_disabled':True,'live_game_modified':False}
(O/'Sampler-loop-static-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
