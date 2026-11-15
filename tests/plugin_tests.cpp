#ifdef NDEBUG
#undef NDEBUG
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cassert>
#include <cstdio>
#include <cstdint>

static unsigned registrations,unregistrations;
static bool allowRegistration;
static HMODULE expectedModule;
extern "C" __declspec(dllexport) bool ReShadeRegisterAddon(void *module,uint32_t version){
    assert(module==expectedModule&&version==1);
    if(!allowRegistration)return false;
    ++registrations;return true;
}
extern "C" __declspec(dllexport) void ReShadeUnregisterAddon(void *module){assert(module==expectedModule);++unregistrations;}

int wmain(int argc,wchar_t **argv){
    assert(argc==2);HMODULE module=LoadLibraryW(argv[1]);assert(module);expectedModule=module;
    auto initialize=reinterpret_cast<BOOL(*)()>(GetProcAddress(module,"SSOVisibilityInitialize"));
    auto asi=reinterpret_cast<void(*)()>(GetProcAddress(module,"InitializeASI"));
    auto shutdown=reinterpret_cast<void(*)()>(GetProcAddress(module,"SSOVisibilityShutdown"));
    auto initAddon=reinterpret_cast<bool(*)(HMODULE,HMODULE)>(GetProcAddress(module,"AddonInit"));
    auto uninitAddon=reinterpret_cast<void(*)(HMODULE,HMODULE)>(GetProcAddress(module,"AddonUninit"));
    assert(initialize&&asi&&shutdown&&initAddon&&uninitAddon);
    auto name=reinterpret_cast<const char *const *>(GetProcAddress(module,"NAME"));assert(name&&*name&&**name);
    HMODULE fake=GetModuleHandleW(NULL);
    assert(!initAddon(nullptr,fake)&&!initAddon(module,nullptr));
    assert(!initAddon(module,fake)&&registrations==0);
    allowRegistration=true;assert(initAddon(module,fake)&&registrations==1);
    assert(initAddon(module,fake)&&registrations==1);
    assert(initialize()&&initialize());asi(); /* Non-game host: no worker or game access. */
    uninitAddon(nullptr,fake);assert(unregistrations==0);
    uninitAddon(module,fake);uninitAddon(module,fake);assert(unregistrations==1);
    assert(initAddon(module,fake)&&registrations==2);uninitAddon(module,fake);assert(unregistrations==2);
    shutdown();shutdown();assert(FreeLibrary(module));
    puts("PLUGIN_LOADER_TESTS_PASS; explicit/ASI initialization, ReShade negotiation, idempotent lifecycle, non-game host");
    return 0;
}
