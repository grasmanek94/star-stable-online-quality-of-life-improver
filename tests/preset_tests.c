#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sso_proxy/presets.h"
#include <assert.h>
#include <stdio.h>
#include <stdarg.h>
#include <wchar.h>
#include <string.h>
void ProxyLog(const char *format,...){(void)format;}
static void Equal(const SsoPreset *a,const SsoPreset *b){assert(memcmp(a->hide,b->hide,14)==0&&a->protectGameplay==b->protectGameplay);}
int wmain(int argc,wchar_t **argv){
    assert(argc==2);SsoPresetBank defaults,bank;SsoPresetsDefaults(&defaults);
    assert(defaults.defaultPreset==8);
    for(unsigned i=0;i<14;i++){
        assert(defaults.items[0].hide[i]==1);
        assert(defaults.items[8].hide[i]==(i<3));
        assert(defaults.items[9].hide[i]==(i<2));
    }
    for(unsigned p=1;p<10;p++){
        unsigned changes=0;
        for(unsigned i=0;i<14;i++){assert(defaults.items[p].hide[i]<=defaults.items[p-1].hide[i]);changes+=defaults.items[p].hide[i]!=defaults.items[p-1].hide[i];}
        assert(changes||(p==5&&defaults.items[p].protectGameplay&&!defaults.items[p-1].protectGameplay));
        assert(defaults.items[p].protectGameplay==(p>=5));
    }
    assert(SsoPresetsLoad(argv[1],&bank)&&bank.defaultPreset==8);
    for(unsigned p=0;p<10;p++)Equal(&defaults.items[p],&bank.items[p]);
    WCHAR folder[MAX_PATH],file[MAX_PATH];assert(GetTempPathW(MAX_PATH,folder));assert(GetTempFileNameW(folder,L"SSO",0,file));
    assert(WritePrivateProfileStringW(L"General",L"DefaultPreset",L"99",file));
    assert(WritePrivateProfileStringW(L"Preset8",L"PlayerPets",L"9",file));
    assert(WritePrivateProfileStringW(L"Preset0",L"PlayerActors",L"0",file));
    assert(SsoPresetsLoad(file,&bank));assert(bank.defaultPreset==8&&bank.items[8].hide[2]==1&&bank.items[0].hide[1]==1);
    assert(WritePrivateProfileStringW(L"General",L"DefaultPreset",L"9",file));
    assert(WritePrivateProfileStringW(L"Preset8",L"PlayerPets",L"0",file));
    assert(WritePrivateProfileStringW(L"Preset8",L"AllParticles",L"1",file));
    assert(WritePrivateProfileStringW(L"Preset8",L"ProtectGameplay",L"0",file));
    assert(SsoPresetsLoad(file,&bank));assert(bank.defaultPreset==9&&!bank.items[8].hide[2]&&bank.items[8].hide[12]&&!bank.items[8].protectGameplay);
    assert(DeleteFileW(file));assert(!SsoPresetsLoad(file,&bank));Equal(&bank.items[8],&defaults.items[8]);
    assert(GetFileAttributesW(file)==INVALID_FILE_ATTRIBUTES);
    puts("PRESET_TESTS_PASS; default8, minimal9, immutable0, gradual levels, INI overrides, validation, missing-file fallback");return 0;
}
