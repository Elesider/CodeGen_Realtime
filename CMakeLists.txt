cmake_minimum_required(VERSION 3.24)

project(SolverCodegen)

add_subdirectory(eigen)

file(GLOB SolverCodegen_SOURCE
    "src/exprpar/*.cpp"
    "src/codegen/*.cpp"
    "src/codegen/components/*.cpp"
    "src/codegen/netlist/*.cpp"
    "src/codegen/netlist/producers/*.cpp"
    "src/codegen/udc/*.cpp"
)

add_executable(SolverCodegen exe/codegen_cli_main.cpp)
target_sources(SolverCodegen PRIVATE ${SolverCodegen_SOURCE})
target_link_libraries(SolverCodegen PRIVATE eigen)
target_include_directories(SolverCodegen PRIVATE include/)
target_compile_features(SolverCodegen PRIVATE cxx_std_14)

# Keep these small code-generation regressions independent of Eigen's BUILD_TESTING.
option(SOLVERCODEGEN_BUILD_TESTS "Enable SolverCodegen regression tests" ON)
if(SOLVERCODEGEN_BUILD_TESTS)
    enable_testing()
    find_package(Python3 3.7 COMPONENTS Interpreter QUIET)
    if(Python3_Interpreter_FOUND)
        add_test(
            NAME bridge_converter_2leg_e2e
            COMMAND "${Python3_EXECUTABLE}"
                "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_bridge_converter_2leg.py"
                --codegen "$<TARGET_FILE:SolverCodegen>"
                --cxx "${CMAKE_CXX_COMPILER}"
                --work-dir "${CMAKE_CURRENT_BINARY_DIR}/tests/bridge_converter_2leg"
        )
        set_tests_properties(bridge_converter_2leg_e2e PROPERTIES TIMEOUT 90)
    else()
        message(WARNING "Python 3 was not found; SolverCodegen regression tests are unavailable")
    endif()
endif()
