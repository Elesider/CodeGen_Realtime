cmake_minimum_required(VERSION 3.24)

project(simulate_pi LANGUAGES CXX)

add_executable(simulate_pi simulate_pi.cpp)
target_compile_features(simulate_pi PRIVATE cxx_std_17)
if(MINGW)
    target_link_options(simulate_pi PRIVATE -static)
endif()

if(MSVC)
    target_compile_options(simulate_pi PRIVATE /utf-8)
endif()

add_custom_command(TARGET simulate_pi POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_SOURCE_DIR}/plot_paper.py"
        "$<TARGET_FILE_DIR:simulate_pi>/plot_paper.py")
