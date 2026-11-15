"""Execute the DLL's actual MASM code in Unicorn, including an ASLR rebase."""
from pathlib import Path
import argparse,json,re,struct,hashlib
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dll',type=Path,required=True)
parser.add_argument('--map',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args()
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *
raw=args.dll.read_bytes();nt=struct.unpack_from('<I',raw,60)[0];opt=nt+24
preferred=struct.unpack_from('<Q',raw,opt+24)[0];size=struct.unpack_from('<I',raw,opt+56)[0];headers=struct.unpack_from('<I',raw,opt+60)[0]
image=bytearray(size);image[:headers]=raw[:headers]
for i in range(struct.unpack_from('<H',raw,nt+6)[0]):
    at=opt+struct.unpack_from('<H',raw,nt+20)[0]+40*i;va,sz,fo=struct.unpack_from('<III',raw,at+12);image[va:va+sz]=raw[fo:fo+sz]
symbols={m[1]:int(m[2],16)-preferred for m in re.finditer(r'^\s+[0-9A-Fa-f]{4}:[0-9A-Fa-f]{8}\s+(\S+)\s+([0-9A-Fa-f]{16})\s', args.map.read_text(encoding='utf-8'),re.M)}
reloc_rva,reloc_size=struct.unpack_from('<II',raw,opt+112+5*8)
relocations=[];at=reloc_rva
while at<reloc_rva+reloc_size:
    page,block=struct.unpack_from('<II',image,at);assert block>=8
    for i in range((block-8)//2):
        entry=struct.unpack_from('<H',image,at+8+2*i)[0];kind=entry>>12
        assert kind in [0,10]
        if kind==10:relocations.append(page+(entry&4095))
    at+=block
GAME=0x140000000;THUNKS=0x130000000;STACK=0x70000000;STOP=0x71000000;ACTOR=0x72000000
MASK=0x123456789ABC0000
gpr=[UC_X86_REG_RAX,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11,UC_X86_REG_RBX,UC_X86_REG_RBP,UC_X86_REG_RSI,UC_X86_REG_RDI,UC_X86_REG_R12,UC_X86_REG_R13,UC_X86_REG_R14,UC_X86_REG_R15]
xmm=[globals()[f'UC_X86_REG_XMM{i}'] for i in range(16)]
sites=json.loads((ROOT/'data/visibility-sites.json').read_text(encoding='utf-8'))
def setup(base):
    data=bytearray(image);delta=base-preferred
    for rva in relocations:struct.pack_into('<Q',data,rva,(struct.unpack_from('<Q',data,rva)[0]+delta)&0xFFFFFFFFFFFFFFFF)
    u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(base,(size+4095)&~4095);u.mem_write(base,bytes(data))
    for address,n in [(GAME,0x2000000),(THUNKS,0x10000),(STACK,0x10000),(STOP,0x1000),(ACTOR,0x1000)]:u.mem_map(address,n)
    sp=STACK+0xEFF8;u.mem_write(sp,struct.pack('<Q',STOP));u.reg_write(UC_X86_REG_RSP,sp)
    for i,r in enumerate(gpr):u.reg_write(r,MASK+i)
    for i,r in enumerate(xmm):u.reg_write(r,0x0123456789ABCDEF0011223344556677+i)
    for r in [UC_X86_REG_RCX,UC_X86_REG_RBX,UC_X86_REG_RSI,UC_X86_REG_RDI]:u.reg_write(r,ACTOR)
    u.mem_write(sp+8,bytes(range(192)))
    expected={r:u.reg_read(r)for r in gpr+xmm};return u,sp,expected
def ret(u):
    sp=u.reg_read(UC_X86_REG_RSP);address=struct.unpack('<Q',bytes(u.mem_read(sp,8)))[0]
    u.reg_write(UC_X86_REG_RSP,sp+8);u.reg_write(UC_X86_REG_RIP,address)
wrapper_results=[];forward_results=[]
for base in [preferred,0x500000000]:
    for i,(name,d) in enumerate(sites.items()):
      for original in [0,1]:
       for hide in [0,1]:
        u,sp,expected=setup(base);target=GAME+int(d['target_rva'],16)
        entry=d.get('kind')=='particle_entry'
        continuation=GAME+int(d['patch_rva'],16)+5 if entry else target
        u.mem_write(base+symbols['g_originals']+8*i,struct.pack('<Q',continuation))
        u.mem_write(base+symbols['g_config'],b'\1')
        u.mem_write(base+symbols['g_config']+27,bytes([1-original,original,1]))
        if entry:u.mem_write(base+symbols['g_particleChildren'],struct.pack('<Q',target))
        thunk=THUNKS+i*16;u.mem_write(thunk,b'\xFF\x25\0\0\0\0'+struct.pack('<Q',base+symbols[f'HideHook_{i}'])+b'\x90\x90')
        helpers={base+symbols[n]for n in ['ProxyHideActor','ProxyHideVisual','ProxyHideFlag','ProxyHideParticles']};seen=[]
        def hook(uc,at,n,_):
            if at==STOP:uc.emu_stop();return
            if at==continuation or (entry and at==target):
                seen.append('children'if entry and at==target else 'original');rsp=uc.reg_read(UC_X86_REG_RSP);assert rsp%16==8
                if name not in ['rider','horse','pet','skinGate','meshGate','particleLegacyGate']:assert rsp==sp
                uc.reg_write(UC_X86_REG_RAX,MASK|original);ret(uc)
            elif at in helpers:
                seen.append('classifier');assert uc.reg_read(UC_X86_REG_RSP)%16==8
                for r in gpr[:7]:uc.reg_write(r,0xDEAD0000)
                for r in xmm[:6]:uc.reg_write(r,0xDEAD0000)
                uc.reg_write(UC_X86_REG_RAX,hide);ret(uc)
        u.hook_add(UC_HOOK_CODE,hook);u.emu_start(thunk,STOP,count=2000)
        assert u.reg_read(UC_X86_REG_RIP)==STOP and u.reg_read(UC_X86_REG_RSP)==sp+8
        expected_stack=bytearray(range(192))
        if entry and not hide:expected_stack[:8]=struct.pack('<Q',expected[UC_X86_REG_RBX])
        assert bytes(u.mem_read(sp+8,192))==bytes(expected_stack),(name,'stack args')
        for r,value in expected.items():
            if r!=UC_X86_REG_RAX:assert u.reg_read(r)==value,(name,r)
        if name in ['rider','horse','pet']:assert u.reg_read(UC_X86_REG_RAX)==MASK|bool(original or hide)
        elif name in ['skinGate','meshGate','particleLegacyGate']:assert u.reg_read(UC_X86_REG_RAX)==MASK|bool(original and not hide)
        elif entry:assert seen==['classifier','children'if hide else 'original']
        else:assert ('original'in seen)==(not hide)
        wrapper_results.append({'layout':'preferred'if base==preferred else 'ASLR DLL beyond near-CALL range','hook':name,'original':original,'hide':hide,'status':'pass'})
    for index in ([0,184,367]if 'g_glFunctions'in symbols else []):
      for lazy in [True,False]:
        u,sp,expected=setup(base);table=base+symbols['g_glFunctions'];real=GAME+0x1000;seen=[]
        if not lazy:u.mem_write(table+index*8,struct.pack('<Q',real))
        def forward_hook(uc,at,n,_):
            if at==STOP:uc.emu_stop();return
            if at==base+symbols['ProxyInitialize']:
                seen.append('init');assert uc.reg_read(UC_X86_REG_RSP)%16==8
                for r in gpr[:7]:uc.reg_write(r,0xBAAD0000)
                for r in xmm[:6]:uc.reg_write(r,0xBAAD0000)
                uc.mem_write(table+index*8,struct.pack('<Q',real));ret(uc)
            elif at==real:
                seen.append('real');assert uc.reg_read(UC_X86_REG_RSP)==sp
                for r,v in expected.items():
                    if r!=UC_X86_REG_R11:assert uc.reg_read(r)==v,('GL args',index,lazy,r)
                assert bytes(uc.mem_read(sp+8,192))==bytes(range(192))
                uc.reg_write(UC_X86_REG_RAX,0xC0FFEE);ret(uc)
        u.hook_add(UC_HOOK_CODE,forward_hook);u.emu_start(base+symbols[f'GL_Export_{index}'],STOP,count=1000)
        assert seen==(['init','real']if lazy else ['real'])
        assert u.reg_read(UC_X86_REG_RAX)==0xC0FFEE and u.reg_read(UC_X86_REG_RSP)==sp+8
        forward_results.append({'dll_base':hex(base),'export_index':index,'lazy':lazy,'status':'pass'})
report={'status':'pass','wrapper_execution_cases':len(wrapper_results),'forwarder_execution_cases':len(forward_results),'dll_sha256':hashlib.sha256(raw).hexdigest(),'wrapper_cases':wrapper_results,'forwarder_cases':forward_results,'method':'Actual linked DLL MASM code in Unicorn, PE DIR64 rebasing, real near-thunk bytes, modeled native helpers/classifier','limits':['No live game-process writes','Models C helper results; actual C is tested separately','Windows OpenGL driver integration checked separately in native smoke test']}
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k]for k in ['status','wrapper_execution_cases','forwarder_execution_cases','dll_sha256']}))
