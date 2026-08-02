cmake_minimum_required(VERSION 3.22.1)
project("cricketbattingtracker" CXX)

# Force 16 KB page size alignment across custom and JNI native libraries
set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,-z,max-page-size=16384")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,-z,max-page-size=16384")

# Native library target consuming AGP build directory flags
add_library(cricketbattingtracker SHARED dummy.cpp)
