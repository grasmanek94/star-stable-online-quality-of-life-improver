#include "sso_proxy/proxy_internal.h"
#include <stddef.h>
#include <string.h>
#include <limits.h>
#include <tlhelp32.h>
#include "classifier.inc"

typedef struct {
    const char *name;
    const BYTE *pattern,*mask;
    SIZE_T length,offset;
    DWORD targetRva;
    void *wrapper;
} HookSpec;
#include "hook_specs.inc"
void *g_originals[HOOK_COUNT];
const char *g_categoryNames[11]={"other player horses","other player characters","other player pets",
    "NPC pets / ambient animals (name based)","NPC actors / unclassified NPC models","NPC horses (name based)",
    "standalone riderless horses","sale / display horses","coins / collectible visuals","quest ? / ! markers","NPC floating text / speech bubbles"};
typedef struct {
    BYTE *window,*call,*thunk;
    BYTE original[64],patched[64];
    SIZE_T length,offset;
} Hook;
static Hook g_hooks[HOOK_COUNT];
static BYTE *g_image,*g_thunks;
static BOOL g_ready,g_installed;
static volatile LONG g_faults;
static DWORD g_epoch;
#ifdef SSO_PROXY_TESTING
static LONG g_testFailAfterWrite=-1;
#endif
_Static_assert(sizeof(Config)==344,"Config layout drift");
_Static_assert(offsetof(Config,hits)==256,"Counter layout drift");

