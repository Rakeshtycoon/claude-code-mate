#pragma once
#include <string>
#include <vector>
#include <array>
#include <cstdint>

struct Vec3 {
    float x, y, z;
};

struct Triangle {
    uint32_t v0, v1, v2;
};

struct XRaySlice {
    std::string name;
    std::string clarityGrade;
    uint32_t    entryId;
};

struct DiamondSolution {
    std::string name;       // "Diam 1", "Diam 2", etc.
    std::vector<Vec3>     vertices;
    std::vector<Triangle> faces;
};

struct CuttingPlane {
    Vec3  normal;           // Plane normal vector
    float distance;         // Plane distance from origin
    std::vector<Vec3> boundaryPoints;
};

struct DiamondModel {
    // Metadata
    std::string modelName;  // "Model 1"
    std::string cutType;    // "OP01"
    std::string markingOut; // "Marking-outMP05"
    std::string sourceFile;

    // Polished solutions (Diam 1, Diam 2, etc.)
    std::vector<DiamondSolution> solutions;

    // Cutting planes (from Entry 5)
    std::vector<CuttingPlane>   cuttingPlanes;
    std::vector<Vec3>           markingPoints;

    // X-ray scan data
    std::vector<XRaySlice>      xraySlices;
    std::vector<std::string>    clarityGrades; // unique grades found

    // Rough stone geometry availability
    bool roughStoneAvailable = false;   // always false (encrypted)
    std::string roughStoneNote = "Rough stone geometry is encrypted by OctoNus Oxygen software. "
                                 "Only polished solution data can be extracted.";

    bool hasGeometry() const {
        for (const auto& sol : solutions)
            if (!sol.vertices.empty()) return true;
        return !markingPoints.empty();
    }
};
