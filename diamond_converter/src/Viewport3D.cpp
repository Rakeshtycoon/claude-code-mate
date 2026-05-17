#include "Viewport3D.h"
#include <QOpenGLContext>
#include <QPainter>
#include <cmath>

constexpr float PI = 3.14159265358979f;

Viewport3D::Viewport3D(QWidget* parent)
    : QOpenGLWidget(parent) {
    setMinimumSize(400, 300);
}

Viewport3D::~Viewport3D() = default;

void Viewport3D::setModel(const DiamondModel* model) {
    m_model = model;
    resetCamera();
    update();
}

void Viewport3D::resetCamera() {
    m_yaw   = 30.0f;
    m_pitch = 20.0f;
    m_zoom  = 8.0f;
    update();
}

void Viewport3D::initializeGL() {
    initializeOpenGLFunctions();
    glClearColor(0.12f, 0.12f, 0.18f, 1.0f);
    glEnable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glEnable(GL_LINE_SMOOTH);
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST);
}

void Viewport3D::resizeGL(int w, int h) {
    glViewport(0, 0, w, h);
}

void Viewport3D::paintGL() {
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    glMatrixMode(GL_PROJECTION);
    glLoadMatrixf(projectionMatrix().constData());

    glMatrixMode(GL_MODELVIEW);
    glLoadMatrixf(viewMatrix().constData());

    drawAxes();
    drawGrid();

    if (m_model) {
        // Draw polished stone solutions
        int colorIdx = 0;
        for (const auto& sol : m_model->solutions) {
            int ci = colorIdx % 4;
            drawDiamondMesh(sol,
                SOLUTION_COLORS[ci][0], SOLUTION_COLORS[ci][1], SOLUTION_COLORS[ci][2],
                0.6f);
            colorIdx++;
        }

        // Draw marking / cutting plane points
        drawMarkingPoints(m_model->markingPoints);
        drawCuttingPlanes(m_model->cuttingPlanes);

        // If no geometry: show info overlay
        if (!m_model->hasGeometry()) {
            QPainter painter(this);
            painter.setPen(Qt::white);
            painter.setFont(QFont("Arial", 11));
            painter.drawText(rect(), Qt::AlignCenter,
                "No 3D geometry available\n"
                "(Rough stone geometry is encrypted\nby OctoNus Oxygen software)");
            painter.end();
        }
    } else {
        // Empty state
        QPainter painter(this);
        painter.setPen(Qt::gray);
        painter.setFont(QFont("Arial", 13));
        painter.drawText(rect(), Qt::AlignCenter, "Open an OX2Z or OX2 file to view");
        painter.end();
    }
}

void Viewport3D::drawAxes() {
    glLineWidth(2.0f);
    glBegin(GL_LINES);
    // X axis - red
    glColor3f(1.0f, 0.3f, 0.3f);
    glVertex3f(0, 0, 0); glVertex3f(3, 0, 0);
    // Y axis - green
    glColor3f(0.3f, 1.0f, 0.3f);
    glVertex3f(0, 0, 0); glVertex3f(0, 3, 0);
    // Z axis - blue
    glColor3f(0.3f, 0.3f, 1.0f);
    glVertex3f(0, 0, 0); glVertex3f(0, 0, 3);
    glEnd();
}

void Viewport3D::drawGrid() {
    glLineWidth(0.5f);
    glColor4f(0.4f, 0.4f, 0.4f, 0.5f);
    float ext = 5.0f;
    float step = 1.0f;
    glBegin(GL_LINES);
    for (float x = -ext; x <= ext; x += step) {
        glVertex3f(x, 0, -ext); glVertex3f(x, 0, ext);
    }
    for (float z = -ext; z <= ext; z += step) {
        glVertex3f(-ext, 0, z); glVertex3f(ext, 0, z);
    }
    glEnd();
}

