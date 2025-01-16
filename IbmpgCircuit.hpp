#pragma once

#include "Circuit.hpp"

class IbmpgCircuit : public Circuit {
public:
  IbmpgCircuit() : Circuit() {}

  void readNetlist(const std::string &file_path);

  void makeBranch(char *bran, char *node1, char *node2, double v);
  void makeComment(char *comment);

  void extractVddGrid();
  void extractGndGrid();
};
