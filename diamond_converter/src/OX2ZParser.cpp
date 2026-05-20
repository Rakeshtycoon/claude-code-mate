#include "OX2ZParser.h"
#include "../include/ox2_format.h"

#include <fstream>
#include <sstream>
#include <cstring>
#include <cmath>
#include <algorithm>
#include <set>
#include <filesystem>
#include <cstdlib>

namespace fs = std::filesystem;

OX2ZParser::OX2ZParser() {
    // Use system temp directory
    m_tempDir = fs::temp_directory_path().string() + "/ox2z_extract_XXXXXX";
}

bool OX2ZParser::parse(const std::string& filePath, DiamondModel& model, ProgressCallback progress) {
    auto prog = [&](int pct, const std::string& msg) {
        if (progress) progress(pct, msg);
    };

    model.sourceFile = filePath;
    prog(0, "Opening file...");

    // Detect format: .ox2z (7-zip) or .ox2 (raw inner file)
    std::string lowerPath = filePath;
    std::transform(lowerPath.begin(), lowerPath.end(), lowerPath.begin(), ::tolower);

    std::string ox2Path;
    bool needsCleanup = false;

    if (lowerPath.size() >= 5 && lowerPath.substr(lowerPath.size() - 5) == ".ox2z") {
        prog(5, "Extracting 7-zip archive...");
        if (!extractOX2Z(filePath, ox2Path)) return false;
        needsCleanup = true;
    } else if (lowerPath.size() >= 4 && lowerPath.substr(lowerPath.size() - 4) == ".ox2") {
        ox2Path = filePath;
    } else {
        m_lastError = "Unsupported file format. Expected .ox2z or .ox2";
        return false;
    }

    prog(15, "Parsing OX2 structure...");
    bool ok = parseOX2(ox2Path, model, progress);

    if (needsCleanup) {
        // Remove extracted temp file
        try { fs::remove(ox2Path); } catch (...) {}
        try { fs::remove(fs::path(ox2Path).parent_path()); } catch (...) {}
    }

    return ok;
}

bool OX2ZParser::extractOX2Z(const std::string& ox2zPath, std::string& extractedPath) {
    // Create unique temp directory
    std::string tmpDir = fs::temp_directory_path().string() + "/ox2z_" +
                         std::to_string(std::hash<std::string>{}(ox2zPath) & 0xFFFF);

    if (!fs::create_directories(tmpDir)) {
        // Directory might already exist, try to use it
    }

    // Build 7z command - properly quoted for Windows paths with spaces
    std::string sevenzip = std::string(SEVENZIP_PATH);
#ifdef _WIN32
    // Windows: outer quotes needed when executable path has spaces; redirect to NUL
    std::string cmd = "\"\"" + sevenzip + "\" e \"" + ox2zPath +
                      "\" -o\"" + tmpDir + "\" -y > NUL 2>&1\"";
#else
    std::string cmd = "\"" + sevenzip + "\" e \"" + ox2zPath +
                      "\" -o\"" + tmpDir + "\" -y > /dev/null 2>&1";
#endif

    int ret = std::system(cmd.c_str());
    if (ret != 0) {
        m_lastError = "Failed to extract archive. Is 7-zip installed?";
        return false;
    }

    // Find the extracted .ox2 file
    for (const auto& entry : fs::directory_iterator(tmpDir)) {
        std::string name = entry.path().string();
        std::string lower = name;
        std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
        if (lower.size() >= 4 && lower.substr(lower.size() - 4) == ".ox2") {
            extractedPath = name;
            return true;
        }
    }

    m_lastError = "No .ox2 file found inside archive";
    return false;
}

