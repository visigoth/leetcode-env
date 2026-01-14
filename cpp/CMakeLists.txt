cmake_minimum_required(VERSION 3.14)
project(leetcode LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Debug build: no optimization, symbols, AddressSanitizer
set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g -fsanitize=address -fno-omit-frame-pointer")
set(CMAKE_EXE_LINKER_FLAGS_DEBUG "-fsanitize=address")

# Fetch GoogleTest
include(FetchContent)
FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG v1.14.0
)
FetchContent_MakeAvailable(googletest)

# Collect wrapper files from root directory only (not recursive)
file(GLOB PROBLEM_SOURCES
    CONFIGURE_DEPENDS
    "${CMAKE_SOURCE_DIR}/[0-9]*.cpp"
)

# Build single test binary
add_executable(leetcode_tests ${PROBLEM_SOURCES})
target_link_libraries(leetcode_tests PRIVATE GTest::gtest_main)
target_include_directories(leetcode_tests PRIVATE ${CMAKE_SOURCE_DIR})

include(GoogleTest)
gtest_discover_tests(leetcode_tests)
