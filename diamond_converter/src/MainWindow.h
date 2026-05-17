#pragma once
#include "DiamondModel.h"
#include "OX2ZParser.h"
#include "OBJExporter.h"
#include "Viewport3D.h"

#include <QMainWindow>
#include <QLabel>
#include <QTextEdit>
#include <QProgressBar>
#include <QPushButton>
#include <QTreeWidget>
#include <QSplitter>
#include <QStatusBar>
#include <QDragEnterEvent>
#include <QDropEvent>

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow() override;

protected:
    void dragEnterEvent(QDragEnterEvent* e) override;
    void dropEvent(QDropEvent* e) override;

private slots:
    void onOpenFile();
    void onExportOBJ();
    void onResetView();
    void onAbout();

private:
    void setupUI();
    void setupMenuBar();
    void loadFile(const QString& path);
    void updateInfoPanel();
    void setStatus(const QString& msg);

    // UI components
    Viewport3D*  m_viewport    = nullptr;
    QTextEdit*   m_infoText    = nullptr;
    QTreeWidget* m_structTree  = nullptr;
    QProgressBar* m_progress   = nullptr;
    QPushButton* m_exportBtn   = nullptr;
    QPushButton* m_openBtn     = nullptr;
    QLabel*      m_fileLabel   = nullptr;

    // Data
    DiamondModel  m_model;
    OX2ZParser    m_parser;
    OBJExporter   m_exporter;
    QString       m_currentFile;
    bool          m_fileLoaded = false;
};
