cmake_minimum_required(VERSION 3.12)

project(pdn)

find_package(LEMON CONFIG REQUIRED)
find_package(Eigen3 CONFIG REQUIRED)
find_package(CLI11 CONFIG REQUIRED)
find_package(BISON REQUIRED)
find_package(FLEX REQUIRED)
find_package(fmt REQUIRED)

flex_target(ibmpg_lexer
  ibmpg.l
  ${CMAKE_CURRENT_BINARY_DIR}/ibmpg_lexer.cpp
)

bison_target(ibmpg_parser
  ibmpg.y
  ${CMAKE_CURRENT_BINARY_DIR}/ibmpg_parser.cpp
)

add_executable(pdn 
  main.cpp
  Circuit.cpp
  IbmpgCircuit.cpp
  Branch.cpp
  ${FLEX_ibmpg_lexer_OUTPUTS}
  ${BISON_ibmpg_parser_OUTPUTS}
)

target_include_directories(pdn PRIVATE ${CMAKE_SOURCE_DIR})
target_include_directories(pdn PRIVATE ${LEMON_INCLUDE_DIR})
target_link_libraries(pdn PRIVATE ${LEMON_LIBRARY})
target_link_libraries(pdn PRIVATE Eigen3::Eigen)
target_link_libraries(pdn PRIVATE CLI11::CLI11)
target_link_libraries(pdn PRIVATE fmt::fmt)

