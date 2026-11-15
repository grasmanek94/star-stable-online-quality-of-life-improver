#pragma once
#include "proxy_internal.h"

#define SSO_CATEGORY_COUNT 14
#define SSO_PRESET_COUNT 10
typedef struct {
    WCHAR name[96];
    BYTE hide[SSO_CATEGORY_COUNT];
    BOOL protectGameplay;
} SsoPreset;
typedef struct {
    SsoPreset items[SSO_PRESET_COUNT];
    unsigned defaultPreset;
} SsoPresetBank;

void SsoPresetsDefaults(SsoPresetBank *bank);
BOOL SsoPresetsLoad(const WCHAR *path,SsoPresetBank *bank);
extern const WCHAR *const g_categoryKeys[SSO_CATEGORY_COUNT];
