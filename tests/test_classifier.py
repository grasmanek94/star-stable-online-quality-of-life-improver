"""Test the compiled classifier against host-owned fixtures; standard-library only."""
from pathlib import Path
import argparse
import ctypes as ct
import hashlib
import json
import struct

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dll',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args()
assert ct.sizeof(ct.c_void_p)==8, 'Use 64-bit Python.'
ROOT=Path(__file__).resolve().parents[1]
held=[]
def buffer(n):
    b=ct.create_string_buffer(n);held.append(b);return ct.addressof(b)
def put(a,fmt,*v):ct.memmove(a,struct.pack(fmt,*v),struct.calcsize(fmt))
def get(a,fmt):return struct.unpack(fmt,ct.string_at(a,struct.calcsize(fmt)))[0]
N=8192;records=buffer(N*64);registry=buffer(16);put(registry,'<QQ',records,records+N*64)
global_registry=buffer(8);put(global_registry,'<Q',registry)
native_dll=ct.CDLL(str(args.dll.resolve()))
native_dll.TestConfig.restype=ct.c_void_p
cfg=native_dll.TestConfig();cache=buffer(N*32)
put(cfg,'<B',1);ct.memset(cfg+16,1,11);put(cfg+72,'<Q',global_registry);put(cfg+88,'<Q',cache);put(cfg+96,'<II',N,1)
vt_names=['mesh','skin','particleEx','particle','playerSSO','playerTP','horse','pet','npc','sale','collect','checkpoint']
vts={name:0x140000000+(i+1)*4096 for i,name in enumerate(vt_names)}
for i,name in enumerate(vt_names):put(cfg+104+i*8,'<Q',vts[name])
src=(ROOT/'src/visibility/classifier.inc').read_text(encoding='utf-8')
functions={}
for name in ['actor','visual','flag','particles']:
    fn=getattr(native_dll,'SSO5_'+name);fn.argtypes=[ct.c_uint64];fn.restype=ct.c_int
    functions[name]=fn

def layout(name):
    return getattr(native_dll,'SSO5_'+name)()

assert layout('sizeof_config')==368 and layout('offset_hits')==256
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
# Particle filtering is independent of actor-category hiding.
for name,offset in [('questItem',200),('trigger',208),('visibilityTrigger',216)]:
    vts[name]=0x160000000+offset;put(cfg+offset,'<Q',vts[name])
def fresh_guard(value):
    put(cfg+30,'<B',value);put(cfg+100,'<I',get(cfg+100,'<I')+1)
def particle_flags(ambient=0,broad=0):
    ct.memset(cfg+16,0,14);put(cfg+27,'<BB',ambient,broad)
put(cfg,'<B',1);fresh_guard(0)
neutral=actor('other','Environment')
p=actor('particleEx','Dust_Day',neutral)
particle_flags();check('particles default off',functions['particles'](p[0]),0)
particle_flags(1);check('ambient allowlisted particle',functions['particles'](p[0]),1)
for kind,name,expected in [('particle','DUST_DAY',1),('particleEx','Dust_DayExtra',0),('particleEx','NotDust_Day',0),('particleEx','Smoke',0),('mesh','Dust_Day',0),('particleEx','QuestItemParticleSystem',0)]:
    item=actor(kind,name,neutral);check('ambient exact class/name '+kind+' '+name,functions['particles'](item[0]),expected)
for kind,name in [('other','RaceObstacle'),('other','FogVolume'),('other','QuestMarkers'),('questItem','Object'),('trigger','Object'),('visibilityTrigger','Object'),('checkpoint','Object'),('collect','Object'),('npc','Person'),('playerSSO','Remote'),('horse','Horse')]:
    root=actor(kind,name,neutral);item=actor('particleEx','Dust_Day',root)
    check('ambient ancestor protection '+kind+' '+name,functions['particles'](item[0]),0)
item=actor('particleEx','Dust_Day',neutral);put(records+item[1]*64+44,'<I',999999)
check('ambient invalid generation stays native',functions['particles'](item[0]),0)
item=actor('particleEx','Dust_Day',neutral);put(records+item[1]*64+40,'<I',item[1])
check('ambient parent cycle stays native',functions['particles'](item[0]),0)
longroot=neutral
for i in range(34):longroot=actor('other','Group',longroot)
item=actor('particleEx','Dust_Day',longroot);check('ambient bounded ancestry',functions['particles'](item[0]),0)
particle_flags(0,1)
for kind,name,expected in [('particleEx','QuestItemParticleSystem',1),('particle','ParticleSystem',1),('skin','ParticleSystem',0)]:
    item=actor(kind,name,neutral);check('broad exact particle class '+kind,functions['particles'](item[0]),expected)
fresh_guard(1);item=actor('particleEx','QuestItemParticleSystem',neutral)
check('broad optional gameplay guard',functions['particles'](item[0]),0)
item=actor('particleEx','ParticleSystem',neutral);check('broad guarded unknown ambient name',functions['particles'](item[0]),1)
fresh_guard(0);ct.memset(cfg+16,0,14);put(cfg+20,'<B',1)
race_npc=actor('npc','RaceObstacle',neutral);mesh=actor('skin','Model',race_npc)
check('aggressive NPC visuals',functions['visual'](mesh[0]),1)
fresh_guard(1);check('normal preset protects race NPC',functions['visual'](mesh[0]),0)
questroot=actor('questItem','Thing',neutral);npc=actor('npc','TownPerson',questroot);mesh=actor('skin','Model',npc)
check('normal preset protects quest item ancestry',functions['visual'](mesh[0]),0)
ct.memset(cfg+16,0,14);put(cfg+29,'<B',1);check('detail grass flag',functions['flag'](13),1)
put(cfg,'<B',0);check('particle master passthrough',functions['particles'](p[0]),0)
report={'status':'pass','case_count':len(cases),'cases':cases,'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'compiled_config_bytes':layout('sizeof_config'),'hits_offset':layout('offset_hits'),'method':'Actual shared classifier built by CMake/MSVC; host-owned fixture memory only','limits':['No game-process writes','No FPS result or full gameplay lifecycle test','Name-based NPC categories are heuristic']}
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'pass','native_cases':len(cases),'config_size':layout('sizeof_config')}))
