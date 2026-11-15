#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void ProxyLog(const char *format,...);
void VisibilityInitialize(void);
BOOL VisibilityEnable(HMODULE image);
BOOL VisibilityDisable(void);
void VisibilityToggleCategory(unsigned index);
LONG VisibilityFaultCount(void);
BOOL VisibilityApplyOptions(const BYTE flags[14],BOOL protectGameplay);
extern const char *g_categoryNames[14];

#ifdef __cplusplus
}
#endif
