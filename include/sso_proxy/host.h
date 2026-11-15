#pragma once
#include "proxy_internal.h"
#ifdef __cplusplus
extern "C" {
#endif
BOOL SsoHostStart(HMODULE module);
void SsoHostStop(void);
void SsoHostDetach(void);
extern volatile LONG g_currentPreset;
#ifdef __cplusplus
}
#endif
