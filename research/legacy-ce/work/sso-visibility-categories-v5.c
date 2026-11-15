/* Pure classifier for CE's built-in x64 C compiler. No game calls, allocation,
   object writes or external imports. CFG_ADDRESS is supplied by the loader.
   All offsets below are guarded to the analyzed 645.348067 executable. */
typedef unsigned char U8;
typedef unsigned int U32;
typedef unsigned long long U64;
typedef struct {
    U32 generation,role,parent,root,rootGeneration,rootParent;
    U64 rootVtable;
} Cache;
typedef struct {
    volatile U8 active;
    U8 pad[15];
    volatile U8 hide[11];
    U8 pad2[37];
    U64 base, registryAddress, localRefAddress, cacheAddress;
    U32 capacity, epoch;
    U64 mesh, skin, particleEx, particle, playerSSO, playerTP, horse, pet;
    U64 npc, sale, collect, checkpoint;
    U8 pad3[56];
    volatile U64 hits[11];
} Config;
#ifndef CFG_ADDRESS
#define CFG_ADDRESS 0
#endif
#define C ((Config *)(U64)CFG_ADDRESS)
static U64 Q(U64 p,U32 o) {return *(volatile U64 *)(p+o);}
static U32 D(U64 p,U32 o) {return *(volatile U32 *)(p+o);}
static U8 B(U64 p,U32 o) {return *(volatile U8 *)(p+o);}
enum { PLAYER_HORSE=1, PLAYER=2, PLAYER_PET=3, NPC_ANIMAL=4,
       NPC=5, NPC_HORSE=6, STANDALONE=7, SALE=8, COINS=9, MARKER=10,
       TEXT=11, KEEP=255 };

static U8 lower(U8 c) { return c>='A'&&c<='Z' ? c+32 : c; }
static int letter(U8 c) { c=lower(c); return c>='a'&&c<='z'; }
/* Literal, underscore/digit and CamelCase boundaries reduce accidental matches
   such as Catherine -> cat or SeahorsePoint -> horse. This remains a heuristic. */
static int word(const char *s,const char *w,int limit) {
    int i,j; U8 before,first,next,last;
    for(i=0;i<limit && s[i];i++) {
        before=i ? (U8)s[i-1] : 0; first=(U8)s[i];
        if(i && letter(before) && !(before>='a'&&before<='z' && first>='A'&&first<='Z')) continue;
        for(j=0;w[j] && i+j<limit && s[i+j] && lower((U8)s[i+j])==(U8)w[j];j++);
        if(w[j] || i+j>=limit) continue;
        next=(U8)s[i+j];last=j?(U8)s[i+j-1]:0;
        if(!letter(next) || (last>='a'&&last<='z' && next>='A'&&next<='Z')) return 1;
    }
    return 0;
}
static const char *name(U64 record,int *limit) {
    U64 ptr;
    if(B(record,31)) {
        ptr=Q(record,24)<<1;
        if(ptr<0x10000 || ptr>=0x0000800000000000ULL) return 0;
        *limit=96;return (const char *)ptr;
    }
    *limit=7;return (const char *)(record+24);
}
static U64 resolve(U64 begin,U64 count,U64 ref) {
    U32 i=D(ref,12); U64 rec;
    if(i>=count) return 0;
    rec=begin+((U64)i<<6);
    return D(rec,44)==D(ref,8) ? Q(rec,32) : 0;
}
static U32 npcRole(U64 record) {
    int n;const char *s=name(record,&n);if(!s)return NPC;
    /* Known human names containing horse terms must stay in the human bucket. */
    if(word(s,"trainer",n)||word(s,"shopkeeper",n)||word(s,"girl",n)||word(s,"stylist",n))return NPC;
    if(word(s,"horse",n)||word(s,"horses",n)||word(s,"pony",n)||word(s,"foal",n)||word(s,"donkey",n)||word(s,"mare",n)||word(s,"stallion",n))return NPC_HORSE;
    if(word(s,"cat",n)||word(s,"dog",n)||word(s,"rabbit",n)||word(s,"bunny",n)||word(s,"fox",n)||word(s,"hen",n)||word(s,"chicken",n)||word(s,"cow",n)||word(s,"sheep",n)||word(s,"goat",n)||word(s,"pig",n)||word(s,"dove",n)||word(s,"crow",n)||word(s,"magpie",n)||word(s,"owl",n)||word(s,"bird",n)||word(s,"squirrel",n)||word(s,"raccoon",n)||word(s,"duck",n)||word(s,"deer",n)||word(s,"frog",n)||word(s,"seal",n)||word(s,"crab",n)||word(s,"butterfly",n))return NPC_ANIMAL;
    return NPC;
}
/* Positive cache hits still check the root's ancestors for ownership. A
   higher grouping node can be reparented without changing the mesh or root. */
