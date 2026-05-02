cmake_minimum_required(VERSION 3.20)

project(airunner_launcher VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
foreach(config IN ITEMS Debug Release RelWithDebInfo MinSizeRel)
  string(TOUPPER "${config}" config_uc)
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${config_uc} "${CMAKE_BINARY_DIR}")
endforeach()

add_executable(airunner src/main.cpp)

if(MSVC)
  target_compile_options(airunner PRIVATE /W4 /permissive-)
else()
  target_compile_options(airunner PRIVATE -Wall -Wextra -Wpedantic)
endif()

install(TARGETS airunner RUNTIME DESTINATION bin)
install(
  FILES runtime_manifest.example.env
  DESTINATION share/airunner
)