#pragma once
#include "DiamondModel.h"
#include <string>
#include <vector>
#include <cstdint>
#include <cstring>
#include <functional>

class OX2ZParser {
public:
    using ProgressCallback = std::function<void(int percent, const std::string& status)>;

    OX2ZParser();

    // Parse .ox2z file, returns populated model on success
    bool parse(const std::string& filePath, DiamondModel& model, ProgressCallback progress = nullptr);

    const std::string& lastError() const { return m_lastError; }

private:
    // Step 1: Extract inner .ox2 from 7-zip archive
    bool extractOX2Z(const std::string& ox2zPath, std::string& extractedPath);

    // Step 2: Parse .ox2 inner file
    bool parseOX2(const std::string& ox2Path, DiamondModel& model, ProgressCallback& progress);

    // Directory parsing
    struct DirEntry {
        uint32_t offset;
        uint32_t id;
        uint32_t size;
        uint8_t  guid[16];
    };
    bool readDirectory(const std::vector<uint8_t>& fileData, std::vector<DirEntry>& entries);

    // Block parsers
    void parseModelMeta(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size,
                        DiamondModel& model);
    void parsePolishedStone(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size,
                            DiamondModel& model);
    void parseCutPlanes(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size,
                        DiamondModel& model);
    void parseXRaySlice(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size,
                        uint32_t entryId, DiamondModel& model);
    // New: V2 solution record block (GUID_SOLUTION_REC) with MA02/DS03 sub-structures
    void parseSolutionRecord(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size,
                             DiamondModel& model);

    // CT07 contour reconstruction
    void parseCT07Contours(const std::vector<uint8_t>& data, const std::vector<DirEntry>& entries,
                           DiamondModel& model, ProgressCallback& progress);
    std::vector<Vec3> decodeCT07NibblePath(const std::vector<uint8_t>& data, uint32_t offset,
                                           uint32_t size);
    void buildMeshFromProfile(const std::vector<Vec3>& profile2D, DiamondSolution& sol,
                              int nSlices = 72);
    // Generate parametric round brilliant in normalized space (R=normRadius, z in [-normPavDepth, +normCrownH])
    void buildRoundBrilliantMesh(float normRadius, float normCrownH, float normPavDepth,
                                  DiamondSolution& sol);

    // Geometry helpers
    std::vector<Triangle> readFaceIndices(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size);
    std::vector<Vec3>     readVertices(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size);
    std::vector<Vec3>     extractValidCoords(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size);

    // Utility
    std::string extractString(const std::vector<uint8_t>& data, uint32_t offset, uint32_t maxLen = 64);
    bool        guidEquals(const uint8_t* a, const uint8_t* b);

    template<typename T>
    T readLE(const std::vector<uint8_t>& data, uint32_t offset) const {
        T val = 0;
        for (size_t i = 0; i < sizeof(T); ++i)
            val |= static_cast<T>(data[offset + i]) << (8 * i);
        return val;
    }

    float readFloat(const std::vector<uint8_t>& data, uint32_t offset) const {
        uint32_t raw = readLE<uint32_t>(data, offset);
        float val;
        memcpy(&val, &raw, sizeof(float));
        return val;
    }

    std::string m_lastError;
    std::string m_tempDir;

    // Geometry extraction constants (binary-analysed from real .ox2 file)
    // Vertices are 64-bit doubles, 3 per record, stride 24 bytes
    static constexpr uint32_t ENTRY4_VERTEX_OFFSET = 96;     // bytes from entry4 start
    static constexpr uint32_t ENTRY4_VERTEX_END    = 50568;  // bytes from entry4 start (2103 verts)
    static constexpr uint32_t ENTRY4_VERTEX_STRIDE = 24;     // bytes per vertex (3 doubles)
    static constexpr uint32_t ENTRY4_XYZ_OFFSET    = 0;      // doubles start at byte 0 of stride
    // Diam 1 face block: [v0,v1,v2,group] each uint32, stride 16, 1804 triangles
    static constexpr uint32_t ENTRY4_FACE_OFFSET   = 72360;  // 0x011aa8 from entry4 start
    static constexpr uint32_t ENTRY4_FACE_SIZE     = 28864;  // 1804 * 16 bytes
    static constexpr uint32_t ENTRY4_FACE_STRIDE   = 16;     // v0,v1,v2 + group_id
    // Diam 2: shares vertex array, different face block at 0x01e030
    static constexpr uint32_t ENTRY4_D2_VERTEX_OFFSET = 50664;  // 0xC5E8, 904 verts
    static constexpr uint32_t ENTRY4_D2_VERTEX_END    = 72360;  // 0x011aa8
    static constexpr uint32_t ENTRY4_D2_FACE_OFFSET   = 122928; // 0x01e030
    static constexpr uint32_t ENTRY4_D2_FACE_SIZE     = 28864;  // 1804 * 16 bytes
    static constexpr float    COORD_VALID_MAX          = 25.0f;  // max coord in mm

    // CT07 block layout constants (byte offsets relative to entry data start)
    static constexpr int CT07_START_X_OFF = 83;   // int16 LE: start pixel x
    static constexpr int CT07_START_Y_OFF = 85;   // int16 LE: start pixel y
    static constexpr int CT07_DATA_START  = 91;   // nibble-encoded direction deltas begin here
};
