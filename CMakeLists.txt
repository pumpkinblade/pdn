cmake_minimum_required(VERSION 3.12)

project(pdn)

find_package(LEMON CONFIG REQUIRED)
find_package(Eigen3 CONFIG REQUIRED)

add_executable(${PROJECT_NAME} 
  main.cpp
  parser.cpp
  solver.cpp
  utils.cpp)

target_include_directories(${PROJECT_NAME} PRIVATE ${LEMON_INCLUDE_DIR})
target_link_libraries(${PROJECT_NAME} PRIVATE ${LEMON_LIBRARY})
target_link_libraries(${PROJECT_NAME} PRIVATE Eigen3::Eigen)