void Viewport3D::drawDiamondMesh(const DiamondSolution& sol, float r, float g, float b, float alpha) {
    if (sol.vertices.empty()) return;

    // Draw wireframe faces
    if (!sol.faces.empty()) {
        glLineWidth(1.0f);
        glColor4f(r, g, b, alpha);
        for (const auto& face : sol.faces) {
            if (face.v0 >= sol.vertices.size() ||
                face.v1 >= sol.vertices.size() ||
                face.v2 >= sol.vertices.size()) continue;
            glBegin(GL_LINE_LOOP);
            glVertex3f(sol.vertices[face.v0].x, sol.vertices[face.v0].y, sol.vertices[face.v0].z);
            glVertex3f(sol.vertices[face.v1].x, sol.vertices[face.v1].y, sol.vertices[face.v1].z);
            glVertex3f(sol.vertices[face.v2].x, sol.vertices[face.v2].y, sol.vertices[face.v2].z);
            glEnd();
        }

        // Fill faces with translucent color
        glColor4f(r, g, b, 0.25f);
        glBegin(GL_TRIANGLES);
        for (const auto& face : sol.faces) {
            if (face.v0 >= sol.vertices.size() ||
                face.v1 >= sol.vertices.size() ||
                face.v2 >= sol.vertices.size()) continue;
            glVertex3f(sol.vertices[face.v0].x, sol.vertices[face.v0].y, sol.vertices[face.v0].z);
            glVertex3f(sol.vertices[face.v1].x, sol.vertices[face.v1].y, sol.vertices[face.v1].z);
            glVertex3f(sol.vertices[face.v2].x, sol.vertices[face.v2].y, sol.vertices[face.v2].z);
        }
        glEnd();
    }

    // Draw all vertices as points
    glPointSize(3.0f);
    glColor4f(r, g, b, 1.0f);
    glBegin(GL_POINTS);
    for (const auto& v : sol.vertices) {
        if (std::abs(v.x) < 25 && std::abs(v.y) < 25 && std::abs(v.z) < 25)
            glVertex3f(v.x, v.y, v.z);
    }
    glEnd();
}

void Viewport3D::drawMarkingPoints(const std::vector<Vec3>& pts) {
    if (pts.empty()) return;

    // Draw points
    glPointSize(6.0f);
    glColor4f(1.0f, 1.0f, 0.0f, 1.0f);  // Yellow
    glBegin(GL_POINTS);
    for (const auto& p : pts)
        glVertex3f(p.x, p.y, p.z);
    glEnd();

    // Draw outline loop
    glLineWidth(2.0f);
    glColor4f(1.0f, 0.8f, 0.0f, 0.8f);
    glBegin(GL_LINE_LOOP);
    for (const auto& p : pts)
        glVertex3f(p.x, p.y, p.z);
    glEnd();
}

void Viewport3D::drawCuttingPlanes(const std::vector<CuttingPlane>& planes) {
    for (size_t pi = 0; pi < planes.size(); ++pi) {
        const auto& plane = planes[pi];
        if (plane.boundaryPoints.size() < 3) continue;

        // Draw plane boundary
        glLineWidth(1.5f);
        float hue = static_cast<float>(pi) / std::max(1.0f, static_cast<float>(planes.size()));
        glColor4f(1.0f - hue, 0.5f, hue, 0.8f);

        glBegin(GL_LINE_LOOP);
        for (const auto& bp : plane.boundaryPoints)
            glVertex3f(bp.x, bp.y, bp.z);
        glEnd();

        // Draw normal arrow from centroid
        Vec3 centroid = {0, 0, 0};
        for (const auto& bp : plane.boundaryPoints) {
            centroid.x += bp.x; centroid.y += bp.y; centroid.z += bp.z;
        }
        float n = static_cast<float>(plane.boundaryPoints.size());
        centroid.x /= n; centroid.y /= n; centroid.z /= n;

        glBegin(GL_LINES);
        glVertex3f(centroid.x, centroid.y, centroid.z);
        glVertex3f(centroid.x + plane.normal.x * 0.5f,
                   centroid.y + plane.normal.y * 0.5f,
                   centroid.z + plane.normal.z * 0.5f);
        glEnd();
    }
}

QMatrix4x4 Viewport3D::projectionMatrix() const {
    QMatrix4x4 m;
    float aspect = width() > 0 ? static_cast<float>(width()) / height() : 1.0f;
    m.perspective(45.0f, aspect, 0.1f, 1000.0f);
    return m;
}

QMatrix4x4 Viewport3D::viewMatrix() const {
    QMatrix4x4 m;
    m.translate(0, 0, -m_zoom);
    m.rotate(m_pitch, 1, 0, 0);
    m.rotate(m_yaw,   0, 1, 0);
    return m;
}

void Viewport3D::mousePressEvent(QMouseEvent* e) {
    if (e->button() == Qt::LeftButton || e->button() == Qt::RightButton) {
        m_lastMousePos = e->pos();
        m_dragging = true;
    }
}

void Viewport3D::mouseMoveEvent(QMouseEvent* e) {
    if (!m_dragging) return;
    QPoint delta = e->pos() - m_lastMousePos;
    m_lastMousePos = e->pos();

    if (e->buttons() & Qt::LeftButton) {
        m_yaw   += delta.x() * 0.5f;
        m_pitch += delta.y() * 0.5f;
        m_pitch = std::max(-89.0f, std::min(89.0f, m_pitch));
    }
    update();
}

void Viewport3D::mouseReleaseEvent(QMouseEvent*) {
    m_dragging = false;
}

void Viewport3D::wheelEvent(QWheelEvent* e) {
    m_zoom -= e->angleDelta().y() * 0.01f;
    m_zoom = std::max(1.0f, std::min(50.0f, m_zoom));
    update();
}
