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
    int processedSol  = 0;
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

        } else if (guidEquals(e.guid, GUID_SOLUTION_REC)) {
            parseSolutionRecord(data, e.offset, e.size, model);
            processedSol++;

        } else if (guidEquals(e.guid, GUID_XRAY_SLICE)) {
            parseXRaySlice(data, e.offset, e.size, e.id, model);
            processedXRay++;
        }
    }

    if (progress) progress(85, "Processed " + std::to_string(processedXRay) +
                           " X-ray slices, " + std::to_string(processedSol) + " solution records");

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
    while (model.solutions.size() < 2) {
        DiamondSolution sol;
        sol.name = "Diam " + std::to_string(model.solutions.size() + 1);
        model.solutions.push_back(sol);
    }

    // Diam 1: vertices (double precision) + face block
    auto& sol1 = model.solutions[0];
    sol1.vertices = readVertices(data, offset + ENTRY4_VERTEX_OFFSET,
                                 ENTRY4_VERTEX_END - ENTRY4_VERTEX_OFFSET);
    sol1.faces    = readFaceIndices(data, offset + ENTRY4_FACE_OFFSET, ENTRY4_FACE_SIZE);

    // Diam 2: 904 vertices (subset of Diam1 positions) + separate face block
    auto& sol2 = model.solutions[1];
    sol2.vertices = readVertices(data, offset + ENTRY4_D2_VERTEX_OFFSET,
                                 ENTRY4_D2_VERTEX_END - ENTRY4_D2_VERTEX_OFFSET);
    sol2.faces    = readFaceIndices(data, offset + ENTRY4_D2_FACE_OFFSET, ENTRY4_D2_FACE_SIZE);
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
        // 4th uint32 is a face-group index (0-903), not vertex count — ignore

        if (v0 < 100000 && v1 < 100000 && v2 < 100000) {
            faces.push_back({v0, v1, v2});
        }
    }
    return faces;
}

