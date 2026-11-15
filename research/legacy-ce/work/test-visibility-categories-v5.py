"""Isolated native C tests. No attachment to or writes into SSOClient.exe."""
from pathlib import Path
import ctypes as ct, json,struct,hashlib,collections,sys
R=Path(__file__).resolve().parents[1];W=R/'work';E=R/'outputs/visibility-categories-v5-evidence'
tcc=ct.CDLL(r'C:\Program Files\Cheat Engine\tcc64-64.dll')
tcc.tcc_new.restype=ct.c_void_p
tcc.tcc_add_include_path.argtypes=[ct.c_void_p,ct.c_char_p];tcc.tcc_add_include_path.restype=ct.c_int
tcc.tcc_set_options.argtypes=[ct.c_void_p,ct.c_char_p]
for name,args,res in [('tcc_set_output_type',[ct.c_void_p,ct.c_int],ct.c_int),('tcc_compile_string',[ct.c_void_p,ct.c_char_p],ct.c_int),('tcc_relocate',[ct.c_void_p,ct.c_void_p],ct.c_int),('tcc_get_symbol',[ct.c_void_p,ct.c_char_p],ct.c_void_p),('tcc_delete',[ct.c_void_p],None)]:
    fn=getattr(tcc,name);fn.argtypes=args;fn.restype=res
held=[]
def buffer(n):
    b=ct.create_string_buffer(n);held.append(b);return ct.addressof(b)
def put(a,fmt,*v):ct.memmove(a,struct.pack(fmt,*v),struct.calcsize(fmt))
def get(a,fmt):return struct.unpack(fmt,ct.string_at(a,struct.calcsize(fmt)))[0]
N=8192;records=buffer(N*64);registry=buffer(16);put(registry,'<QQ',records,records+N*64)
global_registry=buffer(8);put(global_registry,'<Q',registry)
native_dll=ct.CDLL(sys.argv[1])if len(sys.argv)>1 else None
if native_dll:native_dll.TestConfig.restype=ct.c_void_p
cfg=native_dll.TestConfig()if native_dll else buffer(4096);cache=buffer(N*32)
put(cfg,'<B',1);ct.memset(cfg+16,1,11);put(cfg+72,'<Q',global_registry);put(cfg+88,'<Q',cache);put(cfg+96,'<II',N,1)
vt_names=['mesh','skin','particleEx','particle','playerSSO','playerTP','horse','pet','npc','sale','collect','checkpoint']
vts={name:0x140000000+(i+1)*4096 for i,name in enumerate(vt_names)}
for i,name in enumerate(vt_names):put(cfg+104+i*8,'<Q',vts[name])
src=(W/'sso-visibility-categories-v5.c').read_text()
source=f'#define CFG_ADDRESS 0x{cfg:X}ULL\n'+src
state=None
if not native_dll:
    state=tcc.tcc_new();assert state
    tcc.tcc_add_include_path(state,rb'C:\Program Files\Cheat Engine\include')
    tcc.tcc_set_options(state,b'-nostdlib')
    assert tcc.tcc_set_output_type(state,1)==0
    assert tcc.tcc_compile_string(state,source.encode())==0
    size=tcc.tcc_relocate(state,None);assert size>0
    kernel=ct.WinDLL('kernel32',use_last_error=True)
    kernel.VirtualAlloc.argtypes=[ct.c_void_p,ct.c_size_t,ct.c_ulong,ct.c_ulong];kernel.VirtualAlloc.restype=ct.c_void_p
    native_memory=kernel.VirtualAlloc(None,size,0x3000,0x40);assert native_memory
    assert tcc.tcc_relocate(state,native_memory)==0
functions={}
for name in ['actor','visual','flag']:
    if native_dll:
        fn=getattr(native_dll,'SSO5_'+name);fn.argtypes=[ct.c_uint64];fn.restype=ct.c_int
    else:fn=ct.CFUNCTYPE(ct.c_int,ct.c_uint64)(tcc.tcc_get_symbol(state,('SSO5_'+name).encode()))
    functions[name]=fn