int ProxyHideActor(U64 actor) {
    __try {return SSO5_actor(actor);}
    __except(EXCEPTION_EXECUTE_HANDLER){InterlockedIncrement(&g_faults);return 0;}
}
int ProxyHideVisual(U64 actor) {
    __try {return SSO5_visual(actor);}
    __except(EXCEPTION_EXECUTE_HANDLER){InterlockedIncrement(&g_faults);return 0;}
}
int ProxyHideFlag(U32 index) {
    __try {return SSO5_flag(index);}
    __except(EXCEPTION_EXECUTE_HANDLER){InterlockedIncrement(&g_faults);return 0;}
}
LONG VisibilityFaultCount(void){return InterlockedCompareExchange(&g_faults,0,0);}
void VisibilityInitialize(void){for(unsigned i=0;i<11;i++)g_config.hide[i]=1;}
void VisibilityToggleCategory(unsigned index){
    if(index>=11)return;
    g_config.hide[index]=g_config.hide[index]==1?0:1;
    ProxyLog("category %u: %s; hide=%u%s",index+1,g_categoryNames[index],g_config.hide[index],g_config.active?" (active)":" (saved for F5)");
}
static BOOL Equal(const BYTE *a,const BYTE *b,SIZE_T n){
    for(SIZE_T i=0;i<n;i++)if(((const volatile BYTE*)a)[i]!=b[i])return FALSE;return TRUE;
}
static BOOL ImageHeaders(BYTE *base,IMAGE_NT_HEADERS64 **out){
    IMAGE_DOS_HEADER *dos=(IMAGE_DOS_HEADER*)base;
    if(!base||dos->e_magic!=IMAGE_DOS_SIGNATURE||dos->e_lfanew<0x40||dos->e_lfanew>0x1000)return FALSE;
    IMAGE_NT_HEADERS64 *nt=(IMAGE_NT_HEADERS64*)(base+dos->e_lfanew);
    if(nt->Signature!=IMAGE_NT_SIGNATURE||nt->FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64||nt->OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC)return FALSE;
    if(nt->FileHeader.TimeDateStamp!=0x6AEB5BD3||nt->OptionalHeader.SizeOfImage!=0x014AF000||nt->FileHeader.NumberOfSections<1||nt->FileHeader.NumberOfSections>96)return FALSE;
    *out=nt;return TRUE;
}
static BOOL Executable(IMAGE_NT_HEADERS64 *nt,DWORD rva,SIZE_T length){
    IMAGE_SECTION_HEADER *sections=IMAGE_FIRST_SECTION(nt);
    for(unsigned i=0;i<nt->FileHeader.NumberOfSections;i++){
        DWORD size=sections[i].Misc.VirtualSize>sections[i].SizeOfRawData?sections[i].Misc.VirtualSize:sections[i].SizeOfRawData;
        if((sections[i].Characteristics&IMAGE_SCN_MEM_EXECUTE)&&rva>=sections[i].VirtualAddress&&(U64)rva+length<=(U64)sections[i].VirtualAddress+size)return TRUE;
    }
    return FALSE;
}
static BYTE *FindUnique(BYTE *base,IMAGE_NT_HEADERS64 *nt,const HookSpec *spec){
    IMAGE_SECTION_HEADER *sections=IMAGE_FIRST_SECTION(nt);BYTE *found=NULL;
    for(unsigned s=0;s<nt->FileHeader.NumberOfSections;s++){
        IMAGE_SECTION_HEADER *section=&sections[s];
        if(!(section->Characteristics&IMAGE_SCN_MEM_EXECUTE))continue;
        SIZE_T size=section->Misc.VirtualSize>section->SizeOfRawData?section->Misc.VirtualSize:section->SizeOfRawData;
        if((U64)section->VirtualAddress+size>nt->OptionalHeader.SizeOfImage)return NULL;
        BYTE *start=base+section->VirtualAddress;
        for(SIZE_T at=0;at+spec->length<=size;at++){
            if(spec->mask[0]&&start[at]!=spec->pattern[0])continue;
            SIZE_T j;for(j=1;j<spec->length;j++)if(spec->mask[j]&&start[at+j]!=spec->pattern[j])break;
            if(j==spec->length){if(found)return NULL;found=start+at;}
        }
    }
    return found;
}
static BOOL LocalLayout(BYTE *base){
    U64 registry=Q((U64)base,0x1379EF0);if(!registry)return FALSE;
    U64 begin=Q(registry,0),end=Q(registry,8);
    if(!begin||end<begin||end-begin>0x10000000||((end-begin)&63))return FALSE;
    U64 count=(end-begin)>>6,player=resolve(begin,count,(U64)base+0x1302F28);
    if(!player||Q(player,0)!=(U64)base+0xFE4770||!(B(player,144)&4))return FALSE;
    U64 horse=resolve(begin,count,player+1608);
    return horse&&Q(horse,0)==(U64)base+0xF10600&&(B(horse,144)&4);
}
static BYTE *AllocateNear(BYTE *base,SIZE_T size){
    SYSTEM_INFO si;GetSystemInfo(&si);UINT_PTR gran=si.dwAllocationGranularity;
    UINT_PTR center=(UINT_PTR)base&~(gran-1);
    for(UINT_PTR distance=gran;distance<0x70000000;distance+=gran){
        UINT_PTR candidates[2]={center+distance,center>distance?center-distance:0};
        for(unsigned i=0;i<2;i++){
            if(candidates[i]<(UINT_PTR)si.lpMinimumApplicationAddress||candidates[i]>(UINT_PTR)si.lpMaximumApplicationAddress-size)continue;
            MEMORY_BASIC_INFORMATION mbi;
            if(VirtualQuery((void*)candidates[i],&mbi,sizeof(mbi))&&mbi.State==MEM_FREE&&mbi.RegionSize>=size){
                BYTE *p=VirtualAlloc((void*)candidates[i],size,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
                if(p)return p;
            }
        }
    }
    return NULL;
}
static BOOL Prepare(BYTE *base){
    IMAGE_NT_HEADERS64 *nt;
    if(!ImageHeaders(base,&nt)){ProxyLog("F5 rejected: unsupported executable layout; expected 645.348067. OpenGL forwarding continues.");return FALSE;}
    if(!LocalLayout(base)){ProxyLog("F5 rejected: local player/horse not ready or ownership layout differs. Enter the world and retry.");return FALSE;}
    if(g_ready)return base==g_image;
    Hook temporary[HOOK_COUNT];ZeroMemory(temporary,sizeof(temporary));
    for(unsigned i=0;i<HOOK_COUNT;i++){
        const HookSpec *spec=&g_specs[i];BYTE *window=FindUnique(base,nt,spec);
        if(!window||spec->length>64){ProxyLog("F5 rejected: %s signature missing/ambiguous. Disable all CE visibility entries first.",spec->name);return FALSE;}
        BYTE *call=window+spec->offset;INT32 relative;
        memcpy(&relative,call+1,4);BYTE *target=call+5+relative;
        if(call[0]!=0xE8||target!=base+spec->targetRva||!Executable(nt,spec->targetRva,1)){
            ProxyLog("F5 rejected: %s call target differs (possible active CE hook).",spec->name);return FALSE;
        }
        temporary[i].window=window;temporary[i].call=call;temporary[i].length=spec->length;temporary[i].offset=spec->offset;
        memcpy(temporary[i].original,window,spec->length);memcpy(temporary[i].patched,window,spec->length);
    }
    U64 registry=Q((U64)base,0x1379EF0),count=(Q(registry,8)-Q(registry,0))>>6;
    U32 capacity=0x100000;while(capacity<count&&capacity<0x400000)capacity*=2;
    if(capacity<count){ProxyLog("F5 rejected: actor registry exceeds bounded capacity.");return FALSE;}
    Cache *cache=VirtualAlloc(NULL,(SIZE_T)capacity*sizeof(Cache),MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    BYTE *thunks=AllocateNear(base,65536);
    if(!cache||!thunks){if(cache)VirtualFree(cache,0,MEM_RELEASE);if(thunks)VirtualFree(thunks,0,MEM_RELEASE);ProxyLog("F5 rejected: allocation failed; no game code changed.");return FALSE;}
    for(unsigned i=0;i<HOOK_COUNT;i++){
        BYTE *thunk=thunks+i*16;thunk[0]=0xFF;thunk[1]=0x25;
        U64 wrapper=(U64)g_specs[i].wrapper;memcpy(thunk+6,&wrapper,8);thunk[14]=thunk[15]=0x90;
        INT64 displacement=thunk-(temporary[i].call+5);
        if(displacement<INT32_MIN||displacement>INT32_MAX){VirtualFree(cache,0,MEM_RELEASE);VirtualFree(thunks,0,MEM_RELEASE);ProxyLog("F5 rejected: near CALL range validation failed.");return FALSE;}
        INT32 rel=(INT32)displacement;temporary[i].thunk=thunk;
        temporary[i].patched[temporary[i].offset]=0xE8;memcpy(temporary[i].patched+temporary[i].offset+1,&rel,4);
    }
    DWORD old;
    if(!VirtualProtect(thunks,65536,PAGE_EXECUTE_READ,&old)){VirtualFree(cache,0,MEM_RELEASE);VirtualFree(thunks,0,MEM_RELEASE);ProxyLog("F5 rejected: cannot protect prepared code block.");return FALSE;}
    FlushInstructionCache(GetCurrentProcess(),thunks,65536);
    memcpy(g_hooks,temporary,sizeof(g_hooks));g_image=base;g_thunks=thunks;
    for(unsigned i=0;i<HOOK_COUNT;i++)g_originals[i]=base+g_specs[i].targetRva;
    g_config.base=(U64)base;g_config.registryAddress=(U64)base+0x1379EF0;g_config.localRefAddress=(U64)base+0x1302F28;
    g_config.cacheAddress=(U64)cache;g_config.capacity=capacity;
    const DWORD vtables[]={0xEE4520,0xEE5FE8,0xEE6830,0xEE6BA8,0xFE4770,0xFD10F8,0xF10600,0xF4A868,0xF23958,0xF37BB8,0xF3E8D0,0xF26E20};
    U64 *dest=&g_config.mesh;for(unsigned i=0;i<12;i++)dest[i]=(U64)base+vtables[i];
    g_ready=TRUE;ProxyLog("prepared %u unique hooks; cache=%u records (%u MiB). No code sites changed yet.",HOOK_COUNT,capacity,(unsigned)(capacity*sizeof(Cache)/(1024*1024)));
    return TRUE;
}

typedef struct {HANDLE handles[512];BYTE suspended[512];unsigned count;} ThreadSet;
static void ResumeClose(ThreadSet *set){
    for(unsigned i=0;i<set->count;i++){if(set->suspended[i])ResumeThread(set->handles[i]);CloseHandle(set->handles[i]);}
    set->count=0;
}
static BOOL OpenOtherThreads(ThreadSet *set){
    ZeroMemory(set,sizeof(*set));DWORD process=GetCurrentProcessId(),self=GetCurrentThreadId();
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);
    if(snapshot==INVALID_HANDLE_VALUE)return FALSE;
    THREADENTRY32 entry;entry.dwSize=sizeof(entry);BOOL ok=Thread32First(snapshot,&entry),good=ok;
    while(ok){
        if(entry.th32OwnerProcessID==process&&entry.th32ThreadID!=self){
            if(set->count>=512){good=FALSE;break;}
            HANDLE h=OpenThread(THREAD_SUSPEND_RESUME|THREAD_GET_CONTEXT|THREAD_QUERY_INFORMATION,FALSE,entry.th32ThreadID);
            if(!h){if(GetLastError()!=ERROR_INVALID_PARAMETER){good=FALSE;break;}}
            else set->handles[set->count++]=h;
        }
        ok=Thread32Next(snapshot,&entry);
    }
    if(!ok&&GetLastError()!=ERROR_NO_MORE_FILES)good=FALSE;
    CloseHandle(snapshot);if(!good)ResumeClose(set);return good;
}
static BOOL Pause(ThreadSet *set){
    for(unsigned i=0;i<set->count;i++){
        if(SuspendThread(set->handles[i])==(DWORD)-1){DWORD exitCode=STILL_ACTIVE;if(GetExitCodeThread(set->handles[i],&exitCode)&&exitCode!=STILL_ACTIVE)continue;return FALSE;}
        set->suspended[i]=1;
    }
    return TRUE;
}
static BOOL BusyInstruction(ThreadSet *set,BOOL *readable){
    *readable=TRUE;
    for(unsigned t=0;t<set->count;t++)if(set->suspended[t]){
        CONTEXT context;context.ContextFlags=CONTEXT_CONTROL;
        if(!GetThreadContext(set->handles[t],&context)){DWORD exitCode=STILL_ACTIVE;if(GetExitCodeThread(set->handles[t],&exitCode)&&exitCode!=STILL_ACTIVE)continue;*readable=FALSE;return FALSE;}
        for(unsigned i=0;i<HOOK_COUNT;i++)if(context.Rip>=(U64)g_hooks[i].call&&context.Rip<(U64)g_hooks[i].call+5)return TRUE;
    }
    return FALSE;
}
/* No allocation, CRT, file IO or logging below while other threads are paused.
   Code caves/DLL remain mapped even if a suspended thread is inside a wrapper. */
static BOOL ChangeSites(BOOL enable){
    SYSTEM_INFO system;GetSystemInfo(&system);SIZE_T pageSize=system.dwPageSize;
    BYTE *pages[HOOK_COUNT];DWORD protections[HOOK_COUNT];unsigned pageCount=0;
    for(unsigned i=0;i<HOOK_COUNT;i++){
        if(((UINT_PTR)g_hooks[i].call&(pageSize-1))+5>pageSize)return FALSE;
        BYTE *page=(BYTE*)((UINT_PTR)g_hooks[i].call&~(pageSize-1));unsigned j;
        for(j=0;j<pageCount;j++)if(pages[j]==page)break;
        if(j==pageCount)pages[pageCount++]=page;
    }
    for(unsigned attempt=0;attempt<16;attempt++){
        ThreadSet threads;if(!OpenOtherThreads(&threads))return FALSE;
        BOOL good=FALSE,busy=FALSE,readable=FALSE;unsigned changedProtections=0;
        __try {
            if(!Pause(&threads))__leave;
            busy=BusyInstruction(&threads,&readable);if(busy||!readable)__leave;
            for(unsigned i=0;i<HOOK_COUNT;i++){
                Hook *h=&g_hooks[i];
                if(enable){if(!Equal(h->window,h->original,h->length))__leave;}
                else if(!Equal(h->window,h->original,h->length)&&!Equal(h->window,h->patched,h->length))__leave;
            }
            /* __leave above exits only a loop's enclosing try, never writes. */
            for(unsigned i=0;i<pageCount;i++){
                if(!VirtualProtect(pages[i],pageSize,PAGE_EXECUTE_READWRITE,&protections[i]))__leave;
                changedProtections++;
            }
            for(unsigned i=0;i<HOOK_COUNT;i++){
                Hook *h=&g_hooks[i];const BYTE *data=(enable?h->patched:h->original)+h->offset;
                for(unsigned j=0;j<5;j++)((volatile BYTE*)h->call)[j]=data[j];
#ifdef SSO_PROXY_TESTING
                if(enable&&g_testFailAfterWrite==(LONG)i){g_testFailAfterWrite=-1;RaiseException(0xE0005510,0,0,NULL);}
#endif
            }
            good=TRUE;
            for(unsigned i=0;i<HOOK_COUNT;i++)if(!Equal(g_hooks[i].window,enable?g_hooks[i].patched:g_hooks[i].original,g_hooks[i].length))good=FALSE;
            if(!good&&enable){
                for(unsigned i=0;i<HOOK_COUNT;i++)for(unsigned j=0;j<5;j++)((volatile BYTE*)g_hooks[i].call)[j]=g_hooks[i].original[g_hooks[i].offset+j];
            }
            FlushInstructionCache(GetCurrentProcess(),NULL,0);
        } __finally {
            for(unsigned i=0;i<changedProtections;i++){DWORD ignored;VirtualProtect(pages[i],pageSize,protections[i],&ignored);}
            ResumeClose(&threads);
        }
        if(good)return TRUE;
        if(!busy)return FALSE;
        Sleep(2);
    }
    return FALSE;
}
BOOL VisibilityEnable(HMODULE module){
    if(g_installed){ProxyLog(g_config.active?"F5: hiding already enabled.":"F5 refused: a previous restore still needs recovery. Press F6 after removing the conflicting modifier.");return g_config.active!=0;}
    BOOL ready=FALSE;
    __try {ready=Prepare((BYTE*)module);}
    __except(EXCEPTION_EXECUTE_HANDLER){ProxyLog("F5 rejected: unreadable module/actor layout; no activation.");return FALSE;}
    if(!ready)return FALSE;
    if(g_epoch>=65535){ProxyLog("F5 rejected: cache epoch exhausted; restart game.");return FALSE;}
    g_config.active=0;g_config.epoch=++g_epoch;ZeroMemory((void*)g_config.hits,sizeof(g_config.hits));
    BOOL changed=FALSE;
    __try {changed=ChangeSites(TRUE);}
    __except(EXCEPTION_EXECUTE_HANDLER){changed=FALSE;}
    if(!changed){
        /* Retain recovery state even after an exceptional partial write. */
        __try {for(unsigned i=0;i<HOOK_COUNT;i++)if(!Equal(g_hooks[i].call,g_hooks[i].original+g_hooks[i].offset,5))g_installed=TRUE;}
        __except(EXCEPTION_EXECUTE_HANDLER){g_installed=TRUE;}
        ProxyLog("F5 rejected: code changed, a thread was busy, or patch/protection failed. Hiding remains off; recovery=%s.",g_installed?"F6/restart required":"not needed");return FALSE;
    }
    g_installed=TRUE;g_config.active=1;ProxyLog("F5: hiding ENABLED; all %u call sites verified. Category choices retained.",HOOK_COUNT);return TRUE;
}
BOOL VisibilityDisable(void){
    g_config.active=0;
    if(!g_installed){ProxyLog("F6: already restored; hiding off.");return TRUE;}
    BOOL restored=FALSE;
    __try {restored=ChangeSites(FALSE);}
    __except(EXCEPTION_EXECUTE_HANDLER){restored=FALSE;}
    if(!restored){ProxyLog("F6: switches set to passthrough, but exact byte restoration refused/failed. Do not unload the proxy; remove conflicting patches and retry, or restart game.");return FALSE;}
    g_installed=FALSE;ProxyLog("F6: all original calls RESTORED. Native fade-in may take a few seconds.");return TRUE;
}

#ifdef SSO_PROXY_TESTING
Config *VisibilityTestConfig(void){return &g_config;}
unsigned VisibilityTestHookCount(void){return HOOK_COUNT;}
void *VisibilityTestCall(unsigned i){return i<HOOK_COUNT?g_hooks[i].call:NULL;}
void *VisibilityTestWrapper(unsigned i){return i<HOOK_COUNT?g_specs[i].wrapper:NULL;}
BOOL VisibilityTestInstalled(void){return g_installed;}
void VisibilityTestFailAfterWrite(LONG index){g_testFailAfterWrite=index;}
#endif
