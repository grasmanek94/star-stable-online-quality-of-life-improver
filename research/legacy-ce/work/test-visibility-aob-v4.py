from pathlib import Path
import re,struct,json,ctypes,hashlib
R=Path(__file__).resolve().parents[1];W=R/'work';O=R/'outputs';E=O/'visibility-aob-v4-evidence';E.mkdir(exist_ok=True)
common=(W/'sso-visibility-aob-v4.lua').read_text()
raw=Path(r'C:\Users\Rafal\Desktop\StarStableOnline\Star Stable Online\client\SSOClient.exe').read_bytes()
pe=struct.unpack_from('<I',raw,0x3c)[0];opt=pe+24;size=struct.unpack_from('<I',raw,opt+56)[0];hsize=struct.unpack_from('<I',raw,opt+60)[0]
image=bytearray(size);image[:hsize]=raw[:hsize];sections=[]
for i in range(struct.unpack_from('<H',raw,pe+6)[0]):
 at=opt+struct.unpack_from('<H',raw,pe+20)[0]+40*i;vs,va,sz,fo=struct.unpack_from('<IIII',raw,at+8);ch=struct.unpack_from('<I',raw,at+36)[0];image[va:va+sz]=raw[fo:fo+sz];sections.append((va,max(vs,sz),ch))
definitions={}
for role,body in re.findall(r"(rider|horse|pet)=\{(.*?)\},?\n",common,re.S):
 definitions[role]={'pattern':re.search(r"pattern='([^']+)'",body)[1],'branch':int(re.search(r'branch=(\d+)',body)[1]),'call':int(re.search(r'call=(\d+)',body)[1])}
assert len(definitions)==3
matches={}
for role,d in definitions.items():
 rx=re.compile(b''.join(b'.' if p=='??' else re.escape(bytes.fromhex(p)) for p in d['pattern'].split()),re.DOTALL)
 hits=[a+m.start() for a,n,ch in sections if ch&0x20000000 for m in rx.finditer(image[a:a+n])]
 assert len(hits)==1,(role,hits);matches[role]=hits[0]
report={'binary_sha256':hashlib.sha256(raw).hexdigest(),'current_executable_pattern_matches':{k:hex(v) for k,v in matches.items()},'scenarios':[]}
def fixture(relocated):
 base=0x7ff600000000 if relocated else 0x140000000
 header=bytearray(image[:hsize])
 if relocated:struct.pack_into('<I',header,pe+8,0xaabbccdd)
 chunks=[{'address':base,'hex':header.hex()}];sites={};patmatches={}
 positions={'rider':0x600000,'horse':0x610000,'pet':0x620000} if relocated else matches
 wrapper=0x630000 if relocated else 0x1e6f50
 predicate=0x640000 if relocated else 0x799ad0;getter=0x650000 if relocated else 0xd10e0;setter=0x660000 if relocated else 0xd20b0
 def rel(buf,off,at,target):struct.pack_into('<i',buf,off+1,target-(at+off+5))
 for role,d in definitions.items():
  at=positions[role];b=bytearray(image[matches[role]:matches[role]+len(d['pattern'].split())])
  rel(b,d['call'],at,wrapper if role=='horse' else predicate)
  if role in ['rider','horse']:
   rel(b,17 if role=='rider' else 21,at,getter);rel(b,35 if role=='rider' else 39,at,setter)
  if relocated:
   if role=='rider':b[44:48]=struct.pack('<I',0x154);b[d['branch']+1]=0x31
   if role=='horse':b[3:7]=struct.pack('<I',0xaf0);b[d['branch']+1]=0x42
  chunks.append({'address':base+at,'hex':b.hex()})
  normal=at+d['branch']+2+b[d['branch']+1]
  prefix=bytes.fromhex('83 FF 04' if role=='rider' else '83 FB 04' if role=='horse' else 'F3 0F 58 D7')
  chunks.append({'address':base+normal,'hex':prefix.hex()})
  sites[role]={**d,'address':base+at};patmatches[role]=[base+at]
 wrapperbytes=bytearray(image[0x1e6f50:0x1e6f50+40]);rel(wrapperbytes,11,wrapper,0x670000 if relocated else 0x5f8cf0);rel(wrapperbytes,28,wrapper,predicate)
 if relocated:wrapperbytes[7:11]=struct.pack('<I',0xa8)
 chunks.append({'address':base+wrapper,'hex':wrapperbytes.hex()})
 dataRVA=next(a for a,n,ch in sections if not ch&0x20000000)
 return {'base':base,'size':size,'chunks':chunks,'sites':sites,'matches':patmatches,'wrapper':base+wrapper,'dataRVA':dataRVA}
def as_lua(value):
 if isinstance(value,str):return json.dumps(value)
 if isinstance(value,bool):return 'true' if value else 'false'
 if isinstance(value,(float,int)):return str(value)
 if isinstance(value,list):return '{'+','.join(as_lua(v) for v in value)+'}'
 if isinstance(value,dict):return '{'+','.join('['+as_lua(k)+']='+as_lua(v) for k,v in value.items())+'}'
 raise TypeError(type(value))
lua=ctypes.CDLL(r'C:\Program Files\Cheat Engine\lua53-64.dll');lua.luaL_newstate.restype=ctypes.c_void_p;lua.luaL_openlibs.argtypes=[ctypes.c_void_p];lua.luaL_loadstring.argtypes=[ctypes.c_void_p,ctypes.c_char_p];lua.luaL_loadstring.restype=ctypes.c_int;lua.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ssize_t,ctypes.c_void_p];lua.lua_pcallk.restype=ctypes.c_int;lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p];lua.lua_tolstring.restype=ctypes.c_char_p;lua.lua_close.argtypes=[ctypes.c_void_p]
template=(W/'test-visibility-aob-v4-fixture.lua').read_text()
scenarios=['all_restore','independent','pets_first','missing','duplicate','foreign_decoy','data_decoy','already_patched','normal_path_changed','helper_mismatch','wrapper_mismatch','symbol_collision','partial_failure_rollback','changed_context_disable','wrong_process_disable','syntaxcheck']
for relocated in [False,True]:
 model=fixture(relocated)
 for scenario in scenarios:
  source=template.replace('COMMON_QUOTED',as_lua(common)).replace('MODEL',as_lua(model)).replace('SCENARIO',as_lua(scenario))
  state=lua.luaL_newstate();lua.luaL_openlibs(state)
  try:
   code=lua.luaL_loadstring(state,source.encode())
   if code==0:code=lua.lua_pcallk(state,0,0,0,0,None)
   assert code==0,(relocated,scenario,lua.lua_tolstring(state,-1,None))
  finally:lua.lua_close(state)
  report['scenarios'].append({'image':'synthetic relocated/rebased' if relocated else 'current executable layout','scenario':scenario,'status':'pass'})
report.update({'status':'pass','scenario_count':len(report['scenarios']),'method':'Actual embedded Lua in isolated Lua 5.3 VM, mocked CE all-result AOB and Auto Assembler memory APIs; Python signatures searched in real PE executable sections','limitations':['Synthetic relocation is not a real future build','Does not prove future local-control semantics','CE scanner/assembler integration not executed by this test','No target-process writes or live FPS measurement'],'v3_visual_effect':'user confirmed horses/riders/pets hide while own remain visible','v4_live_visual_effect':'not yet tested'})
(E/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({'status':report['status'],'scenarios':report['scenario_count'],'real_binary_matches':report['current_executable_pattern_matches']}))