def layout(name):
    if native_dll:return getattr(native_dll,'SSO5_'+name)()
    at=tcc.tcc_get_symbol(state,('SSO5_'+name).encode())
    return ct.CFUNCTYPE(ct.c_int)(at)()
assert layout('sizeof_config')==344 and layout('offset_hits')==256
cases=[];next_index=0
def actor(kind,name='',parent=None,local=False):
    global next_index
    i=next_index;next_index+=1;a=buffer(4096);rec=records+i*64;gen=1000+i
    put(a,'<Q',vts.get(kind,0x155555550));put(a+128,'<II',gen,i);put(a+144,'<B',64|(4 if local else 0))
    put(rec+32,'<Q',a);put(rec+40,'<II',parent[1] if parent else 0xBADF00D,gen)
    encoded=name.encode()
    if len(encoded)<=7:ct.memmove(rec+24,encoded,len(encoded))
    else:
        s=buffer(len(encoded)+1);ct.memmove(s,encoded,len(encoded));put(rec+24,'<Q',(s>>1)|(1<<63))
    return a,i
def ref(a,off,owner):
    if owner:put(a+off+8,'<II',get(owner[0]+128,'<I'),owner[1])
    else:put(a+off+8,'<II',0,0xBADF00D)
def check(name,value,expected):
    assert value==expected,(name,value,expected);cases.append(name)
def only(n):ct.memset(cfg+16,0,11);put(cfg+16+n,'<B',1)
local=actor('playerSSO','Local',local=True);remote=actor('playerSSO','Remote')
lh=actor('horse','Horse',local=True);ref(lh[0],152,local)
rh=actor('horse','HorseSlave');ref(rh[0],152,remote)
lp=actor('pet','OwnPet',local=True);ref(lp[0],584,local)
rp=actor('pet','RemotePet');ref(rp[0],584,remote)
for name,root,cat in [('player',remote,1),('horse',rh,0),('pet',rp,2)]:
    child=actor('skin','Pelvis',root);only(cat)
    check(name+' selected',functions['visual'](child[0]),1)
    only((cat+1)%11);check(name+' independent flags',functions['visual'](child[0]),0)
for name,root in [('local player',local),('local horse',lh),('local pet',lp)]:
    child=actor('skin','Coins',root);ct.memset(cfg+16,1,11)
    check(name+' protected despite descendant name',functions['visual'](child[0]),0)
for name,cat in [('Cat',3),('Cat1Night',3),('RanchDogSleeping',3),('Hen1',3),('Catherine',4),('HorseTrainer',4),('NewHillcrestHorseAccessories_Shopkeeper',4),('SeahorsePoint',4),('GoldenLeafPaddockHorse01',5),('HorseQC227',5),('Donkey1',5),('Foal1',5),('Elizabeth_SacredGroveVault',4)]:
    root=actor('npc',name,local=True);child=actor('skin','Pelvis',root);only(cat)
    check('NPC split '+name,functions['visual'](child[0]),1)
    only((cat+1)%11);check('NPC split independent '+name,functions['visual'](child[0]),0)
for kind,cat in [('sale',7),('collect',8)]:
    root=actor(kind,'Object');child=actor('mesh','Model',root);only(cat)
    check(kind+' descendants',functions['visual'](child[0]),1)
unowned=actor('horse','Horse');ref(unowned[0],152,None);only(6)
check('riderless horse',functions['actor'](unowned[0]),1)
for word,cat in [('Coin',8),('Coins',8),('ExclamationMark',9),('QuestionMark1',9)]:
    root=actor('other',word);child=actor('mesh','Model',root);only(cat)
    check('named visual '+word,functions['visual'](child[0]),1)
