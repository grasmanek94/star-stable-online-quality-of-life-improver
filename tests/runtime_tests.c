/* Native test executable: patches only a synthetic PE image allocated here. */
#ifdef NDEBUG
#undef NDEBUG /* Keep assertions and their side effects in Release tests. */
#endif
#include "sso_proxy/proxy_internal.h"
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <assert.h>
#include "fixtures/baseline.inc"
#include "layout_specs.inc"
void *VisibilityTestConfig(void);
unsigned VisibilityTestHookCount(void);
void *VisibilityTestCall(unsigned i);
void *VisibilityTestWrapper(unsigned i);
extern void *g_originals[];
int ProxyHideParticles(unsigned long long actor);
BOOL VisibilityTestInstalled(void);
void VisibilityTestFailAfterWrite(LONG index);
int ClientAudit(const wchar_t *path);
int ProxyHideActor(unsigned long long actor);
static volatile LONG stop,beats;
void ProxyLog(const char *format,...){va_list v;va_start(v,format);vprintf(format,v);puts("");va_end(v);}
static DWORD WINAPI Background(void *unused){(void)unused;while(!InterlockedCompareExchange(&stop,0,0)){InterlockedIncrement(&beats);Sleep(1);}return 0;}
static void Q(BYTE *p,SIZE_T off,unsigned long long v){memcpy(p+off,&v,8);}
static void D(BYTE *p,SIZE_T off,DWORD v){memcpy(p+off,&v,4);}
static void Ref(BYTE *p,SIZE_T off,DWORD generation,DWORD index){D(p,off+8,generation);D(p,off+12,index);}
static BYTE expectedWindows[21][256];
static void AssertOriginal(BYTE *image){
    for(unsigned i=0;i<sizeof(fixture_windows)/sizeof(fixture_windows[0]);i++)assert(memcmp(image+fixture_windows[i].rva,expectedWindows[i],fixture_windows[i].length)==0);
}
static void InstallLayoutFixture(BYTE *image,DWORD shift){
    memcpy(image+REGISTRY_RECORDS_REFERENCE_RVA,registry_records_window,sizeof(registry_records_window));
    for(unsigned i=0;i<TARGET_GROUP_COUNT;i++)memcpy(image+g_targetGroups[i].referenceRva,g_targetGroups[i].window,g_targetGroups[i].length);
    for(unsigned i=0;i<2;i++){
        const BindingSpec *binding=&g_bindings[i];BYTE *source=image+binding->referenceSourceRva;
        memcpy(source,binding->window,binding->length);
        INT32 relative=(INT32)((INT64)binding->referenceTargetRva+shift-binding->referenceSourceRva-binding->instructionEnd);
        memcpy(source+binding->displacementOffset,&relative,4);
    }
    for(unsigned i=0;i<RTTI_CLASS_COUNT;i++){
        DWORD col=0x1200000+i*0x100,type=col+0x40,vtable=g_referenceVtables[i]+shift;
        Q(image,vtable-8,(UINT_PTR)image+col);D(image,col,1);D(image,col+12,type);D(image,col+16,col+0xC0);D(image,col+20,col);
        memcpy(image+type+16,g_rttiNames[i],strlen(g_rttiNames[i])+1);
        for(unsigned j=0;j<15;j++)Q(image,vtable+j*8,(UINT_PTR)image+0x1000);
    }
    /* The native grass helper moves independently of its caller. */
    memcpy(image+0x600000,g_targetGroups[8].window,g_targetGroups[8].length);
    BYTE *grass=image+fixture_windows[20].rva+fixture_windows[20].offset;
    INT32 relative=(INT32)((image+0x600000)-(grass+5));memcpy(grass+1,&relative,4);
    for(unsigned i=0;i<21;i++)memcpy(expectedWindows[i],image+fixture_windows[i].rva,fixture_windows[i].length);
}
static unsigned childCalls,nativeCalls;
static unsigned long long expectedActor;
static unsigned long long __fastcall ChildProbe(unsigned long long actor,unsigned long long context,unsigned long long scene){assert(actor==expectedActor&&context==0x1234&&scene==0x5678);childCalls++;return 0xCAFE;}
static unsigned long long __fastcall NativeProbe(unsigned long long actor,unsigned long long context,unsigned long long scene){assert(actor==expectedActor&&context==0x1234&&scene==0x5678);nativeCalls++;return 0xBEEF;}
int wmain(int argc,wchar_t **argv){
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc==3&&!wcscmp(argv[1],L"--inspect-client"))return ClientAudit(argv[2]);
    if(argc!=1){fputs("Usage: sso_runtime_tests [--inspect-client <SSOClient.exe>]\n",stderr);return 2;}
    unsigned passed=0;BYTE *image=VirtualAlloc(NULL,0x014B0000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(image);
    memcpy(image,fixture_header,sizeof(fixture_header));
    for(unsigned i=0;i<sizeof(fixture_windows)/sizeof(fixture_windows[0]);i++)memcpy(image+fixture_windows[i].rva,fixture_windows[i].bytes,fixture_windows[i].length);
    const DWORD layoutShift=0x1000;InstallLayoutFixture(image,layoutShift);
    BYTE *registry=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE),*records=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    BYTE *player=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE),*horse=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    assert(registry&&records&&player&&horse);
    Q(image,g_bindings[0].referenceTargetRva+layoutShift,(UINT_PTR)registry);Q(registry,0,(UINT_PTR)records);Q(registry,8,(UINT_PTR)records+64*8);
    Ref(image,g_bindings[1].referenceTargetRva+layoutShift,100,1);Q(records,64+32,(UINT_PTR)player);D(records,64+44,100);
    Q(player,0,(UINT_PTR)image+g_referenceVtables[SSO_VT_PLAYERSSO]+layoutShift);D(player,128,100);D(player,132,1);player[144]=68;
    Ref(player,1608,200,2);Q(records,128+32,(UINT_PTR)horse);D(records,128+44,200);
    Q(horse,0,(UINT_PTR)image+g_referenceVtables[SSO_VT_HORSE]+layoutShift);D(horse,128,200);D(horse,132,2);horse[144]=68;
    Ref(horse,152,100,1);
    VisibilityInitialize();BYTE *config=(BYTE*)VisibilityTestConfig();
    for(unsigned i=0;i<11;i++)assert(config[16+i]==1);passed++;
    IMAGE_DOS_HEADER *dos=(IMAGE_DOS_HEADER*)image;IMAGE_NT_HEADERS64 *nt=(IMAGE_NT_HEADERS64*)(image+dos->e_lfanew);
    WORD machine=nt->FileHeader.Machine;nt->FileHeader.Machine=IMAGE_FILE_MACHINE_I386;
    assert(!VisibilityEnable((HMODULE)image));AssertOriginal(image);passed++;nt->FileHeader.Machine=machine;
    horse[144]=64;assert(!VisibilityEnable((HMODULE)image));AssertOriginal(image);passed++;horse[144]=68;
    BYTE *rider=image+fixture_windows[0].rva;rider[0]=0;
    assert(!VisibilityEnable((HMODULE)image));rider[0]=fixture_windows[0].bytes[0];AssertOriginal(image);passed++;
    BYTE *gate=image+g_targetGroups[6].referenceRva;BYTE gateByte=gate[3];gate[3]^=2;
    assert(!VisibilityEnable((HMODULE)image));gate[3]=gateByte;AssertOriginal(image);passed++;
    BYTE *recordsCode=image+REGISTRY_RECORDS_REFERENCE_RVA;BYTE stride=recordsCode[41];recordsCode[41]=5;
    assert(!VisibilityEnable((HMODULE)image));recordsCode[41]=stride;AssertOriginal(image);passed++;
    const BindingSpec *localBinding=&g_bindings[1];BYTE *localCode=image+localBinding->referenceSourceRva;
    INT32 localDisplacement;memcpy(&localDisplacement,localCode+localBinding->displacementOffset,4);
    INT32 invalidDisplacement=(INT32)(0x1000-localBinding->referenceSourceRva-localBinding->instructionEnd);
    memcpy(localCode+localBinding->displacementOffset,&invalidDisplacement,4);
    assert(!VisibilityEnable((HMODULE)image));memcpy(localCode+localBinding->displacementOffset,&localDisplacement,4);AssertOriginal(image);passed++;
    BYTE *duplicate=image+0x700000;memcpy(duplicate,rider,fixture_windows[0].length);
    assert(!VisibilityEnable((HMODULE)image));ZeroMemory(duplicate,fixture_windows[0].length);AssertOriginal(image);passed++;
    BYTE *extraTable=image+0x1202000;Q(extraTable,0,(UINT_PTR)image+0x1200000);
    for(unsigned i=0;i<15;i++)Q(extraTable,8+i*8,(UINT_PTR)image+0x1000);
    assert(!VisibilityEnable((HMODULE)image));ZeroMemory(extraTable,16*8);AssertOriginal(image);passed++;
    HANDLE background=CreateThread(NULL,0,Background,NULL,0,NULL);assert(background);
    for(unsigned wait=0;!beats&&wait<200;wait++)Sleep(10);
    assert(beats>0);
    /* A changed timestamp/image size is accepted when layout/ownership/AOBs validate. */
    nt->FileHeader.TimeDateStamp=0x6AF719CF;nt->OptionalHeader.SizeOfImage=0x014B0000;
    assert(VisibilityEnable((HMODULE)image));assert(config[0]==1&&VisibilityTestInstalled());
    assert(g_originals[20]==image+0x600000);assert(*(UINT_PTR*)(config+72)==(UINT_PTR)image+g_bindings[0].referenceTargetRva+layoutShift);passed++;
    assert(VisibilityTestHookCount()==21);for(unsigned i=0;i<21;i++){BYTE *p=VisibilityTestCall(i);assert(p[0]==(i==18?0xE9:0xE8));assert(memcmp(p,fixture_windows[i].bytes+fixture_windows[i].offset,5)!=0);}passed++;
    LONG before=beats;for(unsigned wait=0;beats==before&&wait<200;wait++)Sleep(10);
    if(beats==before){DWORD exitCode;GetExitCodeThread(background,&exitCode);printf("BACKGROUND_STALLED beats=%ld exit=%lu\n",beats,exitCode);}
    assert(beats>before);passed++;
    assert(ProxyHideActor(0xDEADBEEF)==0&&VisibilityFaultCount()>0);passed++;
    VisibilityToggleCategory(2);assert(config[18]==0);passed++;
    BYTE *particle=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(particle);
    Q(particle,0,(UINT_PTR)image+g_referenceVtables[SSO_VT_PARTICLEEX]+layoutShift);expectedActor=(UINT_PTR)particle;
    BYTE *child=image+g_targetGroups[7].referenceRva;child[0]=0xFF;child[1]=0x25;memset(child+2,0,4);Q(child,6,(UINT_PTR)ChildProbe);
    DWORD childOld;assert(VirtualProtect(child,16,PAGE_EXECUTE_READWRITE,&childOld));FlushInstructionCache(GetCurrentProcess(),child,16);
    void *savedContinuation=g_originals[18];g_originals[18]=(void*)NativeProbe;
    typedef unsigned long long (__fastcall *ParticleEntry)(unsigned long long,unsigned long long,unsigned long long);
    ParticleEntry entry=(ParticleEntry)VisibilityTestWrapper(18);
    config[28]=0;assert(entry(expectedActor,0x1234,0x5678)==0xBEEF&&nativeCalls==1&&childCalls==0);passed++;
    config[28]=1;assert(entry(expectedActor,0x1234,0x5678)==0xCAFE&&nativeCalls==1&&childCalls==1);passed++;
    LONG particleFaults=VisibilityFaultCount();assert(!ProxyHideParticles(0xDEADBEEF)&&VisibilityFaultCount()>particleFaults);passed++;
    config[28]=0;g_originals[18]=savedContinuation;
    DWORD epoch;memcpy(&epoch,config+100,4);
    assert(VisibilityDisable());assert(!config[0]&&!VisibilityTestInstalled());AssertOriginal(image);passed++;
    assert(VisibilityEnable((HMODULE)image));assert(config[18]==0);DWORD next;memcpy(&next,config+100,4);assert(next==epoch+1);passed++;
    DWORD old;assert(VirtualProtect(rider,1,PAGE_EXECUTE_READWRITE,&old));BYTE original=rider[0];rider[0]=0x90;
    DWORD ignored;assert(VirtualProtect(rider,1,old,&ignored));
    assert(!VisibilityDisable()&&!config[0]&&VisibilityTestInstalled()&&rider[0]==0x90);passed++;
    assert(VirtualProtect(rider,1,PAGE_EXECUTE_READWRITE,&old));rider[0]=original;assert(VirtualProtect(rider,1,old,&ignored));
    assert(VisibilityDisable());AssertOriginal(image);passed++;
    VisibilityTestFailAfterWrite(1);assert(!VisibilityEnable((HMODULE)image));assert(!config[0]&&VisibilityTestInstalled());passed++;
    assert(VisibilityDisable());AssertOriginal(image);passed++;
    VisibilityTestFailAfterWrite(18);assert(!VisibilityEnable((HMODULE)image));assert(!config[0]&&VisibilityTestInstalled());
    g_originals[18]=(void*)NativeProbe;assert(entry(expectedActor,0x1234,0x5678)==0xBEEF&&nativeCalls==2);g_originals[18]=savedContinuation;passed++;
    assert(VisibilityDisable());AssertOriginal(image);passed++;
    assert(VisibilityEnable((HMODULE)image)&&VisibilityDisable());AssertOriginal(image);passed++;
    assert(VisibilityDisable());passed++;
    InterlockedExchange(&stop,1);assert(WaitForSingleObject(background,5000)==WAIT_OBJECT_0);CloseHandle(background);
    printf("NATIVE_PROXY_TESTS_PASS %u; 21 hooks; no game process accessed\n",passed);return 0;
}
