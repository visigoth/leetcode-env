cmake_minimum_required(VERSION 3.14)
project(leetcode LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Fetch GoogleTest
include(FetchContent)
FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG v1.14.0
)
FetchContent_MakeAvailable(googletest)

# Collect all problem source files
file(GLOB PROBLEM_SOURCES "*/*.cpp")

# Build single test binary
add_executable(leetcode_tests ${PROBLEM_SOURCES})
target_link_libraries(leetcode_tests PRIVATE GTest::gtest_main)
target_include_directories(leetcode_tests PRIVATE ${CMAKE_SOURCE_DIR})

include(GoogleTest)
gtest_discover_tests(leetcode_tests)