static int protectedRoot(U64 begin,U64 count,U32 index) {
    U32 depth,parent;U64 record,ptr,vt,owner;
    for(depth=0;depth<32;depth++) {
        if(index==0x0BADF00D)return 0;
        if(index>=count)return 1;
        record=begin+((U64)index<<6);ptr=Q(record,32);
        if(!ptr||D(ptr,132)!=index||D(ptr,128)!=D(record,44))return 1;
        vt=Q(ptr,0);
        if(vt==C->checkpoint)return 1;
        if((vt==C->playerSSO||vt==C->playerTP||vt==C->horse||vt==C->pet)&&(B(ptr,144)&4))return 1;
        if(vt==C->horse||vt==C->pet) {
            owner=resolve(begin,count,ptr+(vt==C->horse?152:584));
            if(owner&&(Q(owner,0)==C->playerSSO||Q(owner,0)==C->playerTP)&&(B(owner,144)&4))return 1;
        }
        parent=D(record,40);if(parent==index)return 1;index=parent;
    }
    return 1;
}
static U32 role(U64 actor) {
    U64 registry=Q(C->registryAddress,0),begin,end,count,record,current,ptr,vt,owner;
    U32 index,generation,candidate=KEEP,typed=0,parent,depth,rootIndex,cacheable=1;
    Cache *slot=0;
    if(!registry)return KEEP;
    begin=Q(registry,0);end=Q(registry,8);
    if(!begin||end<begin||end-begin>0x10000000ULL||((end-begin)&63))return KEEP;
    count=(end-begin)>>6;index=D(actor,132);generation=D(actor,128);
    if(index>=count)return KEEP;
    record=begin+((U64)index<<6);
    if(D(record,44)!=generation||Q(record,32)!=actor)return KEEP;
    if(index<C->capacity) {
        slot=(Cache *)(C->cacheAddress+(U64)index*32);
        if((slot->role>>16)==C->epoch && slot->generation==generation && slot->parent==D(record,40) && slot->root<count) {
            U64 rr=begin+((U64)slot->root<<6),rp=Q(rr,32);
            if(rp && D(rr,44)==slot->rootGeneration && D(rr,40)==slot->rootParent && Q(rp,0)==slot->rootVtable) {
                U32 cached=slot->role&65535;
                return cached==KEEP||!protectedRoot(begin,count,slot->root)?cached:KEEP;
            }
        }
    }
    rootIndex=index;
    current=index;
    for(depth=0;depth<32;depth++) {
        if(current>=count){if(current!=0x0BADF00D)return KEEP;break;}
        record=begin+(current<<6);ptr=Q(record,32);
        if(!ptr)return KEEP;
        if(D(ptr,132)!=current||D(ptr,128)!=D(record,44))return KEEP;
        vt=Q(ptr,0);
        /* Check ownership even after a category is found in a descendant. */
        if(vt==C->playerSSO||vt==C->playerTP) {
            cacheable=0;
            if(B(ptr,144)&4){candidate=KEEP;break;}
            if(!typed){candidate=PLAYER;typed=1;}
        } else if(vt==C->horse) {
            cacheable=0;
            owner=resolve(begin,count,ptr+152);
            if((B(ptr,144)&4)||(owner && (Q(owner,0)==C->playerSSO||Q(owner,0)==C->playerTP) && (B(owner,144)&4))){candidate=KEEP;break;}
            if(!typed){candidate=!owner?STANDALONE:((Q(owner,0)==C->playerSSO||Q(owner,0)==C->playerTP)?PLAYER_HORSE:NPC_HORSE);typed=1;}
        } else if(vt==C->pet) {
            cacheable=0;
            owner=resolve(begin,count,ptr+584);
            if((B(ptr,144)&4)||(owner && (Q(owner,0)==C->playerSSO||Q(owner,0)==C->playerTP) && (B(owner,144)&4))){candidate=KEEP;break;}
            if(!typed){candidate=owner&&(Q(owner,0)==C->playerSSO||Q(owner,0)==C->playerTP)?PLAYER_PET:NPC_ANIMAL;typed=1;}
        } else if(vt==C->checkpoint) {
            cacheable=0;candidate=KEEP;break;
        } else if(vt==C->npc && !typed) {
            if(candidate!=MARKER)candidate=npcRole(record);typed=1;rootIndex=(U32)current;
        } else if(vt==C->sale && !typed) {
            candidate=SALE;typed=1;rootIndex=(U32)current;
        } else if(vt==C->collect && !typed) {
            candidate=COINS;typed=1;rootIndex=(U32)current;
        } else if(!typed) {
            int n;const char *s=name(record,&n);
            if(s) {
                if(word(s,"coin",n)||word(s,"coins",n)||word(s,"shilling",n)||word(s,"shillings",n)){candidate=COINS;rootIndex=(U32)current;}
                if(word(s,"exclamation",n)||word(s,"question",n)||word(s,"questionmark",n)||word(s,"exclamationmark",n)){candidate=MARKER;rootIndex=(U32)current;}
            }
        }
        parent=D(record,40);if(parent==current)return KEEP;current=parent;
    }
    if(depth==32)return KEEP;
    if(slot && cacheable){
        U64 rr=begin+((U64)rootIndex<<6),rp=Q(rr,32);
        slot->role=0;slot->generation=generation;slot->parent=D(begin+((U64)index<<6),40);
        slot->root=rootIndex;slot->rootGeneration=D(rr,44);slot->rootParent=D(rr,40);slot->rootVtable=rp?Q(rp,0):0;
        slot->role=(C->epoch<<16)|candidate;
    }
    return candidate;
}
static int hideRole(U32 r) {
    if(r>=1 && r<=11 && C->hide[r-1]==1){C->hits[r-1]++;return 1;}return 0;
}
int SSO5_actor(U64 actor) {return C->active && actor ? hideRole(role(actor)) : 0;}
int SSO5_visual(U64 actor) {
    U64 vt;
    if(!C->active || !actor)return 0;
    vt=Q(actor,0);
    if(vt!=C->mesh && vt!=C->skin && vt!=C->particleEx && vt!=C->particle)return 0;
    return hideRole(role(actor));
}
int SSO5_flag(U32 index) {
    if(!C->active||index>=11||C->hide[index]!=1)return 0;
    C->hits[index]++;return 1;
}
/* Kept as exports to let the isolated harness verify the real compiled layout. */
int SSO5_sizeof_config(void) {return sizeof(Config);}
int SSO5_offset_hits(void) {return (int)((U64)&C->hits-(U64)C);}
