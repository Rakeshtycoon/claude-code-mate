#include "MainWindow.h"

#include <QApplication>
#include <QMenuBar>
#include <QToolBar>
#include <QDockWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFileDialog>
#include <QMessageBox>
#include <QMimeData>
#include <QUrl>
#include <QFileInfo>
#include <QThread>
#include <QSplitter>
#include <QGroupBox>
#include <QTreeWidgetItem>
#include <QHeaderView>
#include <QFontDatabase>
#include <QFont>

MainWindow::MainWindow(QWidget* parent) : QMainWindow(parent) {
    setWindowTitle("Diamond Converter - OX2Z to OBJ");
    setMinimumSize(1100, 700);
    setAcceptDrops(true);

    setupUI();
    setupMenuBar();
    setStatus("Ready. Open an OX2Z or OX2 file to begin.");
}

MainWindow::~MainWindow() = default;

void MainWindow::setupUI() {
    // Central widget with horizontal splitter
    auto* central = new QWidget(this);
    auto* mainLayout = new QVBoxLayout(central);
    mainLayout->setContentsMargins(4, 4, 4, 4);
    mainLayout->setSpacing(4);

    // Top toolbar row
    auto* topRow = new QHBoxLayout();
    m_openBtn = new QPushButton("📂 Open OX2Z File", this);
    m_openBtn->setFixedHeight(36);
    m_openBtn->setStyleSheet("font-size:13px; padding: 0 16px; background:#2d6a4f; color:white; border-radius:4px;");
    connect(m_openBtn, &QPushButton::clicked, this, &MainWindow::onOpenFile);

    m_fileLabel = new QLabel("No file loaded", this);
    m_fileLabel->setStyleSheet("color: #aaa; font-style: italic;");

    m_exportBtn = new QPushButton("💾 Export to OBJ", this);
    m_exportBtn->setFixedHeight(36);
    m_exportBtn->setEnabled(false);
    m_exportBtn->setStyleSheet("font-size:13px; padding: 0 16px; background:#1a6b8a; color:white; border-radius:4px;");
    connect(m_exportBtn, &QPushButton::clicked, this, &MainWindow::onExportOBJ);

    auto* resetBtn = new QPushButton("🔄 Reset View", this);
    resetBtn->setFixedHeight(36);
    resetBtn->setStyleSheet("font-size:12px; padding: 0 12px; background:#444; color:white; border-radius:4px;");
    connect(resetBtn, &QPushButton::clicked, this, &MainWindow::onResetView);

    topRow->addWidget(m_openBtn);
    topRow->addWidget(m_fileLabel, 1);
    topRow->addWidget(resetBtn);
    topRow->addWidget(m_exportBtn);
    mainLayout->addLayout(topRow);

    // Progress bar
    m_progress = new QProgressBar(this);
    m_progress->setFixedHeight(4);
    m_progress->setRange(0, 100);
    m_progress->setValue(0);
    m_progress->setTextVisible(false);
    m_progress->setStyleSheet("QProgressBar { background:#222; border:none; }"
                               "QProgressBar::chunk { background:#2d6a4f; }");
    mainLayout->addWidget(m_progress);

    // Main splitter: viewport + info panel
    auto* splitter = new QSplitter(Qt::Horizontal, this);

    // 3D Viewport
    m_viewport = new Viewport3D(this);
    m_viewport->setStyleSheet("border: 1px solid #333;");
    splitter->addWidget(m_viewport);

    // Right panel: info + structure tree
    auto* rightPanel = new QWidget(this);
    auto* rightLayout = new QVBoxLayout(rightPanel);
    rightLayout->setContentsMargins(2, 0, 2, 0);
    rightLayout->setSpacing(4);

    // File info
    auto* infoGroup = new QGroupBox("Diamond Model Info", rightPanel);
    auto* infoLayout = new QVBoxLayout(infoGroup);
    m_infoText = new QTextEdit(infoGroup);
    m_infoText->setReadOnly(true);
    m_infoText->setMaximumHeight(180);
    m_infoText->setStyleSheet("background:#1a1a2a; color:#ddd; font-family:monospace; font-size:11px; border:none;");
    m_infoText->setPlainText("Open a file to see diamond information...");
    infoLayout->addWidget(m_infoText);
    rightLayout->addWidget(infoGroup);

    // Structure tree
    auto* structGroup = new QGroupBox("File Structure (314 blocks)", rightPanel);
    auto* structLayout = new QVBoxLayout(structGroup);
    m_structTree = new QTreeWidget(structGroup);
    m_structTree->setHeaderLabels({"Block", "Type", "Size", "Info"});
    m_structTree->header()->setSectionResizeMode(QHeaderView::ResizeToContents);
    m_structTree->setStyleSheet("background:#1a1a2a; color:#ddd; font-size:11px;");
    structLayout->addWidget(m_structTree);
    rightLayout->addWidget(structGroup, 1);

    rightPanel->setFixedWidth(380);
    splitter->addWidget(rightPanel);
    splitter->setStretchFactor(0, 3);
    splitter->setStretchFactor(1, 1);

    mainLayout->addWidget(splitter, 1);

    // Status bar
    auto* statusBar = new QStatusBar(this);
    setStatusBar(statusBar);

    setCentralWidget(central);
    setStyleSheet("QMainWindow { background: #1a1a2a; } "
                  "QGroupBox { color: #ccc; font-weight: bold; border: 1px solid #444; "
                  "border-radius: 4px; margin-top: 8px; padding-top: 8px; }"
                  "QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #9bf; }");
}

