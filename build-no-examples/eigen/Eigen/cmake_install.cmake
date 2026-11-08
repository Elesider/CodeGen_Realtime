# Install script for directory: /workspaces/CodeGen_Realtime/eigen/Eigen

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
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/eigen3/Eigen" TYPE FILE FILES
    "/workspaces/CodeGen_Realtime/eigen/Eigen/Cholesky"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/CholmodSupport"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/Core"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/Dense"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/Eigen"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/Eigenvalues"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/Geometry"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/Householder"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/IterativeLinearSolvers"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/Jacobi"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/KLUSupport"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/LU"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/MetisSupport"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/OrderingMethods"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/PaStiXSupport"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/PardisoSupport"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/QR"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/QtAlignedMalloc"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/SPQRSupport"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/SVD"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/Sparse"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/SparseCholesky"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/SparseCore"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/SparseLU"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/SparseQR"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/StdDeque"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/StdList"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/StdVector"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/SuperLUSupport"
    "/workspaces/CodeGen_Realtime/eigen/Eigen/UmfPackSupport"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Devel" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/eigen3/Eigen" TYPE DIRECTORY FILES "/workspaces/CodeGen_Realtime/eigen/Eigen/src" FILES_MATCHING REGEX "/[^/]*\\.h$")
endif()

