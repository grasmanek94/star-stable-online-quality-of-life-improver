#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
void ProxyLog(const char *format,...);
void VisibilityInitialize(void);
BOOL VisibilityEnable(HMODULE image);
BOOL VisibilityDisable(void);
void VisibilityToggleCategory(unsigned index);
LONG VisibilityFaultCount(void);
extern const char *g_categoryNames[11];
