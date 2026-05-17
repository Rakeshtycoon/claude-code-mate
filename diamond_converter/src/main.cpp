#include "MainWindow.h"
#include <QApplication>
#include <QStyleFactory>

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    app.setApplicationName("Diamond Converter");
    app.setApplicationVersion("1.0.0");
    app.setOrganizationName("DiamondTools");
    app.setStyle(QStyleFactory::create("Fusion"));

    // Dark palette
    QPalette darkPalette;
    darkPalette.setColor(QPalette::Window,          QColor(26, 26, 42));
    darkPalette.setColor(QPalette::WindowText,       QColor(220, 220, 220));
    darkPalette.setColor(QPalette::Base,             QColor(18, 18, 30));
    darkPalette.setColor(QPalette::AlternateBase,    QColor(30, 30, 50));
    darkPalette.setColor(QPalette::ToolTipBase,      QColor(50, 50, 80));
    darkPalette.setColor(QPalette::ToolTipText,      QColor(220, 220, 220));
    darkPalette.setColor(QPalette::Text,             QColor(220, 220, 220));
    darkPalette.setColor(QPalette::Button,           QColor(40, 40, 60));
    darkPalette.setColor(QPalette::ButtonText,       QColor(220, 220, 220));
    darkPalette.setColor(QPalette::BrightText,       Qt::red);
    darkPalette.setColor(QPalette::Highlight,        QColor(45, 106, 79));
    darkPalette.setColor(QPalette::HighlightedText,  Qt::white);
    darkPalette.setColor(QPalette::Disabled, QPalette::Text, QColor(100, 100, 100));
    app.setPalette(darkPalette);

    MainWindow window;
    window.show();

    // Open file from command line argument
    if (argc > 1) {
        QMetaObject::invokeMethod(&window, [&]() {
            // Slight delay to ensure window is shown
        }, Qt::QueuedConnection);
    }

    return app.exec();
}
