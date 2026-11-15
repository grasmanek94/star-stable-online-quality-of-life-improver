from pathlib import Path
import hashlib,json,re,struct,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];W=ROOT/'work';O=ROOT/'outputs';E=O/'visibility-categories-v5-evidence';E.mkdir(exist_ok=True)
c=(W/'sso-visibility-categories-v5.c').read_text(encoding='utf8')
loader=(W/'sso-visibility-categories-v5.lua').read_text(encoding='utf8')
sites=json.loads((W/'visibility-categories-v5-sites.json').read_text())
revision=hashlib.sha256((c+loader+json.dumps(sites,sort_keys=True)).encode()).hexdigest()
loader=loader.replace("v5-20261115-1",'v5-'+revision[:20])
defs=['local SITE_DEFINITIONS={']
for name,d in sites.items():
    defs.append("{name='%s',pattern='%s',patch_offset=%d,target_rva=%s},"%(name,d['pattern'],d['patch_offset'],d['target_rva']))
defs.append('}')
embedded='local NATIVE_C=[==[\n'+c+'\n]==]\n'+'\n'.join(defs)+'\n'+loader
aa='// Experimental expanded visibility; baseline 645.348067. Disable v2/v3/v4 first.\n'
for action in ['enable','disable']:
    aa+='\n['+action.upper()+']\n{$lua}\nif syntaxcheck then return end\n'+embedded+"\nrun('"+action+"')\n{$asm}\n"
root=ET.Element('CheatTable',{'CheatEngineTableVersion':'45'});entries=ET.SubElement(root,'CheatEntries')
master=ET.SubElement(entries,'CheatEntry');ET.SubElement(master,'ID').text='1'
ET.SubElement(master,'Description').text='"MASTER v5: object visibility (1=hide, 0=normal) ['+revision[:8]+']"'
ET.SubElement(master,'Options',{'moHideChildren':'1'})
ET.SubElement(master,'VariableType').text='Auto Assembler Script';ET.SubElement(master,'AssemblerScript').text=aa
children=ET.SubElement(master,'CheatEntries')
labels=['Other players: horses','Other players: characters','Other players: pets','NPC pets / ambient animals (name based)','NPC actors (fallback for unclassified NPCs)','NPC horses (name based)','Standalone riderless CPXHorse objects','Buyable / display horses','Coins / collectible visuals','Quest ? / ! markers','NPC floating text / speech bubbles']
for i,label in enumerate(labels):
    e=ET.SubElement(children,'CheatEntry');ET.SubElement(e,'ID').text=str(100+i)
    ET.SubElement(e,'Description').text='"'+label+'"';ET.SubElement(e,'VariableType').text='Byte'
    ET.SubElement(e,'Address').text=f'SSO5_CONFIG+{16+i:X}'
    ET.SubElement(e,'DropDownList',{'ReadOnly':'1','DescriptionOnly':'0','DisplayValueAsItem':'1'}).text='0:Normal\n1:Hide'
    sub=ET.SubElement(e,'CheatEntries');stat=ET.SubElement(sub,'CheatEntry');ET.SubElement(stat,'ID').text=str(200+i)
    ET.SubElement(stat,'Description').text='"Native hide decisions (calls, not actor count)"'
    ET.SubElement(stat,'VariableType').text='8 Bytes';ET.SubElement(stat,'Address').text=f'SSO5_CONFIG+{256+i*8:X}'
ET.SubElement(root,'UserdefinedSymbols');ET.indent(root,space='  ')
ET.ElementTree(root).write(O/'Star-Stable-object-visibility-v5.CT',encoding='utf-8',xml_declaration=True)
(O/'Star-Stable-object-visibility-v5.cea').write_text(aa,encoding='utf8')
raw=Path(r'C:\Users\Rafal\Desktop\StarStableOnline\Star Stable Online\client\SSOClient.exe').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='3cec805521c70b64f1a33c5a0efa67679b8112dacbe9594ab1b47301b4d3de8d'
pe=struct.unpack_from('<I',raw,60)[0];opt=pe+24;sections=[]
for i in range(struct.unpack_from('<H',raw,pe+6)[0]):
    at=opt+struct.unpack_from('<H',raw,pe+20)[0]+40*i;vs,va,sz,fo=struct.unpack_from('<IIII',raw,at+8);ch=struct.unpack_from('<I',raw,at+36)[0]
    if ch&0x20000000:sections.append((va,raw[fo:fo+sz]))
matches={}
for name,d in sites.items():
    rx=re.compile(b''.join(b'.' if p=='??' else re.escape(bytes.fromhex(p)) for p in d['pattern'].split()),re.DOTALL)
    hits=[va+m.start() for va,b in sections for m in rx.finditer(b)]
    assert hits==[int(d['rva'],16)],(name,hits)
    matches[name]=hex(hits[0])
(E/'static-validation.json').write_text(json.dumps({'revision':revision,'binary_sha256':hashlib.sha256(raw).hexdigest(),'all_unique_in_executable_sections':True,'matches':matches,'master_scripts':1,'default_hide_flags':[1]*11,'live_test':'pending; v4 confirmation does not validate v5'},indent=2))
print(json.dumps({'table':'Star-Stable-object-visibility-v5.CT','category_controls':len(labels),'unique_native_sites':len(matches),'revision':revision[:20]}))
