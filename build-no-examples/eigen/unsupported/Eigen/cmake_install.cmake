# Install script for directory: /workspaces/CodeGen_Realtime/eigen/unsupported/Eigen

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/usr/local")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Devel" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/eigen3/unsupported/Eigen" TYPE FILE FILES
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/AdolcForward"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/AlignedVector3"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/ArpackSupport"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/AutoDiff"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/BVH"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/EulerAngles"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/FFT"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/IterativeSolvers"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/KroneckerProduct"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/LevenbergMarquardt"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/MatrixFunctions"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/MoreVectorization"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/MPRealSupport"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/NonLinearOptimization"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/NumericalDiff"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/OpenGLSupport"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/Polynomials"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/Skyline"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/SparseExtra"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/SpecialFunctions"
    "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/Splines"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Devel" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/eigen3/unsupported/Eigen" TYPE DIRECTORY FILES "/workspaces/CodeGen_Realtime/eigen/unsupported/Eigen/src" FILES_MATCHING REGEX "/[^/]*\\.h$")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for each subdirectory.
  include("/workspaces/CodeGen_Realtime/build-no-examples/eigen/unsupported/Eigen/CXX11/cmake_install.cmake")

endif()

