#include "OBJExporter.h"
#include <fstream>
#include <sstream>
#include <filesystem>
#include <iomanip>
#include <set>

namespace fs = std::filesystem;

bool OBJExporter::exportToOBJ(const DiamondModel& model, const std::string& outputDir,
                               const std::string& baseName) {
    fs::create_directories(outputDir);

    bool anySuccess = false;

    // Export each polished solution
    for (size_t i = 0; i < model.solutions.size(); ++i) {
        const auto& sol = model.solutions[i];
        if (sol.vertices.empty() && sol.faces.empty()) continue;

        std::string safeName = sol.name;
        for (char& c : safeName) if (c == ' ' || c == '/') c = '_';

        std::string filePath = outputDir + "/" + baseName + "_" + safeName + ".obj";
        if (writeOBJ(sol, filePath, sol.name))
            anySuccess = true;
    }

    // Export cutting/marking points
    if (!model.markingPoints.empty() || !model.cuttingPlanes.empty()) {
        std::string markFile = outputDir + "/" + baseName + "_marking_points.obj";
        if (writeMarkingPoints(model.markingPoints, model.cuttingPlanes, markFile))
            anySuccess = true;
    }

    // Write info text file
    std::string infoFile = outputDir + "/" + baseName + "_info.txt";
    writeInfoFile(model, infoFile);

    if (!anySuccess && !model.markingPoints.empty()) anySuccess = true;

    if (!anySuccess) {
        m_lastError = "No geometry data could be exported. "
                      "Rough stone geometry is encrypted by OctoNus software.";
        return false;
    }
    return true;
}

bool OBJExporter::writeOBJ(const DiamondSolution& solution, const std::string& filePath,
                             const std::string& name) {
    std::ofstream out(filePath);
    if (!out.is_open()) {
        m_lastError = "Cannot write to: " + filePath;
        return false;
    }

    out << "# Diamond Converter - OX2Z to OBJ\n";
    out << "# Stone: " << name << "\n";
    out << "# Vertices: " << solution.vertices.size() << "\n";
    out << "# Faces: " << solution.faces.size() << "\n\n";
    out << "o " << name << "\n\n";

    out << std::fixed << std::setprecision(6);

    // Write vertices
    for (const auto& v : solution.vertices)
        out << "v " << v.x << " " << v.y << " " << v.z << "\n";

    out << "\n";

    // Write faces (1-indexed for OBJ)
    for (const auto& f : solution.faces) {
        if (f.v0 < solution.vertices.size() &&
            f.v1 < solution.vertices.size() &&
            f.v2 < solution.vertices.size()) {
            out << "f " << (f.v0 + 1) << " " << (f.v1 + 1) << " " << (f.v2 + 1) << "\n";
        }
    }

    out.close();
    return true;
}

bool OBJExporter::writeMarkingPoints(const std::vector<Vec3>& points,
                                      const std::vector<CuttingPlane>& planes,
                                      const std::string& filePath) {
    if (points.empty() && planes.empty()) return false;

    std::ofstream out(filePath);
    if (!out.is_open()) return false;

    out << "# Diamond Converter - Marking / Cutting Plane Points\n";
    out << "# These are boundary points for the cutting planes\n\n";
    out << "o MarkingPoints\n\n";

    out << std::fixed << std::setprecision(6);

    for (const auto& p : points)
        out << "v " << p.x << " " << p.y << " " << p.z << "\n";

    // Write cutting plane boundary as line segments
    if (!planes.empty()) {
        out << "\n# Cutting plane boundaries\n";
        int vOffset = 1;
        for (size_t pi = 0; pi < planes.size(); ++pi) {
            const auto& plane = planes[pi];
            out << "# Plane " << (pi + 1) << " (normal: "
                << plane.normal.x << ", " << plane.normal.y << ", " << plane.normal.z << ")\n";
            for (const auto& bp : plane.boundaryPoints)
                out << "v " << bp.x << " " << bp.y << " " << bp.z << "\n";
            vOffset += plane.boundaryPoints.size();
        }
    }

    // Connect marking points as a line loop (approximate outline)
    if (points.size() >= 2) {
        out << "\n# Marking point outline\nl";
        for (size_t i = 1; i <= points.size(); ++i) out << " " << i;
        out << " 1\n";  // close the loop
    }

    out.close();
    return true;
}

bool OBJExporter::writeInfoFile(const DiamondModel& model, const std::string& filePath) {
    std::ofstream out(filePath);
    if (!out.is_open()) return false;

    out << "Diamond Model Information\n";
    out << "=========================\n\n";
    out << "Source file:   " << model.sourceFile << "\n";
    out << "Model name:    " << model.modelName << "\n";
    out << "Cut type:      " << model.cutType << "\n";
    out << "Marking out:   " << model.markingOut << "\n\n";

    out << "Polished Solutions:\n";
    for (const auto& sol : model.solutions) {
        out << "  - " << sol.name
            << " (" << sol.vertices.size() << " vertices, "
            << sol.faces.size() << " faces)\n";
    }

    out << "\nX-Ray Scan Data:\n";
    out << "  Slices: " << model.xraySlices.size() << "\n";
    out << "  Clarity grades found: ";
    for (size_t i = 0; i < model.clarityGrades.size(); ++i) {
        if (i > 0) out << ", ";
        out << model.clarityGrades[i];
    }
    out << "\n\n";

    out << "Marking Points: " << model.markingPoints.size() << "\n";
    out << "Cutting Planes: " << model.cuttingPlanes.size() << "\n\n";

    out << "Note: " << model.roughStoneNote << "\n";

    out.close();
    return true;
}
