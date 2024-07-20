#include "parser.h"

int main(int argc, char *argv[]) {
  SpiceParser parser("./ibm/dc/ibmpg1.spice");
  parser.run();
  auto ckt = parser.circuit();
  std::cout << "num nodes: " << lemon::countNodes(ckt->graph) << "\n";
  std::cout << "num arcs: " << lemon::countArcs(ckt->graph) << "\n";

  return 0;
}