bool OX2ZParser::parseOX2(const std::string& ox2Path, DiamondModel& model, ProgressCallback& progress) {
    // Read entire file into memory
    std::ifstream file(ox2Path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        m_lastError = "Cannot open file: " + ox2Path;
        return false;
    }

    size_t fileSize = file.tellg();
    file.seekg(0);
    std::vector<uint8_t> data(fileSize);
    file.read(reinterpret_cast<char*>(data.data()), fileSize);
    file.close();

    // Verify magic
    if (fileSize < sizeof(OX2Header) ||
        strncmp(reinterpret_cast<const char*>(data.data()), "OX2Z2020", 8) != 0) {
        m_lastError = "Not a valid OX2 file (bad magic bytes)";
        return false;
    }

    uint32_t entryCount = readLE<uint32_t>(data, 8);
    if (entryCount == 0 || entryCount > 10000) {
        m_lastError = "Invalid entry count in OX2 header";
        return false;
    }

    if (progress) progress(20, "Reading " + std::to_string(entryCount) + " data blocks...");

    // Read directory
    std::vector<DirEntry> entries;
    if (!readDirectory(data, entries)) return false;

    // Process entries by GUID type
    int processedXRay = 0;
    for (size_t i = 0; i < entries.size(); ++i) {
        const auto& e = entries[i];
        if (e.offset + e.size > fileSize) continue;

        if (guidEquals(e.guid, GUID_MODEL_META)) {
            parseModelMeta(data, e.offset, e.size, model);
            if (progress) progress(25, "Parsed model metadata");

        } else if (guidEquals(e.guid, GUID_ROUGH_STONE)) {
            // Cannot parse - encrypted
            model.roughStoneAvailable = false;
            if (progress) progress(30, "Rough stone geometry: encrypted (skipping)");

        } else if (guidEquals(e.guid, GUID_POLISHED)) {
            parsePolishedStone(data, e.offset, e.size, model);
            if (progress) progress(50, "Parsed polished stone geometry");

        } else if (guidEquals(e.guid, GUID_CUT_PLANES)) {
            parseCutPlanes(data, e.offset, e.size, model);
            if (progress) progress(60, "Parsed cutting planes");

        } else if (guidEquals(e.guid, GUID_XRAY_SLICE)) {
            parseXRaySlice(data, e.offset, e.size, e.id, model);
            processedXRay++;
        }
    }

    if (progress) progress(85, "Processed " + std::to_string(processedXRay) + " X-ray slices");

    // Collect unique clarity grades
    std::set<std::string> grades;
    for (const auto& xr : model.xraySlices)
        if (!xr.clarityGrade.empty()) grades.insert(xr.clarityGrade);
    model.clarityGrades.assign(grades.begin(), grades.end());

    // If model name not found, use filename
    if (model.modelName.empty())
        model.modelName = fs::path(ox2Path).stem().string();

    if (progress) progress(100, "Done");
    return true;
}

bool OX2ZParser::readDirectory(const std::vector<uint8_t>& data, std::vector<DirEntry>& entries) {
    uint32_t entryCount = readLE<uint32_t>(data, 8);
    uint32_t dirStart   = 0x40;  // Directory starts at byte 64
    uint32_t entrySize  = 0x40;  // Each entry is 64 bytes

    entries.clear();
    entries.reserve(entryCount);

    for (uint32_t i = 0; i < entryCount; ++i) {
        uint32_t off = dirStart + i * entrySize;
        if (off + entrySize > data.size()) break;

        DirEntry e;
        e.offset = readLE<uint32_t>(data, off);
        e.id     = readLE<uint32_t>(data, off + 4);
        e.size   = readLE<uint32_t>(data, off + 12);
        memcpy(e.guid, data.data() + off + 16, 16);
        entries.push_back(e);
    }
    return !entries.empty();
}

void OX2ZParser::parseModelMeta(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size,
                                 DiamondModel& model) {
    // Known string offsets within entry 2:
    // @20: model name ("Model 1")
    // @31: cut type ("OP01")
    // @59: marking out type ("Marking-outMP05")
    // @307: "Diam 1"
    // @322: "Diam 2"

    auto readStr = [&](uint32_t relOff) -> std::string {
        if (relOff >= size) return "";
        return extractString(data, offset + relOff);
    };

    model.modelName  = readStr(20);
    model.cutType    = readStr(31);
    model.markingOut = readStr(59);

    // Extract solution names
    for (uint32_t pos : {307u, 322u, 337u, 352u}) {
        std::string name = readStr(pos);
        if (!name.empty() && name.rfind("Diam", 0) == 0) {
            DiamondSolution sol;
            sol.name = name;
            model.solutions.push_back(sol);
        }
    }

    // If no solutions found, add a default one
    if (model.solutions.empty()) {
        DiamondSolution sol;
        sol.name = "Polished Stone";
        model.solutions.push_back(sol);
    }
}

void OX2ZParser::parsePolishedStone(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size,
                                     DiamondModel& model) {
    if (model.solutions.empty()) {
        DiamondSolution sol;
        sol.name = "Polished Stone";
        model.solutions.push_back(sol);
    }

    auto& sol = model.solutions[0];

    // Face index block: at entry4 + ENTRY4_FACE_OFFSET
    // Each face: (v0:uint32, v1:uint32, v2:uint32, n:uint32) = 16 bytes
    uint32_t faceBlockOffset = offset + ENTRY4_FACE_OFFSET;
    uint32_t faceBlockSize   = ENTRY4_FACE_SIZE;
    sol.faces = readFaceIndices(data, faceBlockOffset, faceBlockSize);

    // Vertex data: at entry4 + ENTRY4_VERTEX_OFFSET, stride = ENTRY4_VERTEX_STRIDE
    // XYZ starts at ENTRY4_XYZ_OFFSET within each stride record
    uint32_t vertStart = offset + ENTRY4_VERTEX_OFFSET;
    uint32_t vertEnd   = offset + ENTRY4_VERTEX_END;
    sol.vertices = readVertices(data, vertStart, vertEnd - vertStart);
}

