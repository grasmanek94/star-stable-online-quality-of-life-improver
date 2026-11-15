"""Execute the actual Lua-generated wrappers in an isolated x64 emulator.

CE's assembler is represented by Keystone with CE hexadecimal constants made
explicit. Native helper/classifier calls are modeled; classifier C has its own
actual-native tests. Nothing attaches to the running game.
"""
from pathlib import Path
import ctypes as ct,json,re,struct,sys
R=Path(__file__).resolve().parents[1];W=R/'work';E=R/'outputs/visibility-categories-v5-evidence'
sys.path[:0]=[str(W/'sampler-libs'),str(W/'v5-libs')]
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *
lua=ct.CDLL(r'C:\Program Files\Cheat Engine\lua53-64.dll')
lua.luaL_newstate.restype=ct.c_void_p
for name,args,result in [('luaL_openlibs',[ct.c_void_p],None),('luaL_loadstring',[ct.c_void_p,ct.c_char_p],ct.c_int),('lua_pcallk',[ct.c_void_p,ct.c_int,ct.c_int,ct.c_int,ct.c_ssize_t,ct.c_void_p],ct.c_int),('lua_tolstring',[ct.c_void_p,ct.c_int,ct.c_void_p],ct.c_char_p),('lua_close',[ct.c_void_p],None)]:
    fn=getattr(lua,name);fn.argtypes=args;fn.restype=result
loader=(W/'sso-visibility-categories-v5.lua').read_text()
def lua_eval(source):
    state=lua.luaL_newstate();lua.luaL_openlibs(state)
    try:
        rc=lua.luaL_loadstring(state,source.encode())
        if rc==0:rc=lua.lua_pcallk(state,0,1,0,0,None)
        if rc:raise RuntimeError(lua.lua_tolstring(state,-1,None).decode())
        return lua.lua_tolstring(state,-1,None).decode()
    finally:lua.lua_close(state)
BASE=0x140000000;CODE=0x150000000;STACK=0x70000000;STOP=0x71000000;ACTOR=0x72000000
FN=CODE+0x800;CLASSIFIER=CODE+0x100;SAVED_MASK=0x0123456789ABCD00
sites=json.loads((W/'visibility-categories-v5-sites.json').read_text())
ks=Ks(KS_ARCH_X86,KS_MODE_64)
def assemble(text,address):
    lines=[]
    for line in text.splitlines():
        if line.startswith('label('):continue
        if re.fullmatch(r'[A-F0-9]+:',line):continue
        if line.endswith(':'):lines.append(line);continue
        mnemonic,_,operand=line.partition(' ')
        operand=re.sub(r'(?<!\w)([0-9A-F]+)(?!\w)',lambda m:'0x'+m[1],operand)
        lines.append(mnemonic+' '+operand)
    data,_=ks.asm('\n'.join(lines),address)
    return bytes(data)
