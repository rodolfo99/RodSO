/* RodSO tiny x86_64 UEFI boot manager: GNU/Clang built PE/COFF application.
 * Loads Linux EFI stub from the same boot volume and passes its initrd path.
 * SPDX-License-Identifier: MIT
 */
typedef unsigned char UINT8;
typedef unsigned short UINT16;
typedef unsigned int UINT32;
typedef unsigned long long UINT64;
typedef unsigned long long UINTN;
typedef unsigned long long EFI_STATUS;
typedef void *EFI_HANDLE;
typedef UINT16 CHAR16;
#define EFIAPI __attribute__((ms_abi))
#define EFI_ERROR(x) ((x) & (1ULL << 63))
typedef struct { UINT32 Data1; UINT16 Data2, Data3; UINT8 Data4[8]; } EFI_GUID;
typedef struct { UINT64 Signature; UINT32 Revision, HeaderSize, CRC32, Reserved; } EFI_TABLE_HEADER;
typedef struct EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL;
struct EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL {
    void *Reset;
    EFI_STATUS(EFIAPI *OutputString)(EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL*, const CHAR16*);
};
typedef struct {
    EFI_TABLE_HEADER Hdr;
    void *RaiseTPL, *RestoreTPL, *AllocatePages, *FreePages, *GetMemoryMap;
    EFI_STATUS(EFIAPI *AllocatePool)(UINT32, UINTN, void**);
    void *FreePool, *CreateEvent, *SetTimer, *WaitForEvent, *SignalEvent;
    void *CloseEvent, *CheckEvent, *InstallProtocolInterface, *ReinstallProtocolInterface;
    void *UninstallProtocolInterface;
    EFI_STATUS(EFIAPI *HandleProtocol)(EFI_HANDLE, EFI_GUID*, void**);
    void *Reserved, *RegisterProtocolNotify, *LocateHandle, *LocateDevicePath;
    void *InstallConfigurationTable;
    EFI_STATUS(EFIAPI *LoadImage)(UINT8, EFI_HANDLE, void*, void*, UINTN, EFI_HANDLE*);
    EFI_STATUS(EFIAPI *StartImage)(EFI_HANDLE, UINTN*, CHAR16**);
} EFI_BOOT_SERVICES;
typedef struct {
    EFI_TABLE_HEADER Hdr;
    CHAR16 *FirmwareVendor;
    UINT32 FirmwareRevision;
    UINT32 Padding;
    EFI_HANDLE ConsoleInHandle;
    void *ConIn;
    EFI_HANDLE ConsoleOutHandle;
    EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *ConOut;
    EFI_HANDLE StandardErrorHandle;
    EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *StdErr;
    void *RuntimeServices;
    EFI_BOOT_SERVICES *BootServices;
} EFI_SYSTEM_TABLE;
typedef struct {
    UINT32 Revision;
    UINT32 Padding;
    EFI_HANDLE ParentHandle;
    EFI_SYSTEM_TABLE *SystemTable;
    EFI_HANDLE DeviceHandle;
    void *FilePath;
    void *Reserved;
    UINT32 LoadOptionsSize;
    UINT32 Padding2;
    void *LoadOptions;
    void *ImageBase;
    UINT64 ImageSize;
    UINT32 ImageCodeType, ImageDataType;
    void *Unload;
} EFI_LOADED_IMAGE_PROTOCOL;
typedef struct { UINT8 Type, SubType; UINT16 Length; } EFI_DEVICE_PATH;
static EFI_GUID loaded_image_guid={0x5b1b31a1,0x9562,0x11d2,{0x8e,0x3f,0x00,0xa0,0xc9,0x69,0x72,0x3b}};
static EFI_GUID device_path_guid ={0x09576e91,0x6d3f,0x11d2,{0x8e,0x39,0x00,0xa0,0xc9,0x69,0x72,0x3b}};
static const CHAR16 kernel_name[] = {'\\','E','F','I','\\','B','O','O','T','\\','V','M','L','I','N','U','Z',0};
static const CHAR16 kernel_cmdline[] = {
 'r','d','i','n','i','t','=','/','i','n','i','t',' ',
 'i','n','i','t','r','d','=','\\','E','F','I','\\','B','O','O','T','\\','I','N','I','T','R','D','.','I','M','G',' ',
 'c','o','n','s','o','l','e','=','t','t','y','0',' ',
 'l','o','g','l','e','v','e','l','=','3',0
};
static const CHAR16 hello[] = {'R','o','d','S','O',' ','-',' ','I','n','i','c','i','a','n','d','o',' ','L','i','n','u','x','.','.','.','\r','\n',0};
static const CHAR16 no_loaded[] = {'E','r','r','o','r',':',' ','L','o','a','d','e','d','I','m','a','g','e','\r','\n',0};
static const CHAR16 no_path[] = {'E','r','r','o','r',':',' ','d','i','s','p','o','s','i','t','i','v','o',' ','E','F','I','\r','\n',0};
static const CHAR16 no_kernel[] = {'E','r','r','o','r',':',' ','V','M','L','I','N','U','Z',' ','n','o',' ','e','n','c','o','n','t','r','a','d','o','\r','\n',0};
static const CHAR16 no_start[] = {'E','r','r','o','r',':',' ','L','i','n','u','x',' ','n','o',' ','a','r','r','a','n','c','o','\r','\n',0};
static void copy_bytes(UINT8 *dest, const UINT8 *src, UINTN len) { for(UINTN i=0;i<len;++i) dest[i]=src[i]; }
static void show(EFI_SYSTEM_TABLE *st, const CHAR16 *s) { if(st->ConOut && st->ConOut->OutputString) st->ConOut->OutputString(st->ConOut,s); }
EFI_STATUS EFIAPI EfiMain(EFI_HANDLE ImageHandle, EFI_SYSTEM_TABLE *st);
static void * volatile efi_relocation_anchor = (void*)&EfiMain;
EFI_STATUS EFIAPI EfiMain(EFI_HANDLE ImageHandle, EFI_SYSTEM_TABLE *st) {
    (void)efi_relocation_anchor;
    EFI_BOOT_SERVICES *bs=st->BootServices;
    EFI_LOADED_IMAGE_PROTOCOL *current=0,*linux_image=0;
    EFI_DEVICE_PATH *base=0;
    EFI_HANDLE linux_handle=0;
    EFI_STATUS status;
    show(st,hello);
    status=bs->HandleProtocol(ImageHandle,&loaded_image_guid,(void**)&current);
    if(EFI_ERROR(status)||!current){show(st,no_loaded);return status;}
    status=bs->HandleProtocol(current->DeviceHandle,&device_path_guid,(void**)&base);
    if(EFI_ERROR(status)||!base){show(st,no_path);return status;}
    UINTN base_len=0;
    for(UINTN n=0;n<128;n++) {
        EFI_DEVICE_PATH *node=(EFI_DEVICE_PATH*)((UINT8*)base+base_len);
        if(node->Type==0x7f && node->SubType==0xff) break;
        if(node->Length<4 || node->Length>2048) return 2;
        base_len+=node->Length;
        if(base_len>4096) return 2;
    }
    UINTN name_size=sizeof(kernel_name);
    UINTN file_node_size=4+name_size;
    UINTN total=base_len+file_node_size+4;
    UINT8 *path=0;
    status=bs->AllocatePool(2,total,(void**)&path);
    if(EFI_ERROR(status)||!path){show(st,no_path);return status;}
    copy_bytes(path,(UINT8*)base,base_len);
    path[base_len]=4; path[base_len+1]=4;
    path[base_len+2]=(UINT8)file_node_size;
    path[base_len+3]=(UINT8)(file_node_size>>8);
    copy_bytes(path+base_len+4,(const UINT8*)kernel_name,name_size);
    UINTN end_offset=base_len+file_node_size;
    path[end_offset]=0x7f; path[end_offset+1]=0xff; path[end_offset+2]=4; path[end_offset+3]=0;
    status=bs->LoadImage(0,ImageHandle,path,0,0,&linux_handle);
    if(EFI_ERROR(status)||!linux_handle){show(st,no_kernel);return status;}
    status=bs->HandleProtocol(linux_handle,&loaded_image_guid,(void**)&linux_image);
    if(EFI_ERROR(status)||!linux_image){show(st,no_loaded);return status;}
    linux_image->LoadOptions=(void*)kernel_cmdline;
    linux_image->LoadOptionsSize=(UINT32)sizeof(kernel_cmdline);
    status=bs->StartImage(linux_handle,0,0);
    show(st,no_start);
    return status;
}
