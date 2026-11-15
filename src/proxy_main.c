#include "sso_proxy/proxy_internal.h"
#include <process.h>
#include <stdarg.h>
#include <stdio.h>
#include <wchar.h>
#include "gl_exports.inc"
static INIT_ONCE g_once=INIT_ONCE_STATIC_INIT;
static HMODULE g_self,g_real;
static HANDLE g_log=INVALID_HANDLE_VALUE;
static volatile LONG g_stop;
static volatile LONG g_workerStarted;
static BOOL g_gameHost;

void ProxyLog(const char *format,...){
    char message[1200],line[1400];va_list args;va_start(args,format);
    vsnprintf_s(message,sizeof(message),_TRUNCATE,format,args);va_end(args);
    SYSTEMTIME time;GetSystemTime(&time);
    int n=_snprintf_s(line,sizeof(line),_TRUNCATE,"%04u-%02u-%02u %02u:%02u:%02u UTC | %s\r\n",time.wYear,time.wMonth,time.wDay,time.wHour,time.wMinute,time.wSecond,message);
    if(n<0)return;
    if(g_log!=INVALID_HANDLE_VALUE){DWORD written;WriteFile(g_log,line,(DWORD)n,&written,NULL);}
    else OutputDebugStringA(line);
}
static BOOL IsGameHost(void){
    static WCHAR filename[32768];DWORD n=GetModuleFileNameW(NULL,filename,32768);
    if(!n||n>=32768)return FALSE;
    WCHAR *slash=wcsrchr(filename,L'\\');const WCHAR *base=slash?slash+1:filename;
    return _wcsicmp(base,L"SSOClient.exe")==0;
}
static unsigned __stdcall Hotkeys(void *unused){
    (void)unused;
    const int keys[13]={VK_F5,VK_F6,VK_NUMPAD1,VK_NUMPAD2,VK_NUMPAD3,VK_NUMPAD4,VK_NUMPAD5,VK_NUMPAD6,VK_NUMPAD7,VK_NUMPAD8,VK_NUMPAD9,VK_NUMPAD0,VK_DECIMAL};
    BYTE previous[13]={0};LONG lastFaults=0;
    ProxyLog("hotkeys ready; F5 enable, F6 restore; Ctrl+Num1..9,0 toggle categories; Ctrl+NumDecimal floating text. NumLock ON. Initial hiding OFF, defaults all 1.");
    while(!InterlockedCompareExchange(&g_stop,0,0)){
        DWORD foregroundPid=0;HWND foreground=GetForegroundWindow();if(foreground)GetWindowThreadProcessId(foreground,&foregroundPid);
        BOOL active=foregroundPid==GetCurrentProcessId();BOOL ctrl=(GetAsyncKeyState(VK_CONTROL)&0x8000)!=0;
        for(unsigned i=0;i<13;i++){
            BYTE pressed=(GetAsyncKeyState(keys[i])&0x8000)!=0;
            if(active&&pressed&&!previous[i]){
                if(i==0)VisibilityEnable(GetModuleHandleW(NULL));
                else if(i==1)VisibilityDisable();
                else if(ctrl)VisibilityToggleCategory(i-2);
            }
            previous[i]=pressed;
        }
        LONG faults=VisibilityFaultCount();
        if(faults!=lastFaults){ProxyLog("native classifier guarded %ld unreadable-object access(es); affected decisions fell back to native behavior.",faults);lastFaults=faults;}
        Sleep(20);
    }
    return 0;
}
static BOOL CALLBACK Initialize(PINIT_ONCE once,PVOID parameter,PVOID *context){
    (void)once;(void)parameter;(void)context;
    static WCHAR file[32768];DWORD n=GetModuleFileNameW(g_self,file,32768);
    if(n&&n<32720){WCHAR *slash=wcsrchr(file,L'\\');if(slash){slash[1]=0;wcscat_s(file,32768,L"SSO-visibility-proxy.log");g_log=CreateFileW(file,FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,NULL,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);}}
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
    VisibilityInitialize();
    ProxyLog("SSO visibility OpenGL proxy x64 v1; real library=%ls; %u exports forwarded. Baseline client645.348067; hiding off.",system,GL_EXPORT_COUNT);
    g_gameHost=IsGameHost();
    if(!g_gameHost)ProxyLog("host is not SSOClient.exe; forwarding only, no hotkeys or game patches.");
    return TRUE;
}
void ProxyInitialize(void){
    if(!InitOnceExecuteOnce(&g_once,Initialize,NULL,NULL)){
        ProxyLog("fatal: OpenGL initialization failed.");TerminateProcess(GetCurrentProcess(),ERROR_DLL_INIT_FAILED);
    }
    /* Start the worker after releasing InitOnce and after DLL initialization. */
    if(g_gameHost&&InterlockedCompareExchange(&g_workerStarted,1,0)==0){
        uintptr_t thread=_beginthreadex(NULL,0,Hotkeys,NULL,0,NULL);
        if(thread)CloseHandle((HANDLE)thread);else ProxyLog("hotkey worker creation failed; graphics forwarding remains active.");
    }
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID reserved){
    (void)reserved;
    if(reason==DLL_PROCESS_ATTACH)g_self=module;
    else if(reason==DLL_PROCESS_DETACH)InterlockedExchange(&g_stop,1);
    /* Static CRT needs thread notifications. No LoadLibrary, waits, scanning,
       thread creation, file IO or code patching takes place under loader lock. */
    return TRUE;
}
