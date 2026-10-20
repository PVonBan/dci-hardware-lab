cmake_minimum_required(VERSION 3.22)
project(RSP550Lab VERSION 0.1.0 LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
add_subdirectory(${JUCE_PATH} JUCE)
juce_add_console_app(rsplab PRODUCT_NAME "rsplab")
target_sources(rsplab PRIVATE Source/Main.cpp)
target_compile_definitions(rsplab PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)
target_link_libraries(rsplab PRIVATE juce::juce_audio_devices juce::juce_audio_formats
    juce::juce_recommended_config_flags)
