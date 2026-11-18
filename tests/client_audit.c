/* Optional discovery audit of a user-supplied PE file. Never loads or executes
   game code, opens a game process, changes the file, or installs any hooks. */
#include "sso_proxy/proxy_internal.h"
#include <stdio.h>
#include <string.h>
#include "layout_specs.inc"

BOOL VisibilityTestInspect(HMODULE image,void *sites[21],void *targets[21],
    uint64_t bindings[2],uint64_t vtables[RTTI_CLASS_COUNT]);

static BOOL Fits(SIZE_T at,SIZE_T size,SIZE_T total){return at<=total&&size<=total-at;}
static BYTE *MapClientData(const wchar_t *path,SIZE_T *imageSize){
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
    if(file==INVALID_HANDLE_VALUE)return NULL;
    LARGE_INTEGER length;BYTE *raw=NULL,*image=NULL;DWORD got;
    if(!GetFileSizeEx(file,&length)||length.QuadPart<4096||length.QuadPart>512*1024*1024)goto done;
    DWORD size=(DWORD)length.QuadPart;
    raw=VirtualAlloc(NULL,size,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!raw)goto done;
    if(!ReadFile(file,raw,size,&got,NULL)||got!=size)goto done;
    IMAGE_DOS_HEADER *dos=(IMAGE_DOS_HEADER*)raw;
    if(dos->e_magic!=IMAGE_DOS_SIGNATURE||dos->e_lfanew<0x40||!Fits(dos->e_lfanew,sizeof(IMAGE_NT_HEADERS64),size))goto done;
    IMAGE_NT_HEADERS64 *nt=(IMAGE_NT_HEADERS64*)(raw+dos->e_lfanew);
    if(nt->Signature!=IMAGE_NT_SIGNATURE||nt->FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64||nt->OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC||
       nt->FileHeader.SizeOfOptionalHeader<sizeof(IMAGE_OPTIONAL_HEADER64)||nt->FileHeader.NumberOfSections<1||nt->FileHeader.NumberOfSections>96)goto done;
    SIZE_T sectionOffset=(SIZE_T)((BYTE*)IMAGE_FIRST_SECTION(nt)-raw),headersEnd=sectionOffset+nt->FileHeader.NumberOfSections*sizeof(IMAGE_SECTION_HEADER);
    SIZE_T mappedSize=nt->OptionalHeader.SizeOfImage,headerSize=nt->OptionalHeader.SizeOfHeaders;
    if(mappedSize<4096||mappedSize>512*1024*1024||headerSize<headersEnd||!Fits(0,headerSize,size)||!Fits(0,headerSize,mappedSize))goto done;
    image=VirtualAlloc(NULL,mappedSize,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!image)goto done;
    memcpy(image,raw,headerSize);
    IMAGE_SECTION_HEADER *sections=IMAGE_FIRST_SECTION(nt);
    for(unsigned i=0;i<nt->FileHeader.NumberOfSections;i++){
        IMAGE_SECTION_HEADER *s=&sections[i];SIZE_T span=s->Misc.VirtualSize>s->SizeOfRawData?s->Misc.VirtualSize:s->SizeOfRawData;
        if(!Fits(s->PointerToRawData,s->SizeOfRawData,size)||!Fits(s->VirtualAddress,span,mappedSize))goto invalid;
        memcpy(image+s->VirtualAddress,raw+s->PointerToRawData,s->SizeOfRawData);
    }
    if(nt->OptionalHeader.NumberOfRvaAndSizes<=IMAGE_DIRECTORY_ENTRY_BASERELOC)goto invalid;
    IMAGE_DATA_DIRECTORY directory=nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_BASERELOC];
    if(!directory.Size||!Fits(directory.VirtualAddress,directory.Size,mappedSize))goto invalid;
    SIZE_T at=directory.VirtualAddress,end=at+directory.Size;
    uint64_t delta=(uint64_t)(UINT_PTR)image-nt->OptionalHeader.ImageBase;
    while(at<end){
        if(!Fits(at,sizeof(IMAGE_BASE_RELOCATION),end))goto invalid;
        IMAGE_BASE_RELOCATION *block=(IMAGE_BASE_RELOCATION*)(image+at);
        if(block->SizeOfBlock<8||(block->SizeOfBlock&1)||!Fits(at,block->SizeOfBlock,end))goto invalid;
        WORD *entries=(WORD*)(block+1);unsigned count=(block->SizeOfBlock-8)/2;
        for(unsigned i=0;i<count;i++){
            WORD type=entries[i]>>12;SIZE_T target=(SIZE_T)block->VirtualAddress+(entries[i]&0xFFF);
            if(type==IMAGE_REL_BASED_ABSOLUTE)continue;
            if(type!=IMAGE_REL_BASED_DIR64||!Fits(target,8,mappedSize))goto invalid;
            uint64_t value;memcpy(&value,image+target,8);value+=delta;memcpy(image+target,&value,8);
        }
        at+=block->SizeOfBlock;
    }
    *imageSize=mappedSize;goto done;
invalid:
    VirtualFree(image,0,MEM_RELEASE);image=NULL;
done:
    if(raw)VirtualFree(raw,0,MEM_RELEASE);CloseHandle(file);return image;
}

int ClientAudit(const wchar_t *path){
    SIZE_T imageSize=0;BYTE *image=MapClientData(path,&imageSize);
    if(!image){fputs("CLIENT_AUDIT_FAILED: invalid/unreadable x64 PE or unsupported relocations\n",stderr);return 1;}
    void *sites[21],*targets[21];uint64_t bindings[2],vtables[RTTI_CLASS_COUNT];
    BOOL valid=VisibilityTestInspect((HMODULE)image,sites,targets,bindings,vtables);
    if(valid){
        printf("{\"status\":\"pass\",\"mode\":\"file discovery only; no game execution or patching\",\"image_size\":\"0x%zX\",\"hooks\":[",imageSize);
        for(unsigned i=0;i<21;i++)printf("%s{\"index\":%u,\"patch_rva\":\"0x%zX\",\"target_rva\":\"0x%zX\"}",i?",":"",i,(SIZE_T)((BYTE*)sites[i]-image),(SIZE_T)((BYTE*)targets[i]-image));
        printf("],\"registry_rva\":\"0x%llX\",\"local_player_ref_rva\":\"0x%llX\",\"vtables\":[",(unsigned long long)(bindings[0]-(UINT_PTR)image),(unsigned long long)(bindings[1]-(UINT_PTR)image));
        for(unsigned i=0;i<RTTI_CLASS_COUNT;i++)printf("%s{\"class\":\"%s\",\"rva\":\"0x%llX\"}",i?",":"",g_rttiNames[i],(unsigned long long)(vtables[i]-(UINT_PTR)image));
        puts("]}");
    }else fputs("CLIENT_AUDIT_FAILED: discovery rejected the supplied executable\n",stderr);
    VirtualFree(image,0,MEM_RELEASE);return valid?0:1;
}