std::vector<Triangle> OX2ZParser::readFaceIndices(const std::vector<uint8_t>& data,
                                                    uint32_t offset, uint32_t size) {
    std::vector<Triangle> faces;
    uint32_t numRecords = size / ENTRY4_FACE_STRIDE;

    for (uint32_t i = 0; i < numRecords; ++i) {
        uint32_t o = offset + i * ENTRY4_FACE_STRIDE;
        if (o + 12 > data.size()) break;

        uint32_t v0 = readLE<uint32_t>(data, o);
        uint32_t v1 = readLE<uint32_t>(data, o + 4);
        uint32_t v2 = readLE<uint32_t>(data, o + 8);
        uint32_t n  = readLE<uint32_t>(data, o + 12);

        // Validate: reasonable vertex indices and n==3 (triangles)
        if (n == 3 && v0 < 100000 && v1 < 100000 && v2 < 100000) {
            faces.push_back({v0, v1, v2});
        }
    }
    return faces;
}

std::vector<Vec3> OX2ZParser::readVertices(const std::vector<uint8_t>& data,
                                            uint32_t offset, uint32_t size) {
    std::vector<Vec3> vertices;

    // Stride=24 bytes per record, XYZ at byte offset 4 within record
    uint32_t numRecords = size / ENTRY4_VERTEX_STRIDE;

    for (uint32_t i = 0; i < numRecords; ++i) {
        uint32_t recordStart = offset + i * ENTRY4_VERTEX_STRIDE + ENTRY4_XYZ_OFFSET;
        if (recordStart + 12 > data.size()) break;

        Vec3 v;
        v.x = readFloat(data, recordStart);
        v.y = readFloat(data, recordStart + 4);
        v.z = readFloat(data, recordStart + 8);

        // Only keep valid coordinates
        if (std::abs(v.x) < COORD_VALID_MAX && std::abs(v.y) < COORD_VALID_MAX &&
            std::abs(v.z) < COORD_VALID_MAX && std::isfinite(v.x) &&
            std::isfinite(v.y) && std::isfinite(v.z)) {
            vertices.push_back(v);
        } else {
            // Insert zero vertex to maintain index alignment
            vertices.push_back({0.0f, 0.0f, 0.0f});
        }
    }
    return vertices;
}

void OX2ZParser::parseCutPlanes(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size,
                                 DiamondModel& model) {
    // Entry 5: V2 header (12 bytes) + 4 planes worth of data
    // Extract all float values in range (-5, 5) as marking boundary points
    model.markingPoints = extractValidCoords(data, offset + 12, size - 12);

    // Try to interpret as cutting planes (NX, NY, NZ, D groups)
    // Groups of 3 consecutive valid floats near the diamond surface
    std::vector<Vec3> pts = model.markingPoints;

    // Group into sets of 3 for approximate plane normals
    for (size_t i = 0; i + 2 < pts.size(); i += 3) {
        if (i + 3 <= pts.size()) {
            CuttingPlane plane;
            plane.normal   = pts[i];
            plane.distance = 0.0f;
            plane.boundaryPoints = {pts[i], pts[i+1], pts[i+2]};
            model.cuttingPlanes.push_back(plane);
        }
    }
}

std::vector<Vec3> OX2ZParser::extractValidCoords(const std::vector<uint8_t>& data,
                                                   uint32_t offset, uint32_t size) {
    std::vector<Vec3> result;
    std::vector<float> validFloats;

    // Collect all float32 values in range (-5, 5) excluding near-zero
    for (uint32_t i = 0; i + 4 <= size; i += 4) {
        float v = readFloat(data, offset + i);
        if (std::isfinite(v) && std::abs(v) < 5.0f && std::abs(v) > 0.0001f) {
            validFloats.push_back(v);
        }
    }

    // Group as XYZ triplets
    for (size_t i = 0; i + 3 <= validFloats.size(); i += 3) {
        result.push_back({validFloats[i], validFloats[i+1], validFloats[i+2]});
    }
    return result;
}

void OX2ZParser::parseXRaySlice(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size,
                                  uint32_t entryId, DiamondModel& model) {
    XRaySlice slice;
    slice.entryId = entryId;

    // Name at offset 160 within the block
    if (offset + 160 < data.size())
        slice.name = extractString(data, offset + 160, 30);

    // Clarity grade at offset 174
    if (offset + 174 < data.size())
        slice.clarityGrade = extractString(data, offset + 174, 10);

    if (!slice.name.empty())
        model.xraySlices.push_back(slice);
}

std::string OX2ZParser::extractString(const std::vector<uint8_t>& data, uint32_t offset, uint32_t maxLen) {
    std::string result;
    for (uint32_t i = 0; i < maxLen && offset + i < data.size(); ++i) {
        uint8_t b = data[offset + i];
        if (b >= 32 && b < 127)
            result += static_cast<char>(b);
        else
            break;
    }
    // Trim trailing spaces
    while (!result.empty() && result.back() == ' ') result.pop_back();
    return result;
}

bool OX2ZParser::guidEquals(const uint8_t* a, const uint8_t* b) {
    return memcmp(a, b, 16) == 0;
}