void MainWindow::setupMenuBar() {
    auto* menuBar = this->menuBar();
    menuBar->setStyleSheet("QMenuBar { background:#111; color:#ddd; } "
                           "QMenuBar::item:selected { background:#333; }");

    auto* fileMenu = menuBar->addMenu("&File");
    fileMenu->setStyleSheet("QMenu { background:#222; color:#ddd; } "
                            "QMenu::item:selected { background:#444; }");
    fileMenu->addAction("&Open OX2Z...", this, &MainWindow::onOpenFile, QKeySequence::Open);
    fileMenu->addSeparator();
    auto* exportAction = fileMenu->addAction("&Export to OBJ...", this, &MainWindow::onExportOBJ, QKeySequence("Ctrl+E"));
    connect(this, &MainWindow::destroyed, exportAction, []{});
    fileMenu->addSeparator();
    fileMenu->addAction("E&xit", qApp, &QApplication::quit, QKeySequence::Quit);

    auto* viewMenu = menuBar->addMenu("&View");
    viewMenu->addAction("&Reset Camera", this, &MainWindow::onResetView, QKeySequence("R"));

    auto* helpMenu = menuBar->addMenu("&Help");
    helpMenu->addAction("&About", this, &MainWindow::onAbout);
}

void MainWindow::onOpenFile() {
    QString path = QFileDialog::getOpenFileName(
        this, "Open Diamond Planning File", "",
        "Diamond Files (*.ox2z *.ox2);;All Files (*)");
    if (!path.isEmpty()) loadFile(path);
}

void MainWindow::loadFile(const QString& path) {
    setStatus("Loading: " + path);
    m_progress->setValue(0);
    m_fileLabel->setText(QFileInfo(path).fileName());

    m_model = DiamondModel{};

    bool ok = m_parser.parse(path.toStdString(), m_model,
        [this](int pct, const std::string& msg) {
            m_progress->setValue(pct);
            setStatus(QString::fromStdString(msg));
            QApplication::processEvents();
        });

    if (!ok) {
        QMessageBox::critical(this, "Error",
            "Failed to parse file:\n" + QString::fromStdString(m_parser.lastError()));
        setStatus("Error: " + QString::fromStdString(m_parser.lastError()));
        m_progress->setValue(0);
        return;
    }

    m_currentFile = path;
    m_fileLoaded = true;
    m_exportBtn->setEnabled(true);

    m_viewport->setModel(&m_model);
    updateInfoPanel();

    setStatus("Loaded successfully: " + QFileInfo(path).fileName());
    m_progress->setValue(100);
}

