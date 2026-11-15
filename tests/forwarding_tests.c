/* Runs only in this helper process. Never injects into or opens the game. */
#ifdef NDEBUG
#undef NDEBUG /* Tests must execute their assertions in every configuration. */
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

#ifdef NDEBUG
#error Tests require active assertions, including Release builds.
#endif

typedef HGLRC (WINAPI *ContextFn)(void);
typedef HDC (WINAPI *DcFn)(void);
typedef unsigned int (WINAPI *ErrorFn)(void);
typedef const unsigned char *(WINAPI *StringFn)(unsigned int);

static IMAGE_EXPORT_DIRECTORY *Exports(HMODULE module) {
    const BYTE *base=(const BYTE *)module;
    const IMAGE_DOS_HEADER *dos=(const IMAGE_DOS_HEADER *)base;
    assert(dos->e_magic==IMAGE_DOS_SIGNATURE);
    const IMAGE_NT_HEADERS64 *nt=(const IMAGE_NT_HEADERS64 *)(base+dos->e_lfanew);
    assert(nt->Signature==IMAGE_NT_SIGNATURE && nt->FileHeader.Machine==IMAGE_FILE_MACHINE_AMD64);
    return (IMAGE_EXPORT_DIRECTORY *)(base+nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT].VirtualAddress);
}

int wmain(int argc,wchar_t **argv) {
    assert(argc==2);
    assert(!GetModuleHandleW(L"opengl32.dll"));
    HMODULE proxy=LoadLibraryExW(argv[1],NULL,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if(!proxy)fwprintf(stderr,L"LoadLibraryExW(%ls) failed: %lu\n",argv[1],GetLastError());
    assert(proxy);
    ContextFn proxyContext=(ContextFn)GetProcAddress(proxy,"wglGetCurrentContext");
    assert(proxyContext && !proxyContext()); /* Triggers the lazy real-library load. */
    wchar_t path[32768];UINT length=GetSystemDirectoryW(path,32768);
    assert(length && length<32740);
    assert(wcscat_s(path,32768,L"\\opengl32.dll")==0);
    HMODULE system=LoadLibraryExW(path,NULL,LOAD_LIBRARY_SEARCH_SYSTEM32);
    assert(system && system!=proxy);
    ContextFn systemContext=(ContextFn)GetProcAddress(system,"wglGetCurrentContext");
    assert(systemContext && proxyContext()==systemContext());
    ErrorFn proxyError=(ErrorFn)GetProcAddress(proxy,"glGetError"),systemError=(ErrorFn)GetProcAddress(system,"glGetError");
    StringFn proxyString=(StringFn)GetProcAddress(proxy,"glGetString"),systemString=(StringFn)GetProcAddress(system,"glGetString");
    DcFn proxyDc=(DcFn)GetProcAddress(proxy,"wglGetCurrentDC"),systemDc=(DcFn)GetProcAddress(system,"wglGetCurrentDC");
    assert(proxyError && systemError && proxyString && systemString && proxyDc && systemDc);
    assert(proxyError()==systemError());
    assert(proxyString(0x1F02)==systemString(0x1F02));
    assert(proxyDc()==systemDc());

    IMAGE_EXPORT_DIRECTORY *actual=Exports(proxy),*expected=Exports(system);
    assert(actual->Base==expected->Base && actual->NumberOfNames==expected->NumberOfNames);
    assert(actual->NumberOfFunctions==expected->NumberOfFunctions && actual->NumberOfNames==368);
    const DWORD *names=(const DWORD *)((const BYTE *)system+expected->AddressOfNames);
    const WORD *ordinals=(const WORD *)((const BYTE *)system+expected->AddressOfNameOrdinals);
    const DWORD *proxyNames=(const DWORD *)((const BYTE *)proxy+actual->AddressOfNames);
    const WORD *proxyOrdinals=(const WORD *)((const BYTE *)proxy+actual->AddressOfNameOrdinals);
    for(DWORD i=0;i<expected->NumberOfNames;i++) {
        const char *name=(const char *)system+names[i];
        assert(strcmp(name,(const char *)proxy+proxyNames[i])==0 && ordinals[i]==proxyOrdinals[i]);
        FARPROC named=GetProcAddress(proxy,name);
        FARPROC ordinal=GetProcAddress(proxy,MAKEINTRESOURCEA(expected->Base+ordinals[i]));
        assert(named && named==ordinal);
    }
    printf("FORWARDING_TESTS_PASS %lu; name/ordinal parity; lazy System32 load; 4 GL/WGL smoke calls\n",actual->NumberOfNames);
    /* The proxy intentionally pins itself until exit; no live unloading test. */
    return 0;
}