results=[];exports={}
gpr=[UC_X86_REG_RAX,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11,UC_X86_REG_RBX,UC_X86_REG_RBP,UC_X86_REG_RSI,UC_X86_REG_RDI,UC_X86_REG_R12,UC_X86_REG_R13,UC_X86_REG_R14,UC_X86_REG_R15]
xmm=[globals()[f'UC_X86_REG_XMM{i}'] for i in range(16)]
for si,(name,d) in enumerate(sites.items()):
    address=CODE+0x1000+si*0x800;target=BASE+int(d['target_rva'],16)
    p="{name=%s,target=%d}"%(json.dumps(name),target)
    state="{functions={actor=%d,visual=%d,flag=%d}}"%(FN,FN+8,FN+16)
    text=lua_eval(loader+f'\nreturn wrapper({p},{address},{state},{si+1})')
    binary=assemble(text,address);assert len(binary)<0x800
    exports[name]={'address':hex(address),'target':hex(target),'ce_assembly':text,'machine_code':binary.hex(' ')}
    for original in [0,1]:
      for hide in [0,1]:
        u=Uc(UC_ARCH_X86,UC_MODE_64)
        u.mem_map(BASE,0x2000000);u.mem_map(CODE,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000);u.mem_map(ACTOR,0x1000)
        u.mem_write(address,binary);u.mem_write(FN,struct.pack('<QQQ',CLASSIFIER,CLASSIFIER,CLASSIFIER))
        sp=STACK+0xEFF8;u.mem_write(sp,struct.pack('<Q',STOP));u.reg_write(UC_X86_REG_RSP,sp)
        for i,r in enumerate(gpr):u.reg_write(r,SAVED_MASK+i)
        for i,r in enumerate(xmm):u.reg_write(r,0x0123456789ABCDEF0011223344556677+i)
        for r in [UC_X86_REG_RCX,UC_X86_REG_RSI,UC_X86_REG_RDI,UC_X86_REG_RBX]:u.reg_write(r,ACTOR)
        expected={r:u.reg_read(r) for r in gpr+xmm};seen=[]
        def hook(uc,at,n,_):
            if at==STOP:uc.emu_stop();return
            if at in [target,CLASSIFIER]:
                rsp=uc.reg_read(UC_X86_REG_RSP);assert rsp%16==8,(name,'alignment',hex(rsp))
                if at==target:
                    seen.append('original')
                    # A tail-called void helper must see the caller's original
                    # return address/shadow space/stack arguments unchanged.
                    if name not in ['rider','horse','pet','skinGate','meshGate']:
                        assert rsp==sp,(name,'stack argument base changed')
                    uc.reg_write(UC_X86_REG_RAX,SAVED_MASK|original)
                else:
                    seen.append('classifier')
                    # Model the full set of volatile registers a C helper may
                    # clobber, including SIMD argument registers.
                    for r in gpr[:7]:uc.reg_write(r,0xDEAD0000)
                    for r in xmm[:6]:uc.reg_write(r,0xDEAD0000)
                    uc.reg_write(UC_X86_REG_RAX,hide)
                ret=struct.unpack('<Q',bytes(uc.mem_read(rsp,8)))[0]
                uc.reg_write(UC_X86_REG_RSP,rsp+8);uc.reg_write(UC_X86_REG_RIP,ret)
        u.hook_add(UC_HOOK_CODE,hook);u.emu_start(address,STOP,count=2000)
        assert u.reg_read(UC_X86_REG_RIP)==STOP,(name,seen)
        assert u.reg_read(UC_X86_REG_RSP)==sp+8
        for r,value in expected.items():
            if r==UC_X86_REG_RAX:continue
            assert u.reg_read(r)==value,(name,original,hide,'register',r)
        if name in ['rider','horse','pet']:
            assert u.reg_read(UC_X86_REG_RAX)==SAVED_MASK|bool(original or hide),(name,seen)
        elif name in ['skinGate','meshGate']:
            assert u.reg_read(UC_X86_REG_RAX)==SAVED_MASK|bool(original and not hide),(name,seen)
        else:
            assert ('original' in seen)==(not hide),(name,seen)
            assert u.reg_read(UC_X86_REG_RAX)==(SAVED_MASK|original if not hide else expected[UC_X86_REG_RAX])
        results.append({'hook':name,'original_boolean':original,'classifier_hide':hide,'status':'pass'})
# Syntax check must return before touching any scanner/compiler/process API.
cttext=(R/'outputs/Star-Stable-object-visibility-v5.cea').read_text()
for action in ['ENABLE','DISABLE']:
    block=cttext.split('['+action+']\n{$lua}\n',1)[1].split('\n{$asm}',1)[0]
    assert lua_eval('syntaxcheck=true\nlocal function attempt()\n'+block+'\nend\nattempt()\nreturn "pass"')=='pass'
(E/'wrapper-assembly.json').write_text(json.dumps(exports,indent=2))
(E/'wrapper-validation.json').write_text(json.dumps({'status':'pass','native_execution_cases':len(results),'cases':results,'syntax_check_both_sections':'pass','method':'Actual Lua wrapper generator in Lua 5.3; Keystone x64 assembly; Unicorn modeled original/classifier callees','limitations':['CE assembler and compiler integration need a live table test','Native C classification is tested separately','No game-process writes or FPS measurements']},indent=2))
print(json.dumps({'status':'pass','wrapper_execution_cases':len(results),'syntax_check':'pass'}))
