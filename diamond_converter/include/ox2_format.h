#pragma once
#include <cstdint>
#include <array>

// OX2Z2020 format structures - OctoNus Oxygen 2020 diamond planning software

#pragma pack(push, 1)

// Inner .ox2 file header (8 bytes magic + version info)
struct OX2Header {
    char     magic[8];       // "OX2Z2020"
    uint32_t entryCount;     // Total number of directory entries
    uint32_t reserved[5];    // Padding to 32 bytes
};

// Directory entry (64 bytes each, starts at file offset 0x40)
struct OX2DirEntry {
    uint32_t dataOffset;     // Absolute byte offset to data block
    uint32_t entryId;        // Sequential entry ID (1-based)
    uint32_t field3;         // Usually 0
    uint32_t dataSize;       // Size of data block in bytes
    uint8_t  typeGuid[16];   // Block type GUID
    uint8_t  padding[32];    // Zero padding
};

// V2 block header (common prefix for most data blocks)
struct V2BlockHeader {
    char     tag[2];         // "V2"
    uint16_t blockType;      // Block type identifier
    uint32_t contentSize;    // Size of content
    uint32_t count;          // Item count or sub-field
    uint32_t flags;          // Additional flags
};

// exd1 sub-block directory (within V2 blocks of type 0x0100)
struct Exd1Header {
    char     tag[4];         // "exd1"
    uint32_t subBlockCount;  // Number of sub-blocks
};

struct Exd1SubBlock {
    uint32_t type;           // Sub-block type
    uint32_t flags;
    uint32_t constRef;       // Reference/pointer (often 50568)
    uint32_t dataOffset;     // Offset to data (relative to parent entry)
    uint32_t dataSize;       // Size of data in bytes
};

// XRayAuto block data layout
// - V2 header (16 bytes)
// - "exd1" tag at offset 28
// - Name string at offset 160 (e.g., "XRayAuto-1")
// - Grade string at offset 174 (e.g., "VVS1", "SI1")

#pragma pack(pop)

// Known block type GUIDs
static const uint8_t GUID_FILE_INDEX[16]   = {0x82,0x69,0x35,0x1c,0x6c,0x05,0x20,0x4b,0xb4,0x19,0x0e,0x04,0x03,0x05,0x16,0x8e};
static const uint8_t GUID_MODEL_META[16]   = {0x93,0x36,0x53,0xaa,0x52,0xad,0x45,0x4d,0xb5,0x91,0x35,0x83,0xb3,0x27,0x4b,0xfa};
static const uint8_t GUID_ROUGH_STONE[16]  = {0xde,0x17,0x6a,0x16,0x2d,0x70,0xd5,0x4a,0xb4,0xe4,0x7e,0x3f,0x94,0xff,0xfb,0xb3};
static const uint8_t GUID_POLISHED[16]     = {0xc2,0x43,0x3f,0x6b,0x96,0x19,0x2e,0x4a,0x9d,0xec,0x59,0x8f,0x05,0x33,0x43,0x11};
static const uint8_t GUID_CUT_PLANES[16]  = {0xf0,0x6e,0x16,0xcb,0x99,0x6a,0xf3,0x45,0x97,0xa6,0xde,0x4a,0x9f,0x69,0x31,0x75};
static const uint8_t GUID_XRAY_SLICE[16]  = {0x85,0xa4,0xe6,0xc5,0x58,0xda,0x18,0x4d,0xad,0xbd,0x21,0xc5,0x8e,0xa8,0x8b,0x4f};
