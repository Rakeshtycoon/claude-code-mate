#pragma once
#include "DiamondModel.h"
#include <string>

class OBJExporter {
public:
    // Export diamond model to OBJ format
    // outputPath: path to output .obj file (without extension)
    // Returns true on success
    bool exportToOBJ(const DiamondModel& model, const std::string& outputDir,
                     const std::string& baseName);

    const std::string& lastError() const { return m_lastError; }

private:
    bool writeOBJ(const DiamondSolution& solution, const std::string& filePath,
                  const std::string& name);
    bool writeMarkingPoints(const std::vector<Vec3>& points,
                            const std::vector<CuttingPlane>& planes,
                            const std::string& filePath);
    bool writeInfoFile(const DiamondModel& model, const std::string& filePath);

    std::string m_lastError;
};
