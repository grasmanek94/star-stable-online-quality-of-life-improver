/* Loader ABI adapter only. All visibility, settings and input code is shared C.
 * ReShade's documented AddonInit/AddonUninit contract and registration ABI are
 * resolved dynamically. API level 1 is sufficient: no graphics events are used.
 * References and compatibility limits: docs/LOADER_ADAPTERS.md.
 */
#include "sso_proxy/host.h"
#include <cstdint>

static HMODULE g_module;
static SRWLOCK g_addonLock=SRWLOCK_INIT;
using RegisterAddon=bool (*)(void *,uint32_t);
using UnregisterAddon=void (*)(void *);
static UnregisterAddon g_unregister;
static bool g_registered;

extern "C" __declspec(dllexport) const char *NAME="SSO Visibility";
extern "C" __declspec(dllexport) const char *DESCRIPTION="Native SSO visibility presets and optional cosmetic particle filters";

extern "C" __declspec(dllexport) BOOL SSOVisibilityInitialize(){return SsoHostStart(g_module);}
extern "C" __declspec(dllexport) void InitializeASI(){SSOVisibilityInitialize();}
extern "C" __declspec(dllexport) void SSOVisibilityShutdown(){SsoHostStop();}

extern "C" __declspec(dllexport) bool AddonInit(HMODULE module,HMODULE reshadeModule){
    if(module!=g_module||!reshadeModule)return false;
    AcquireSRWLockExclusive(&g_addonLock);
    if(g_registered){ReleaseSRWLockExclusive(&g_addonLock);return true;}
    auto reg=reinterpret_cast<RegisterAddon>(GetProcAddress(reshadeModule,"ReShadeRegisterAddon"));
    auto unreg=reinterpret_cast<UnregisterAddon>(GetProcAddress(reshadeModule,"ReShadeUnregisterAddon"));
    bool ok=reg&&unreg&&reg(module,1);
    if(ok){
        g_unregister=unreg;g_registered=true;
        if(!SsoHostStart(module)){unreg(module);g_registered=false;g_unregister=nullptr;ok=false;}
    }
    ReleaseSRWLockExclusive(&g_addonLock);return ok;
}
extern "C" __declspec(dllexport) void AddonUninit(HMODULE module,HMODULE reshadeModule){
    (void)reshadeModule;
    if(module!=g_module)return;
    AcquireSRWLockExclusive(&g_addonLock);
    if(g_registered){SsoHostStop();g_unregister(module);g_registered=false;g_unregister=nullptr;}
    ReleaseSRWLockExclusive(&g_addonLock);
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID reserved){
    (void)reserved;
    if(reason==DLL_PROCESS_ATTACH)g_module=module;
    else if(reason==DLL_PROCESS_DETACH)SsoHostDetach();
    return TRUE;
}