void MainWindow::updateInfoPanel() {
    // Info text
    QString info;
    info += QString("Model:      %1\n").arg(QString::fromStdString(m_model.modelName));
    info += QString("Cut Type:   %1\n").arg(QString::fromStdString(m_model.cutType));
    info += QString("Marking:    %1\n\n").arg(QString::fromStdString(m_model.markingOut));

    info += QString("Solutions:  %1\n").arg(m_model.solutions.size());
    for (const auto& sol : m_model.solutions) {
        QString meta;
        if (sol.weightCt > 0.0f)
            meta += QString("  %1ct").arg(sol.weightCt, 0, 'f', 2);
        if (sol.priceUsd > 0.0f)
            meta += QString("  $%1").arg(sol.priceUsd, 0, 'f', 2);
        if (!sol.clarity.empty())
            meta += QString("  %1").arg(QString::fromStdString(sol.clarity));
        if (sol.labelId > 0)
            meta += QString("  [ID %1]").arg(sol.labelId);
        info += QString("  ▸ %1%2  (%3 verts, %4 faces)\n")
                .arg(QString::fromStdString(sol.name))
                .arg(meta)
                .arg(sol.vertices.size())
                .arg(sol.faces.size());
    }

    info += QString("\nCutting Planes: %1\n").arg(m_model.cuttingPlanes.size());
    info += QString("Marking Points: %1\n\n").arg(m_model.markingPoints.size());

    info += QString("X-Ray Slices: %1\n").arg(m_model.xraySlices.size());
    info += "Clarity Grades: ";
    for (size_t i = 0; i < m_model.clarityGrades.size(); ++i) {
        if (i > 0) info += ", ";
        info += QString::fromStdString(m_model.clarityGrades[i]);
    }
    info += "\n\n";

    if (!m_model.roughStoneAvailable) {
        info += "⚠ Rough stone geometry:\n  ENCRYPTED by OctoNus\n  (cannot convert to OBJ)";
    }

    m_infoText->setPlainText(info);

    // Structure tree
    m_structTree->clear();

    auto addItem = [this](QTreeWidgetItem* parent, const QString& name, const QString& type,
                          const QString& size, const QString& detail) {
        auto* item = parent ? new QTreeWidgetItem(parent) : new QTreeWidgetItem(m_structTree);
        item->setText(0, name);
        item->setText(1, type);
        item->setText(2, size);
        item->setText(3, detail);
        return item;
    };

    addItem(nullptr, "Header", "OX2Z2020", "-", "Magic + entry count");

    auto* metaItem = addItem(nullptr, "Entry 2", "Model Metadata", "1,444 B",
                             QString::fromStdString(m_model.modelName));
    for (const auto& sol : m_model.solutions)
        addItem(metaItem, QString::fromStdString(sol.name), "Solution", "-", "");

    addItem(nullptr, "Entry 3", "Rough Stone", "439,429 B", "⚠ ENCRYPTED");

    // Solution records (from solution record blocks)
    bool hasSolRec = false;
    for (const auto& sol : m_model.solutions)
        if (sol.labelId > 0) { hasSolRec = true; break; }

    if (hasSolRec) {
        auto* solRecItem = addItem(nullptr, "Solution Records", "GUID_SOLUTION_REC",
                                   QString("%1 records").arg(m_model.solutions.size()), "");
        for (const auto& sol : m_model.solutions) {
            QString detail;
            if (sol.weightCt > 0) detail += QString("%1ct ").arg(sol.weightCt, 0, 'f', 2);
            if (sol.priceUsd > 0) detail += QString("$%1 ").arg(sol.priceUsd, 0, 'f', 0);
            if (!sol.clarity.empty()) detail += QString::fromStdString(sol.clarity);
            addItem(solRecItem, QString::fromStdString(sol.name.empty() ?
                    "ID " + std::to_string(sol.labelId) : sol.name),
                    "Solution", "-", detail);
        }
    } else {
        auto* solItem = addItem(nullptr, "Polished Stone", "GUID_POLISHED",
                                QString("%1 solutions").arg(m_model.solutions.size()), "");
        for (const auto& sol : m_model.solutions) {
            addItem(solItem, QString::fromStdString(sol.name), "Geometry",
                    QString("%1v %2f").arg(sol.vertices.size()).arg(sol.faces.size()), "");
        }
    }

    if (!m_model.cuttingPlanes.empty() || !m_model.markingPoints.empty())
        addItem(nullptr, "Cutting Planes", "GUID_CUT_PLANES", "-",
                QString("%1 marking pts").arg(m_model.markingPoints.size()));

    auto* xrayItem = addItem(nullptr, "X-Ray Slices", "GUID_XRAY_SLICE",
                             QString("%1 slices").arg(m_model.xraySlices.size()), "");

    // Show all xray slices (usually ≤ 5)
    for (const auto& xr : m_model.xraySlices) {
        QString detail = QString::fromStdString(xr.clarityGrade);
        if (xr.jpegSize > 0)
            detail += QString("  JPEG %1 KB").arg(xr.jpegSize / 1024);
        addItem(xrayItem, QString::fromStdString(xr.name.empty() ?
                "Slice " + std::to_string(xr.entryId) : xr.name),
                "XRay", "-", detail);
    }

    m_structTree->expandAll();
}

