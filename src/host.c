/* Common controller for the proxy, ReShade and explicit-entry ASI/DLL loaders. */
#include "sso_proxy/host.h"
#include "sso_proxy/presets.h"
#include "layout_specs.inc"
#include <process.h>
#include <stdarg.h>
#include <stdio.h>
#include <wchar.h>

static INIT_ONCE g_hostOnce=INIT_ONCE_STATIC_INIT;
static SRWLOCK g_lifecycleLock=SRWLOCK_INIT;
static HMODULE g_hostModule;
static HANDLE g_worker,g_controllerMutex,g_log=INVALID_HANDLE_VALUE;
static volatile LONG g_stop;
static BOOL g_gameHost,g_ownsController;
static WCHAR g_iniPath[32768];
static SsoPresetBank g_presets;
volatile LONG g_currentPreset=8;

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
    WCHAR filename[32768];DWORD n=GetModuleFileNameW(NULL,filename,32768);
    if(!n||n>=32768)return FALSE;
    WCHAR *slash=wcsrchr(filename,L'\\');return _wcsicmp(slash?slash+1:filename,L"SSOClient.exe")==0;
}
static void ApplyPreset(unsigned index,BOOL enable){
    if(index>=10)return;
    const SsoPreset *preset=&g_presets.items[index];
    if(!VisibilityApplyOptions(preset->hide,preset->protectGameplay))return;
    InterlockedExchange(&g_currentPreset,(LONG)index);
    ProxyLog("preset %u: %ls; gameplay guards=%u%s",index,preset->name,(unsigned)preset->protectGameplay,index==0?"; BROAD particle/cue suppression":"");
    if(enable)VisibilityEnable(GetModuleHandleW(NULL));
}
static unsigned __stdcall Hotkeys(void *unused){
    (void)unused;BYTE previous[13]={0};LONG faultsBefore=0;
    const int keys[13]={VK_F5,VK_F6,VK_F7,VK_NUMPAD0,VK_NUMPAD1,VK_NUMPAD2,VK_NUMPAD3,VK_NUMPAD4,VK_NUMPAD5,VK_NUMPAD6,VK_NUMPAD7,VK_NUMPAD8,VK_NUMPAD9};
    ProxyLog("controls ready: F5 enable, F6 restore, F7 reload INI, Ctrl+Numpad0 all, 1..9 presets. NumLock ON. Hiding starts OFF.");
    while(!InterlockedCompareExchange(&g_stop,0,0)){
        DWORD foregroundPid=0;HWND foreground=GetForegroundWindow();if(foreground)GetWindowThreadProcessId(foreground,&foregroundPid);
        BOOL foregroundGame=foregroundPid==GetCurrentProcessId(),ctrl=(GetAsyncKeyState(VK_CONTROL)&0x8000)!=0;
        for(unsigned i=0;i<13;i++){
            BYTE pressed=(GetAsyncKeyState(keys[i])&0x8000)!=0;
            if(foregroundGame&&pressed&&!previous[i]){
                if(i==0)VisibilityEnable(GetModuleHandleW(NULL));
                else if(i==1)VisibilityDisable();
                else if(i==2){SsoPresetsLoad(g_iniPath,&g_presets);ApplyPreset((unsigned)g_currentPreset,FALSE);ProxyLog("INI reloaded: %ls",g_iniPath);}
                else if(ctrl)ApplyPreset(i-3,TRUE);
            }
            previous[i]=pressed;
        }
        LONG faults=VisibilityFaultCount();
        if(faults!=faultsBefore){ProxyLog("guarded classifier read failures=%ld; affected decisions used native behavior.",faults);faultsBefore=faults;}
        Sleep(20);
    }
    return 0;
}
static BOOL CALLBACK InitializeHost(PINIT_ONCE once,PVOID parameter,PVOID *context){
    (void)once;(void)parameter;(void)context;
    static WCHAR folder[32768],logPath[32768];DWORD n=GetModuleFileNameW(g_hostModule,folder,32768);
    if(!n||n>=32690)return FALSE;
    WCHAR *slash=wcsrchr(folder,L'\\');if(!slash)return FALSE;slash[1]=0;
    wcscpy_s(g_iniPath,32768,folder);wcscat_s(g_iniPath,32768,L"SSOVisibility.ini");
    wcscpy_s(logPath,32768,folder);wcscat_s(logPath,32768,L"SSO-visibility.log");
    g_log=CreateFileW(logPath,FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,NULL,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    g_gameHost=IsGameHost();
    if(!g_gameHost){ProxyLog("host is not SSOClient.exe; controller inactive.");return TRUE;}
    WCHAR mutexName[96];swprintf_s(mutexName,96,L"Local\\SSOVisibility.Controller.%lu",GetCurrentProcessId());
    g_controllerMutex=CreateMutexW(NULL,FALSE,mutexName);DWORD error=GetLastError();
    if(!g_controllerMutex||error==ERROR_ALREADY_EXISTS){if(g_controllerMutex){CloseHandle(g_controllerMutex);g_controllerMutex=NULL;}ProxyLog("another visibility host already owns this process; controller inactive.");return TRUE;}
    g_ownsController=TRUE;HMODULE pinned;
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCWSTR)g_hostModule,&pinned)){CloseHandle(g_controllerMutex);g_controllerMutex=NULL;g_ownsController=FALSE;return FALSE;}
    VisibilityInitialize();SsoPresetsLoad(g_iniPath,&g_presets);ApplyPreset(g_presets.defaultPreset,FALSE);
    ProxyLog("SSO Visibility " SSO_VERSION_STRING "; layout reference " SSO_LAYOUT_REFERENCE "; PE version gate disabled; INI=%ls; pinned until process exit.",g_iniPath);
    return TRUE;
}
BOOL SsoHostStart(HMODULE module){
    AcquireSRWLockExclusive(&g_lifecycleLock);g_hostModule=module;
    BOOL ok=InitOnceExecuteOnce(&g_hostOnce,InitializeHost,NULL,NULL);
    if(ok&&g_gameHost&&g_ownsController&&!g_worker){
        InterlockedExchange(&g_stop,0);
        g_worker=(HANDLE)_beginthreadex(NULL,0,Hotkeys,NULL,0,NULL);
        if(!g_worker){ProxyLog("controller thread creation failed.");ok=FALSE;}
    }
    ReleaseSRWLockExclusive(&g_lifecycleLock);return ok;
}
void SsoHostStop(void){
    AcquireSRWLockExclusive(&g_lifecycleLock);InterlockedExchange(&g_stop,1);
    if(g_worker){WaitForSingleObject(g_worker,INFINITE);CloseHandle(g_worker);g_worker=NULL;}
    if(g_ownsController)VisibilityDisable();
    ReleaseSRWLockExclusive(&g_lifecycleLock);
}
void SsoHostDetach(void){InterlockedExchange(&g_stop,1);}
