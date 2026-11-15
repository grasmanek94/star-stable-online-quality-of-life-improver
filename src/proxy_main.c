#include "sso_proxy/host.h"
#include <wchar.h>
#include "gl_exports.inc"
static INIT_ONCE g_once=INIT_ONCE_STATIC_INIT;
static HMODULE g_self,g_real;

static BOOL CALLBACK Initialize(PINIT_ONCE once,PVOID parameter,PVOID *context){
    (void)once;(void)parameter;(void)context;
    static WCHAR system[32768];UINT length=GetSystemDirectoryW(system,32768);
    if(!length||length>32740){ProxyLog("fatal: cannot resolve Windows System32.");TerminateProcess(GetCurrentProcess(),ERROR_MOD_NOT_FOUND);return FALSE;}
    wcscat_s(system,32768,L"\\opengl32.dll");
    g_real=LoadLibraryExW(system,NULL,LOAD_LIBRARY_SEARCH_SYSTEM32);
    if(!g_real||g_real==g_self){ProxyLog("fatal: cannot load real System32 OpenGL (error %lu).",GetLastError());TerminateProcess(GetCurrentProcess(),ERROR_MOD_NOT_FOUND);return FALSE;}
    for(unsigned i=0;i<GL_EXPORT_COUNT;i++){
        FARPROC proc=GetProcAddress(g_real,g_glNames[i]);
        if(!proc){ProxyLog("fatal: System32 OpenGL export missing: %s @%u.",g_glNames[i],g_glOrdinals[i]);TerminateProcess(GetCurrentProcess(),ERROR_PROC_NOT_FOUND);return FALSE;}
        InterlockedExchangePointer((PVOID volatile*)&g_glFunctions[i],(PVOID)proc);
    }
    HMODULE pinned;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCWSTR)g_self,&pinned);
    return TRUE;
}
void ProxyInitialize(void){
    if(!InitOnceExecuteOnce(&g_once,Initialize,NULL,NULL)){
        ProxyLog("fatal: OpenGL initialization failed.");TerminateProcess(GetCurrentProcess(),ERROR_DLL_INIT_FAILED);
    }
    SsoHostStart(g_self);
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID reserved){
    (void)reserved;
    if(reason==DLL_PROCESS_ATTACH)g_self=module;
    else if(reason==DLL_PROCESS_DETACH)SsoHostDetach();
    /* Static CRT needs thread notifications. No LoadLibrary, waits, scanning,
       thread creation, file IO or code patching takes place under loader lock. */
    return TRUE;
}
