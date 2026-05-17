#pragma once
#include "DiamondModel.h"
#include <QOpenGLWidget>
#include <QOpenGLFunctions>
#include <QMatrix4x4>
#include <QVector3D>
#include <QMouseEvent>
#include <QWheelEvent>
#include <memory>

class Viewport3D : public QOpenGLWidget, protected QOpenGLFunctions {
    Q_OBJECT

public:
    explicit Viewport3D(QWidget* parent = nullptr);
    ~Viewport3D() override;

    void setModel(const DiamondModel* model);
    void resetCamera();

protected:
    void initializeGL() override;
    void resizeGL(int w, int h) override;
    void paintGL() override;

    void mousePressEvent(QMouseEvent* e) override;
    void mouseMoveEvent(QMouseEvent* e) override;
    void mouseReleaseEvent(QMouseEvent* e) override;
    void wheelEvent(QWheelEvent* e) override;

private:
    void drawAxes();
    void drawGrid();
    void drawDiamondMesh(const DiamondSolution& sol, float r, float g, float b, float alpha);
    void drawMarkingPoints(const std::vector<Vec3>& pts);
    void drawCuttingPlanes(const std::vector<CuttingPlane>& planes);
    void drawVertex(const Vec3& v);
    void drawWireSphere(float radius, int slices, int stacks);

    QMatrix4x4 projectionMatrix() const;
    QMatrix4x4 viewMatrix() const;

    const DiamondModel* m_model = nullptr;

    // Camera state
    float m_yaw   = 30.0f;
    float m_pitch = 20.0f;
    float m_zoom  = 8.0f;
    QPoint m_lastMousePos;
    bool   m_dragging = false;

    // Colors for multiple solutions
    static constexpr float SOLUTION_COLORS[][3] = {
        {0.4f, 0.7f, 1.0f},   // Blue - Diam 1
        {1.0f, 0.6f, 0.2f},   // Orange - Diam 2
        {0.4f, 1.0f, 0.4f},   // Green - Diam 3
        {1.0f, 0.4f, 0.4f},   // Red - Diam 4
    };
};
