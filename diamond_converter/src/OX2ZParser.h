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

    // Geometry extraction constants (discovered through analysis)
    static constexpr uint32_t ENTRY4_VERTEX_OFFSET = 96;    // bytes from entry4 start
    static constexpr uint32_t ENTRY4_VERTEX_END    = 50568; // bytes from entry4 start
    static constexpr uint32_t ENTRY4_VERTEX_STRIDE = 24;    // bytes per vertex record
    static constexpr uint32_t ENTRY4_XYZ_OFFSET    = 4;     // XYZ position within stride
    static constexpr uint32_t ENTRY4_FACE_OFFSET   = 50568; // face index block offset
    static constexpr uint32_t ENTRY4_FACE_SIZE     = 80;    // face index block size
    static constexpr uint32_t ENTRY4_FACE_STRIDE   = 16;    // (v0, v1, v2, n) each 4 bytes
    static constexpr float    COORD_VALID_MAX       = 25.0f; // max valid coordinate (mm)
};