std::vector<Vec3> OX2ZParser::readVertices(const std::vector<uint8_t>& data,
                                            uint32_t offset, uint32_t size) {
    std::vector<Vec3> vertices;

    // Each vertex: 3 x float64 (double), stride=24, XYZ_OFFSET=0
    uint32_t numRecords = size / ENTRY4_VERTEX_STRIDE;

    for (uint32_t i = 0; i < numRecords; ++i) {
        uint32_t base = offset + i * ENTRY4_VERTEX_STRIDE + ENTRY4_XYZ_OFFSET;
        if (base + 24 > data.size()) break;

        double dx, dy, dz;
        memcpy(&dx, data.data() + base,      8);
        memcpy(&dy, data.data() + base + 8,  8);
        memcpy(&dz, data.data() + base + 16, 8);

        Vec3 v{ (float)dx, (float)dy, (float)dz };

        if (std::abs(v.x) < COORD_VALID_MAX && std::abs(v.y) < COORD_VALID_MAX &&
            std::abs(v.z) < COORD_VALID_MAX && std::isfinite(v.x) &&
            std::isfinite(v.y) && std::isfinite(v.z)) {
            vertices.push_back(v);
        } else {
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

    // Locate embedded JPEG (0xFF 0xD8 0xFF marker); typically at block-relative offset ~670
    static const uint8_t jpegSof[] = {0xFF, 0xD8, 0xFF};
    static const uint8_t jpegEoi[] = {0xFF, 0xD9};
    for (uint32_t j = 0; j + 2 < size; ++j) {
        if (data[offset + j]     == jpegSof[0] &&
            data[offset + j + 1] == jpegSof[1] &&
            data[offset + j + 2] == jpegSof[2]) {
            slice.jpegOffset = offset + j;
            // Find JPEG end
            for (uint32_t k = j + 2; k + 1 < size; ++k) {
                if (data[offset + k] == jpegEoi[0] && data[offset + k + 1] == jpegEoi[1]) {
                    slice.jpegSize = (offset + k + 2) - slice.jpegOffset;
                    break;
                }
            }
            break;
        }
    }

    // Scan the whole block for the inclusion layer name.
    // Format: uint32 nameLen + name_bytes + uint32 gradeLen + grade_bytes
    // e.g. \x0e\x00\x00\x00 + "Curved Crack-1" + \x02\x00\x00\x00 + "I1"
    static const char* clarityTokens[] = {
        "VVS1","VVS2","VS1","VS2","SI1","SI2","I1","I2","I3","IF","FL", nullptr
    };
    for (uint32_t j = 0; j + 8 < size && slice.name.empty(); ++j) {
        uint32_t nameLen = readLE<uint32_t>(data, offset + j);
        if (nameLen < 3 || nameLen > 60 || j + 4 + nameLen + 4 > size) continue;

        // Verify all nameLen bytes are printable ASCII
        bool allPrintable = true;
        for (uint32_t k = 0; k < nameLen; ++k) {
            uint8_t c = data[offset + j + 4 + k];
            if (c < 32 || c >= 127) { allPrintable = false; break; }
        }
        if (!allPrintable) continue;

        // Read grade length immediately after name
        uint32_t gradeStart = j + 4 + nameLen;
        uint32_t gradeLen   = readLE<uint32_t>(data, offset + gradeStart);
        if (gradeLen < 2 || gradeLen > 6 || gradeStart + 4 + gradeLen > size) continue;

        // Check grade bytes against known clarity tokens
        for (int ci = 0; clarityTokens[ci]; ++ci) {
            size_t tlen = strlen(clarityTokens[ci]);
            if (tlen == gradeLen &&
                memcmp(data.data() + offset + gradeStart + 4, clarityTokens[ci], tlen) == 0) {
                slice.name         = extractString(data, offset + j + 4, nameLen);
                slice.clarityGrade = clarityTokens[ci];
                break;
            }
        }
    }

    // Fallback: try legacy fixed offsets if scan found nothing
    if (slice.name.empty() && offset + 160 < data.size())
        slice.name = extractString(data, offset + 160, 30);
    if (slice.clarityGrade.empty() && offset + 174 < data.size())
        slice.clarityGrade = extractString(data, offset + 174, 10);

    model.xraySlices.push_back(slice);
}

void OX2ZParser::parseSolutionRecord(const std::vector<uint8_t>& data, uint32_t offset, uint32_t size,
                                      DiamondModel& model) {
    // Solution record blocks use MA02 and DS03 sub-structures.
    // MA02: "MA02" + uint32 length + text like "66)  B: 0.93 (511.50) B-EX-3: 0.93 (I1)"
    // DS03: "DS03" + uint32 length + text like "0.93 512 Diam 1" + uint32 + "Diam 1"

    DiamondSolution sol;

    // Find MA02 sub-block
    static const uint8_t ma02Tag[] = {'M','A','0','2'};
    for (uint32_t j = 0; j + 8 < size; ++j) {
        if (memcmp(data.data() + offset + j, ma02Tag, 4) == 0) {
            uint32_t textLen = readLE<uint32_t>(data, offset + j + 4);
            if (textLen == 0 || textLen > 512 || j + 8 + textLen > size) break;
            std::string text = extractString(data, offset + j + 8, textLen);
            // Parse: "<id>)  B: <weight> (<price>) <variant>: <w2> (<clarity>)"
            auto parseNum = [](const std::string& s, size_t pos) -> float {
                try { return std::stof(s.substr(pos)); } catch (...) { return 0.0f; }
            };
            // Extract label ID (digits before ')')
            size_t rp = text.find(')');
            if (rp != std::string::npos)
                try { sol.labelId = std::stoi(text.substr(0, rp)); } catch (...) {}
            // Extract weight: after "B: "
            size_t bpos = text.find("B: ");
            if (bpos != std::string::npos) sol.weightCt = parseNum(text, bpos + 3);
            // Extract price: first '(' after weight
            size_t popen = text.find('(', bpos != std::string::npos ? bpos : 0);
            if (popen != std::string::npos) sol.priceUsd = parseNum(text, popen + 1);
            // Extract clarity: second '(' content
            size_t popen2 = text.find('(', popen != std::string::npos ? popen + 1 : 0);
            if (popen2 != std::string::npos) {
                size_t pclose2 = text.find(')', popen2);
                if (pclose2 != std::string::npos)
                    sol.clarity = text.substr(popen2 + 1, pclose2 - popen2 - 1);
            }
            // Extract variant (word before second colon)
            size_t colon2 = text.rfind(':', popen2 != std::string::npos ? popen2 : text.size());
            if (colon2 != std::string::npos) {
                size_t vstart = text.rfind(' ', colon2 - 1);
                if (vstart != std::string::npos)
                    sol.variant = text.substr(vstart + 1, colon2 - vstart - 1);
            }
            break;
        }
    }

    // Find DS03 sub-block to get the solution name ("Diam 1")
    static const uint8_t ds03Tag[] = {'D','S','0','3'};
    for (uint32_t j = 0; j + 8 < size; ++j) {
        if (memcmp(data.data() + offset + j, ds03Tag, 4) == 0) {
            uint32_t textLen = readLE<uint32_t>(data, offset + j + 4);
            if (textLen == 0 || textLen > 256 || j + 8 + textLen > size) break;
            std::string text = extractString(data, offset + j + 8, textLen);
            // Format: "<weight> <price_int> <name>" e.g. "0.93 512 Diam 1"
            // Skip the two numeric tokens, rest is name
            size_t sp1 = text.find(' ');
            if (sp1 != std::string::npos) {
                size_t sp2 = text.find(' ', sp1 + 1);
                if (sp2 != std::string::npos && sp2 + 1 < text.size())
                    sol.name = text.substr(sp2 + 1);
            }
            // Also read the second "Diam 1" string right after the first name
            if (sol.name.empty()) sol.name = text;
            break;
        }
    }

    if (sol.labelId > 0 || !sol.name.empty()) {
        // Merge with existing solution by name, or append
        bool merged = false;
        for (auto& existing : model.solutions) {
            if (!sol.name.empty() && existing.name == sol.name) {
                existing.labelId  = sol.labelId;
                existing.weightCt = sol.weightCt;
                existing.priceUsd = sol.priceUsd;
                existing.clarity  = sol.clarity;
                existing.variant  = sol.variant;
                merged = true;
                break;
            }
        }
        if (!merged)
            model.solutions.push_back(sol);
    }
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
