#include "sso_proxy/presets.h"
#include <wchar.h>
#include <stdlib.h>

const WCHAR *const g_categoryKeys[SSO_CATEGORY_COUNT]={
    L"PlayerHorses",L"PlayerActors",L"PlayerPets",L"NpcPets",L"NpcActors",L"NpcHorses",
    L"StandaloneHorses",L"SaleHorses",L"Coins",L"QuestMarkers",L"NpcText",
    L"AmbientParticles",L"AllParticles",L"DetailGrass"
};

void SsoPresetsDefaults(SsoPresetBank *bank){
    static const WCHAR *const names[10]={L"Everything (broad)",L"Aggressive: keep quest markers",
        L"Aggressive: keep dialogue text",L"Aggressive: keep collectibles",L"Aggressive: ambient particles only",
        L"Gameplay guards enabled",L"Keep NPC people",L"Players and ambient decoration",
        L"Other riders, horses and pets",L"Other riders and horses only"};
    ZeroMemory(bank,sizeof(*bank));bank->defaultPreset=8;
    for(unsigned p=0;p<10;p++){
        wcscpy_s(bank->items[p].name,96,names[p]);
        if(p==0)for(unsigned i=0;i<SSO_CATEGORY_COUNT;i++)bank->items[p].hide[i]=1;
        else bank->items[p]=bank->items[p-1];
        wcscpy_s(bank->items[p].name,96,names[p]);
        bank->items[p].protectGameplay=p>=5;
        if(p==1)bank->items[p].hide[9]=0;
        if(p==2)bank->items[p].hide[10]=0;
        if(p==3)bank->items[p].hide[8]=0;
        if(p==4)bank->items[p].hide[12]=0;
        if(p==6)bank->items[p].hide[4]=0;
        if(p==7){bank->items[p].hide[3]=0;bank->items[p].hide[5]=0;bank->items[p].hide[6]=0;bank->items[p].hide[7]=0;}
        if(p==8){bank->items[p].hide[11]=0;bank->items[p].hide[13]=0;}
        if(p==9)bank->items[p].hide[2]=0;
    }
}
static BOOL ReadBoolean(const WCHAR *path,const WCHAR *section,const WCHAR *key,BOOL fallback){
    WCHAR value[32];GetPrivateProfileStringW(section,key,L"",value,32,path);
    if(!value[0])return fallback;
    if(wcscmp(value,L"0")==0)return FALSE;
    if(wcscmp(value,L"1")==0)return TRUE;
    ProxyLog("INI: invalid [%ls] %ls=%ls; using default %u.",section,key,value,(unsigned)fallback);
    return fallback;
}
BOOL SsoPresetsLoad(const WCHAR *path,SsoPresetBank *bank){
    SsoPresetsDefaults(bank);
    if(GetFileAttributesW(path)==INVALID_FILE_ATTRIBUTES){ProxyLog("INI not found; using built-in presets, default 8.");return FALSE;}
    WCHAR number[32],*end=NULL;GetPrivateProfileStringW(L"General",L"DefaultPreset",L"8",number,32,path);
    unsigned long selected=wcstoul(number,&end,10);
    if(end!=number&&!*end&&selected<SSO_PRESET_COUNT)bank->defaultPreset=(unsigned)selected;
    else ProxyLog("INI: invalid DefaultPreset; using 8.");
    for(unsigned p=1;p<10;p++){
        WCHAR section[24],name[96];swprintf_s(section,24,L"Preset%u",p);
        GetPrivateProfileStringW(section,L"Name",bank->items[p].name,name,96,path);
        wcscpy_s(bank->items[p].name,96,name);
        for(unsigned i=0;i<SSO_CATEGORY_COUNT;i++)bank->items[p].hide[i]=(BYTE)ReadBoolean(path,section,g_categoryKeys[i],bank->items[p].hide[i]);
        bank->items[p].protectGameplay=ReadBoolean(path,section,L"ProtectGameplay",bank->items[p].protectGameplay);
    }
    /* Preset0 is deliberately immutable: every supported filter, guards off. */
    return TRUE;
}
