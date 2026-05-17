cmake_minimum_required(VERSION 3.16)
project(DiamondConverter VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets OpenGL OpenGLWidgets)

# 7-zip extraction dependency (use system 7z binary)
find_program(SEVENZIP_EXECUTABLE NAMES 7z 7za REQUIRED)
message(STATUS "Found 7-zip: ${SEVENZIP_EXECUTABLE}")

add_executable(DiamondConverter
    src/main.cpp
    src/MainWindow.cpp
    src/MainWindow.h
    src/OX2ZParser.cpp
    src/OX2ZParser.h
    src/DiamondModel.cpp
    src/DiamondModel.h
    src/OBJExporter.cpp
    src/OBJExporter.h
    src/Viewport3D.cpp
    src/Viewport3D.h
    resources/resources.qrc
)

target_link_libraries(DiamondConverter PRIVATE
    Qt6::Core
    Qt6::Widgets
    Qt6::OpenGL
    Qt6::OpenGLWidgets
)

target_compile_definitions(DiamondConverter PRIVATE
    SEVENZIP_PATH="${SEVENZIP_EXECUTABLE}"
)

install(TARGETS DiamondConverter DESTINATION bin)