void MainWindow::onExportOBJ() {
    if (!m_fileLoaded) return;

    QString dir = QFileDialog::getExistingDirectory(this, "Select Output Directory");
    if (dir.isEmpty()) return;

    QString baseName = QFileInfo(m_currentFile).baseName();
    bool ok = m_exporter.exportToOBJ(m_model, dir.toStdString(), baseName.toStdString());

    if (ok) {
        QMessageBox::information(this, "Export Complete",
            QString("Files saved to:\n%1\n\n"
                    "Exported files:\n"
                    "• %2_Diam_1.obj (polished stone mesh)\n"
                    "• %2_marking_points.obj (cutting planes)\n"
                    "• %2_info.txt (diamond information)\n\n"
                    "Note: Rough stone geometry is encrypted and\ncannot be exported.")
            .arg(dir).arg(baseName));
        setStatus("Export complete: " + dir);
    } else {
        QMessageBox::warning(this, "Export Warning",
            "Limited data exported.\n\n" +
            QString::fromStdString(m_exporter.lastError()));
    }
}

void MainWindow::onResetView() {
    if (m_viewport) m_viewport->resetCamera();
}

void MainWindow::onAbout() {
    QMessageBox::about(this, "About Diamond Converter",
        "<b>Diamond Converter v1.0</b><br>"
        "OX2Z / OX2 Diamond Planning File Converter<br><br>"
        "Converts OctoNus Oxygen diamond planning files<br>"
        "to OBJ 3D format.<br><br>"
        "<b>Supported input:</b> .ox2z, .ox2<br>"
        "<b>Output:</b> .obj (Wavefront OBJ)<br><br>"
        "<b>Limitation:</b> Rough stone geometry is<br>"
        "encrypted by OctoNus Oxygen software<br>"
        "and cannot be decrypted.<br><br>"
        "Only polished solution geometry and<br>"
        "cutting plane data can be extracted.");
}

void MainWindow::setStatus(const QString& msg) {
    statusBar()->showMessage(msg);
}

void MainWindow::dragEnterEvent(QDragEnterEvent* e) {
    if (e->mimeData()->hasUrls()) {
        for (const auto& url : e->mimeData()->urls()) {
            QString path = url.toLocalFile().toLower();
            if (path.endsWith(".ox2z") || path.endsWith(".ox2")) {
                e->acceptProposedAction();
                return;
            }
        }
    }
}

void MainWindow::dropEvent(QDropEvent* e) {
    for (const auto& url : e->mimeData()->urls()) {
        QString path = url.toLocalFile();
        if (!path.isEmpty()) {
            loadFile(path);
            break;
        }
    }
}
