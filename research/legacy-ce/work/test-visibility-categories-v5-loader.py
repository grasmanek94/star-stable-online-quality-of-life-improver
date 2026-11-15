"""Execute the actual loader in mock CE memory; no live process operations."""
from pathlib import Path
import ctypes as ct,json,struct,hashlib
R=Path(__file__).resolve().parents[1];W=R/'work';E=R/'outputs/visibility-categories-v5-evidence'
raw=Path(r'C:\Users\Rafal\Desktop\StarStableOnline\Star Stable Online\client\SSOClient.exe').read_bytes()
pe=struct.unpack_from('<I',raw,60)[0];opt=pe+24;hsize=struct.unpack_from('<I',raw,opt+60)[0]
sites=json.loads((W/'visibility-categories-v5-sites.json').read_text());base=0x140000000
model={'base':base,'pe':pe,'chunks':[{'address':base,'hex':raw[:hsize].hex()}],'sites':{}}
for name,d in sites.items():
    a=base+int(d['rva'],16);model['chunks'].append({'address':a,'hex':d['window']});model['sites'][name]={'address':a,'hex':d['window']}
lua=ct.CDLL(r'C:\Program Files\Cheat Engine\lua53-64.dll');lua.luaL_newstate.restype=ct.c_void_p
for name,args,result in [('luaL_openlibs',[ct.c_void_p],None),('luaL_loadstring',[ct.c_void_p,ct.c_char_p],ct.c_int),('lua_pcallk',[ct.c_void_p,ct.c_int,ct.c_int,ct.c_int,ct.c_ssize_t,ct.c_void_p],ct.c_int),('lua_tolstring',[ct.c_void_p,ct.c_int,ct.c_void_p],ct.c_char_p),('lua_close',[ct.c_void_p],None)]:
    fn=getattr(lua,name);fn.argtypes=args;fn.restype=result
def literal(x):
    if isinstance(x,str):return json.dumps(x)
    if isinstance(x,(int,float)):return str(x)
    if isinstance(x,list):return '{'+','.join(literal(i) for i in x)+'}'
    return '{'+','.join('['+literal(k)+']='+literal(v) for k,v in x.items())+'}'
loader=(W/'sso-visibility-categories-v5.lua').read_text()
definitions=[{'name':n,'pattern':d['pattern'],'patch_offset':d['patch_offset'],'target_rva':int(d['target_rva'],16)} for n,d in sites.items()]
fixture=(W/'test-visibility-categories-v5-loader.lua').read_text()
scenarios=['enable_restore_reuse','missing','duplicate','own_layout_reject','new_build_reject','far_cave_reject','compile_failure','symbol_conflict','partial_failure','changed_context_disable','wrong_process_disable']
results=[]
for scenario in scenarios:
    source='local SITE_DEFINITIONS='+literal(definitions)+'\nlocal NATIVE_C="fixture"\n'+loader+'\n'+fixture.replace('MODEL',literal(model)).replace('SCENARIO',literal(scenario))
    state=lua.luaL_newstate();lua.luaL_openlibs(state)
    try:
        status=lua.luaL_loadstring(state,source.encode())
        if status==0:status=lua.lua_pcallk(state,0,1,0,0,None)
        error=lua.lua_tolstring(state,-1,None)
        assert status==0,(scenario,error.decode()if error else None)
        assert error==b'pass'
    finally:lua.lua_close(state)
    results.append({'scenario':scenario,'status':'pass'})
(E/'loader-validation.json').write_text(json.dumps({'status':'pass','scenario_count':len(results),'results':results,'loader_sha256':hashlib.sha256(loader.encode()).hexdigest(),'method':'Actual Lua loader in isolated Lua 5.3, real baseline PE headers/windows, mocked CE APIs','limitations':['Compiler/scanner/Auto Assembler integration is mocked','No live game writes or FPS measurement']},indent=2))
print(json.dumps({'status':'pass','loader_scenarios':len(results)}))
