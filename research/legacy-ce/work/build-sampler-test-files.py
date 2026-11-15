from pathlib import Path
import json,struct,hashlib,xml.etree.ElementTree as ET,zipfile
R=Path(r'C:\Users\Rafal\Documents\Codex\2026-11-15\tr');W=R/'work';O=R/'outputs'
exe=Path(r'C:\Users\Rafal\Desktop\StarStableOnline\Star Stable Online\client\SSOClient.exe').read_bytes()
digest=hashlib.sha256(exe).hexdigest()
assert digest=='3cec805521c70b64f1a33c5a0efa67679b8112dacbe9594ab1b47301b4d3de8d'
pe=struct.unpack_from('<I',exe,0x3c)[0];opt=pe+24;sz=struct.unpack_from('<H',exe,pe+20)[0]
sections=[]
for i in range(struct.unpack_from('<H',exe,pe+6)[0]):
    off=opt+sz+i*40
    vs,va,rs,fo=struct.unpack_from('<IIII',exe,off+8)
    sections.append((va,max(vs,rs),fo))
def read(rva,n):
    if rva<struct.unpack_from('<I',exe,opt+60)[0]:return exe[rva:rva+n]
    for va,size,fo in sections:
        if va<=rva and rva+n<=va+size:return exe[fo+rva-va:fo+rva-va+n]
    raise ValueError(hex(rva))
def hx(b):return b.hex(' ').upper()
deep=json.loads((W/'ida-sampler-deep.json').read_text())
for key,value in deep['sites'].items():assert read(int(key,16),48)==bytes.fromhex(value)
assert read(0x6842a4,2)==b'\x74\x29' and read(0x684a06,2)==b'\x74\x1e'
sites=[('QuatTouchGate',0x6842a4,0x6842a1),('VectorTouchGate',0x684a06,0x684a03)]
timestamp_off=pe+8;image_size_off=opt+56
header_guards=[f'assert(SSOClient.exe+{timestamp_off:08X},{hx(read(timestamp_off,4))})',f'assert(SSOClient.exe+{image_size_off:08X},{hx(read(image_size_off,4))})']
def script(selected):
    chosen=[sites[i] for i in selected]
    lines=['// EXPERIMENTAL performance A/B patch; no live-game crash guarantee.', '// SSOClient.exe 645.348067 / Stellar 645 only.', '// SHA256: '+digest.upper(), '// Offline differential emulation: 630 input cases matched.', '// ENABLE: one-byte JZ -> JMP per selected loop; DISABLE restores JZ.', '// The key searches, interpolation, guards and function prologues remain intact.', '// All addresses are module-relative, so ASLR is supported.','']
    lines.extend(f'define({name},SSOClient.exe+{gate:08X})' for name,gate,_ in chosen)
    for mode in ['ENABLE','DISABLE']:
        lines.extend(['',f'[{mode}]'])
        lines.extend(header_guards)
        for name,gate,start in chosen:
            context=bytearray(read(start,48))
            if mode=='DISABLE':context[gate-start]=0xeb
            lines.append(f'assert(SSOClient.exe+{start:08X},{hx(context)})')
        lines.append('')
        for name,gate,start in chosen:
            lines.extend([name+':','  db '+('EB' if mode=='ENABLE' else '74')])
    return '\n'.join(lines)+'\n'
combined=script([0,1]);(O/'Star-Stable-sampler-loop-test.cea').write_text(combined,encoding='utf-8')
table=ET.Element('CheatTable',{'CheatEngineTableVersion':'45'})
entries=ET.SubElement(table,'CheatEntries')
for i,(label,selected) in enumerate([('TEST: skip BOTH sampler touch loops (build 645.348067)',[0,1]),('TEST: skip quaternion touch loop ONLY',[0]),('TEST: skip vector touch loop ONLY',[1])],1):
    entry=ET.SubElement(entries,'CheatEntry')
    ET.SubElement(entry,'ID').text=str(i)
    ET.SubElement(entry,'Description').text='"'+label+'"'
    ET.SubElement(entry,'VariableType').text='Auto Assembler Script'
    ET.SubElement(entry,'AssemblerScript').text=script(selected)
ET.SubElement(table,'UserdefinedSymbols')
ET.indent(table,space='  ')
ET.ElementTree(table).write(O/'Star-Stable-sampler-loop-test.CT',encoding='utf-8',xml_declaration=True)
results=json.loads((W/'sampler-emulation-results.json').read_text())
(O/'Sampler-loop-emulation-results.json').write_text(json.dumps(results,indent=2))
evidence={'binary_sha256':digest,'pe_timestamp_offset':hex(timestamp_off),'pe_timestamp':hex(struct.unpack_from('<I',exe,timestamp_off)[0]),'size_of_image_offset':hex(image_size_off),'size_of_image':hex(struct.unpack_from('<I',exe,image_size_off)[0]),'sites':[{'name':name,'gate_rva':hex(gate),'original':hx(read(gate,2)),'enabled':hx(b'\xeb'+read(gate+1,1)),'guard_rva':hex(start),'guard_original':hx(read(start,48))} for name,gate,start in sites],'live_game_modified':False,'ce_autoassembler_executed':False}
(O/'Sampler-loop-patch-evidence.json').write_text(json.dumps(evidence,indent=2))
print(json.dumps({'created':['Star-Stable-sampler-loop-test.cea','Star-Stable-sampler-loop-test.CT'],'timestamp_offset':hex(timestamp_off),'image_size_offset':hex(image_size_off),'cases':results['cases']}))
