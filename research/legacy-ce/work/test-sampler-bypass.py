"""Offline differential test: native sampler/search code, deterministic math shims.

No process attachment or writes to the game executable are performed.
"""
import sys,struct,json,math,random,hashlib,time,argparse
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--exe',type=Path,required=True,help='Unmodified SSOClient.exe 645.348067')
parser.add_argument('--output',type=Path,default=Path('sampler-emulation-results.json'))
parser.add_argument('--unicorn-path',type=Path,help='Optional directory containing an installed unicorn package')
args=parser.parse_args()
if args.unicorn_path:sys.path.insert(0,str(args.unicorn_path))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
raw=args.exe.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='3cec805521c70b64f1a33c5a0efa67679b8112dacbe9594ab1b47301b4d3de8d'
pe=struct.unpack_from('<I',raw,0x3c)[0];opt=pe+24
base=struct.unpack_from('<Q',raw,opt+24)[0];image_size=struct.unpack_from('<I',raw,opt+56)[0]
image=bytearray((image_size+4095)&~4095)
headers=struct.unpack_from('<I',raw,opt+60)[0];image[:headers]=raw[:headers]
section_base=opt+struct.unpack_from('<H',raw,pe+20)[0]
for i in range(struct.unpack_from('<H',raw,pe+6)[0]):
    off=section_base+40*i;va,size,fo=struct.unpack_from('<III',raw,off+12)
    image[va:va+size]=raw[fo:fo+size]
for gate,expected in [(0x6842a4,b'\x74\x29'),(0x684a06,b'\x74\x1e')]:assert image[gate:gate+2]==expected
DATA=0x60000000;STACK=0x70000000;STACK_SIZE=0x100000;STOP=0x50000000
OUT=DATA;DEFAULT=DATA+0x80;TABLE=DATA+0x1000;INDEX=DATA+0x2000;KEYS=DATA+0x200000
CALLEE_REGS=[UC_X86_REG_RBX,UC_X86_REG_RBP,UC_X86_REG_RSI,UC_X86_REG_RDI,UC_X86_REG_R12,UC_X86_REG_R13,UC_X86_REG_R14,UC_X86_REG_R15]+[globals()[f'UC_X86_REG_XMM{i}'] for i in range(6,16)]
FUNCTION_RANGES=[(0x6841c0,0x68451a),(0x684930,0x684b4e),(0x683e60,0x683f24),(0x684010,0x6840d3)]
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def lowfloat(value):return struct.unpack('<f',struct.pack('<I',value&0xffffffff))[0]
class Runner:
    def __init__(self,bypass=False):
        self.uc=Uc(UC_ARCH_X86,UC_MODE_64)
        self.uc.mem_map(base,len(image));self.uc.mem_write(base,bytes(image))
        self.uc.mem_map(DATA,0x800000);self.uc.mem_map(STACK,STACK_SIZE);self.uc.mem_map(STOP,0x1000)
        self.uc.hook_add(UC_HOOK_CODE,self.code)
        self.uc.hook_add(UC_HOOK_MEM_WRITE,self.write)
        if bypass:self.patch(True)
    def patch(self,enabled):
        for gate in [0x6842a4,0x684a06]:self.uc.mem_write(base+gate,b'\xeb' if enabled else b'\x74')
        self.uc.ctl_remove_cache(base+0x683e00,base+0x684c00)
    def code(self,uc,address,size,_):
        rva=address-base
        self.instructions+=1
        if rva in [0x6842b0,0x684a10]:self.loop_iterations+=1
        if rva in [0x9ff720,0xa003b0]:
            arg=lowfloat(uc.reg_read(UC_X86_REG_XMM0));name='acosf' if rva==0x9ff720 else 'sinf'
            self.math_calls.append((name,arg))
            value=math.acos(max(-1.0,min(1.0,arg))) if name=='acosf' else math.sin(arg)
            uc.reg_write(UC_X86_REG_XMM0,struct.unpack('<I',struct.pack('<f',value))[0])
            sp=uc.reg_read(UC_X86_REG_RSP);ret=struct.unpack('<Q',uc.mem_read(sp,8))[0]
            uc.reg_write(UC_X86_REG_RSP,sp+8);uc.reg_write(UC_X86_REG_RIP,ret)
        elif not any(lo<=rva<hi for lo,hi in FUNCTION_RANGES):
            raise AssertionError(f'Unexpected native call/instruction at RVA {rva:x}')
    def write(self,uc,access,address,size,value,_):
        if STACK<=address and address+size<=STACK+STACK_SIZE:return
        if OUT<=address and address+size<=OUT+16:return
        raise AssertionError(f'Unexpected write outside output/stack: {address:x} size {size}')
    def run(self,case):
        mode,n,t,interp,lookup,kind,seed=case
        rng=random.Random(seed)
        duration=f32(3.0)
        values=[]
        for i in range(n):
            when=f32(duration*i/max(1,n-1))
            if mode=='vector':v=[f32(rng.uniform(-20,20)) for _ in range(3)]
            else:
                v=[rng.uniform(-1,1) for _ in range(4)] if kind=='general' else [rng.uniform(-.01,.01) for _ in range(3)]+[1.0]
                norm=math.sqrt(sum(x*x for x in v));v=[f32(x/norm) for x in v]
                if kind=='opposite' and i%2:v=[-x for x in v]
            values.append(struct.pack('<'+'f'*(len(v)+1),when,*v))
        keys=b''.join(values)
        index_values=[min(n-1,int(i*n/lookup)) for i in range(lookup)] if n and lookup else []
        indices=struct.pack('<'+'H'*len(index_values),*index_values)
        uc=self.uc
        if keys:uc.mem_write(KEYS,keys)
        if indices:uc.mem_write(INDEX,indices)
        uc.mem_write(TABLE,struct.pack('<QQQ',INDEX,INDEX+len(indices),INDEX+len(indices)))
        uc.mem_write(DEFAULT,struct.pack('<4f',9,8,7,1));uc.mem_write(OUT,b'\xcc'*32)
        sp=STACK+STACK_SIZE-0x1008
        uc.mem_write(sp-0x1000,b'\xa5'*0x2000)
        uc.mem_write(sp,struct.pack('<Q',STOP))
        uc.mem_write(sp+0x28,struct.pack('<I',n))
        uc.mem_write(sp+0x30,struct.pack('<f',f32(t)))
        uc.mem_write(sp+0x38,struct.pack('<Q',interp))
        uc.mem_write(sp+0x40,struct.pack('<f',duration))
        for i,reg in enumerate(CALLEE_REGS):uc.reg_write(reg,(0x12345678+i) if i<8 else (0x1234567890abcdef1234567890abcdef+i))
        saved=[uc.reg_read(r) for r in CALLEE_REGS]
        uc.reg_write(UC_X86_REG_RCX,OUT);uc.reg_write(UC_X86_REG_RDX,DEFAULT);uc.reg_write(UC_X86_REG_R8,TABLE);uc.reg_write(UC_X86_REG_R9,KEYS)
        uc.reg_write(UC_X86_REG_RSP,sp);uc.reg_write(UC_X86_REG_EFLAGS,2);uc.reg_write(UC_X86_REG_MXCSR,0x1f80)
        self.instructions=0;self.loop_iterations=0;self.math_calls=[]
        entry=base+(0x6841c0 if mode=='quaternion' else 0x684930)
        uc.emu_start(entry,STOP,count=2000000)
        assert uc.reg_read(UC_X86_REG_RIP)==STOP,'Instruction limit reached'
        assert [uc.reg_read(r) for r in CALLEE_REGS]==saved,'Callee-saved register changed'
        assert uc.reg_read(UC_X86_REG_RSP)==sp+8,'Stack pointer not restored'
        assert uc.reg_read(UC_X86_REG_RAX)==OUT,'Returned output pointer differs'
        output=bytes(uc.mem_read(OUT,32))
        assert output[(16 if mode=='quaternion' else 12):]==b'\xcc'*(32-(16 if mode=='quaternion' else 12)),'Output overrun'
        return {'output':output.hex(),'math_calls':self.math_calls,'loop_iterations':self.loop_iterations,'instructions':self.instructions}

