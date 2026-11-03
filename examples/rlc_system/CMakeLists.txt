cmake_minimum_required(VERSION 3.24)
project(RLCExample LANGUAGES CXX)
add_executable(simulate_rlc main.cpp)
target_compile_features(simulate_rlc PRIVATE cxx_std_17)
if(MINGW)
    target_link_options(simulate_rlc PRIVATE -static)
endif()
add_custom_command(TARGET simulate_rlc POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${CMAKE_CURRENT_SOURCE_DIR}/plot.py" "$<TARGET_FILE_DIR:simulate_rlc>/plot.py")