checkpoint=actor('checkpoint','Checkpoint');child=actor('mesh','Coins',checkpoint);ct.memset(cfg+16,1,11)
check('checkpoint overrides coin-like descendant',functions['visual'](child[0]),0)
check('non-visual root is not gated',functions['visual'](remote[0]),0)
for cat in range(11):
    only(cat);check('direct flag '+str(cat),functions['flag'](cat),1)
    check('other flag '+str(cat),functions['flag']((cat+1)%11),0)
put(cfg,'<B',0);check('master passthrough actor',functions['actor'](rp[0]),0);check('master passthrough visual',functions['visual'](rh[0]),0);check('master passthrough flag',functions['flag'](0),0);put(cfg,'<B',1)
root=actor('npc','Cat');child=actor('skin','Pelvis',root);only(3);check('cache initial category',functions['visual'](child[0]),1)
# Reparenting/ownership changes must not leave a formerly hidden mesh invisible.
put(records+child[1]*64+40,'<I',local[1]);check('reparented local protection',functions['visual'](child[0]),0)
root=actor('npc','Cat');child=actor('skin','Pelvis',root);only(3);check('root parent initial category',functions['visual'](child[0]),1)
put(records+root[1]*64+40,'<I',local[1]);check('root reparented under local player',functions['visual'](child[0]),0)
group=actor('other','Group');root=actor('npc','Cat',group);child=actor('skin','Pelvis',root);only(3)
check('cached NPC in neutral group',functions['visual'](child[0]),1)
put(records+group[1]*64+40,'<I',local[1]);check('higher group becomes local owned',functions['visual'](child[0]),0)
root=actor('npc','Cat');last=root
for i in range(34):last=actor('other','Group',last)
child=actor('skin','Coins',last);ct.memset(cfg+16,1,11)
check('too-deep ancestry stays visible',functions['visual'](child[0]),0)
child=actor('skin','Pelvis',rh);only(0);check('remote horse before owner change',functions['visual'](child[0]),1)
ref(rh[0],152,local);check('horse owner becomes local without generation change',functions['visual'](child[0]),0)
child=actor('skin','Pelvis',rp);only(2);check('remote pet before owner change',functions['visual'](child[0]),1)
ref(rp[0],584,local);check('pet owner becomes local without generation change',functions['visual'](child[0]),0)
ct.memset(cfg+16,1,11)
put(records+rp[1]*64+44,'<I',99999);check('generation mismatch rejected',functions['actor'](rp[0]),0)
report={'status':'pass','case_count':len(cases),'cases':cases,'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'compiled_config_bytes':layout('sizeof_config'),'hits_offset':layout('offset_hits'),'method':'Actual classifier compiled with the installed CE x64 TCC DLL; host-owned fixture memory only','limitations':['No target-process writes','Does not execute the game or validate native patch integration','Name-based NPC categories are heuristic','No FPS result or full gameplay lifecycle test']}
live=json.loads((E/'live-category-census.json').read_text(encoding='utf-8-sig'))if(E/'live-category-census.json').exists()else{'SelectedActiveActors':[]}
categories=collections.Counter();examples={}
for item in live['SelectedActiveActors']:
    if item['Class']!='CPXQuestControl':continue
    root=actor('npc',item.get('Name') or '',local=True)
    functions['actor'](root[0]);category=get(cache+root[1]*32+4,'<I')&65535
    categories[str(category)]+=1;examples.setdefault(str(category),[])
    if len(examples[str(category)])<20:examples[str(category)].append(item.get('Name'))
report['snapshot_npc_name_classification']={'counts':dict(categories),'examples':examples,'note':'Loaded records, not visible/on-screen NPC counts; physical model types are not independently labeled'}
if native_dll:report['method']='Actual shared classifier compiled with MSVC /O2 /MT; host-owned fixture memory only'
(E/('msvc-classifier-validation.json'if native_dll else 'native-classifier-validation.json')).write_text(json.dumps(report,indent=2))
print(json.dumps({'status':'pass','native_cases':len(cases),'config_size':layout('sizeof_config')}))
if state:tcc.tcc_delete(state)
