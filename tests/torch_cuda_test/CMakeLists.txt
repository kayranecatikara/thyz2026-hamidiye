cmake_minimum_required(VERSION 3.18)
project(torch_cuda_test)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT DEFINED Torch_DIR)
  set(Torch_DIR "/usr/local/libtorch/share/cmake/Torch")
endif()
find_package(Torch REQUIRED)

add_executable(torch_cuda_test main.cpp)
target_link_libraries(torch_cuda_test ${TORCH_LIBRARIES})
