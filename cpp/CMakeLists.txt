cmake_minimum_required(VERSION 3.14)
project(leetcode LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Debug build: no optimization, symbols, AddressSanitizer
set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g -fsanitize=address -fno-omit-frame-pointer")
set(CMAKE_EXE_LINKER_FLAGS_DEBUG "-fsanitize=address")

# RelWithDebInfo: optimized with symbols for profiling (CMake built-in, recognized by dependencies)
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g -DNDEBUG -fno-omit-frame-pointer")
set(CMAKE_EXE_LINKER_FLAGS_RELWITHDEBINFO "")

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

# Benchmark support
FetchContent_Declare(
    benchmark
    GIT_REPOSITORY https://github.com/google/benchmark.git
    GIT_TAG v1.8.3
)
set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(benchmark)

# Each bench/*.cpp becomes its own benchmark binary
file(GLOB BENCHMARK_SOURCES CONFIGURE_DEPENDS "${CMAKE_SOURCE_DIR}/bench/[0-9]*.cpp")
foreach(BENCH_SRC ${BENCHMARK_SOURCES})
    get_filename_component(BENCH_NAME ${BENCH_SRC} NAME_WE)
    add_executable(bench_${BENCH_NAME} ${BENCH_SRC})
    target_link_libraries(bench_${BENCH_NAME} PRIVATE benchmark::benchmark)
    target_include_directories(bench_${BENCH_NAME} PRIVATE ${CMAKE_SOURCE_DIR})
endforeach()