def main():
    cases=[];rng=random.Random(645348067)
    for mode in ['quaternion','vector']:
        for n in [0,1,2,7,8,9,24,25,64,255,1024,4096,65535]:
            for t,interp,lookup in [(-.25,0,0),(0,1,1),(1.234,1,8),(3,1,16),(3.5,0,0)]:
                cases.append((mode,n,t,interp,lookup,'general',rng.randrange(10**9)))
        for _ in range(250):
            cases.append((mode,rng.randrange(1,400),rng.uniform(-.25,3.5),rng.randrange(2),rng.choice([0,1,4,8,16]),rng.choice(['general','near','opposite']),rng.randrange(10**9)))
    baseline=Runner();patched=Runner(True);total_reads=0;math_cases=0;instruction_savings=0;started=time.time()
    for i,case in enumerate(cases):
        original=baseline.run(case);bypassed=patched.run(case)
        assert original['output']==bypassed['output'],('Output mismatch',case)
        assert original['math_calls']==bypassed['math_calls'],('Math helper argument mismatch',case)
        assert bypassed['loop_iterations']==0,('Loop still executed',case)
        assert original['loop_iterations']==(case[1]+7)//8,('Original loop count unexpected',case,original['loop_iterations'])
        total_reads+=original['loop_iterations'];math_cases+=bool(original['math_calls']);instruction_savings+=original['instructions']-bypassed['instructions']
        if (i+1)%100==0:print(f'Compared {i+1}/{len(cases)} original/bypass cases',flush=True)
    patched.patch(False)
    restore_indices=[0,5,10,15,20,25,30,35,40,45,50,55,60,65,90]
    restoration_cases=[cases[offset+i] for offset in [0,len(cases)//2] for i in restore_indices]
    for case in restoration_cases:
        restored=patched.run(case);original=baseline.run(case)
        assert restored==original,('Restore mismatch',case)
    result={'status':'pass','cases':len(cases),'native_sampler_runs':2*len(cases)+2*len(restoration_cases),'restoration_cases':len(restoration_cases),'restoration_cases_per_sampler':15,'math_helper_cases':math_cases,'total_loop_iterations_removed':total_reads,'emulated_instruction_difference':instruction_savings,'seconds':round(time.time()-started,3),'key_counts':'Selected counts spanning 0 to 65535, including boundaries and randomized cases; not exhaustive','comparisons':['output buffer bytes','guard bytes','returned output pointer','callee-saved registers including XMM6-XMM15','restored stack pointer','external math call arguments','enabled loops skipped','disabled behavior restored for both samplers'],'math_model':'Sampler and search instructions are the original native bytes. External acosf/sinf calls use deterministic float32 Python math shims; runtime CRT integration is not tested.','limitations':['Does not attach to or patch the live game','Does not model CPU caches, timing, concurrency, integrity checks or arbitrary invalid inputs','This is not a guarantee against a live-game crash']}
    args.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
