#include "parser.h"
#include "solver.h"
#include "utils.h"
#include <fstream>
#include <unordered_map>

void solve_op(const std::string &spFile, const std::string &slnFile) {
  SpiceParser parser(spFile);
  parser.run();
  auto ckt = parser.circuit();

  // for (int i = 0, ie = ckt->graph.nodeNum(); i < ie; ++i) {
  //   auto name = ckt->nodeNameMap[ckt->graph.nodeFromId(i)];
  //   std::cout << "node " << i << " " << name << "\n";
  // }
  // for (GraphT::ArcIt a(ckt->graph); a != lemon::INVALID; ++a) {
  //   auto [type, value] = ckt->arcCompMap[a];
  //   auto name = ckt->arcCompNameMap[a];
  //   std::cout << name << " " << (int)type << " " << value << "\n";
  // }

  OperatingPointSolver solver(parser.circuit());
  solver.run();
  auto sln = solver.solution();

  // write solution file
  std::ofstream fout(slnFile);
  ASSERT(fout.is_open(), "open file `%s` failed", slnFile.c_str());
  for (GraphT::NodeIt n(ckt->graph); n != lemon::INVALID; ++n) {
    auto name = ckt->nodeNameMap[n];
    auto voltage = sln->nodeVoltageMap[n];
    if (name == "0")
      name = "G";
    fout << name << " " << voltage << "\n";
  }
}

void compare(const std::string &slnFile, const std::string &refFile) {
  std::ifstream fSln(slnFile);
  std::ifstream fRef(refFile);
  ASSERT(fSln.is_open(), "open file `%s` failed", slnFile.c_str());
  ASSERT(fRef.is_open(), "open file `%s` failed", refFile.c_str());

  std::unordered_map<std::string, double> slnMap, refMap;
  std::string name;
  double value;
  while (fSln >> name >> value) {
    slnMap.emplace(name, value);
  }
  while (fRef >> name >> value) {
    refMap.emplace(name, value);
  }

  double maxError = 0;
  double avgError = 0;
  std::string maxErrorName;
  for (const auto &[refName, refVale] : refMap) {
    if (slnMap.find(refName) == slnMap.end()) {
      LOG_INFO("solution missing the value of `%s`", refName.c_str());
      continue;
    }
    if (std::abs(refMap[refName] - slnMap[refName])) {
      maxError = std::abs(refMap[refName] - slnMap[refName]);
      maxErrorName = refName;
    }
    avgError += std::abs(refMap[refName] - slnMap[refName]);
  }
  LOG_INFO("max error: %f in node %s", maxError, maxErrorName.c_str());
  LOG_INFO("average error: %f", maxError / refMap.size());
}

int main(int argc, char *argv[]) {
  std::string spFile = "./test/test1.spice";
  std::string slnFile = "./test/test1.solution";
  std::string refFile;
  if (argc > 2) {
    spFile = argv[1];
    slnFile = argv[2];
  }
  if (argc > 3) {
    refFile = argv[3];
  }

  solve_op(spFile, slnFile);
  if (!refFile.empty()) {
    compare(slnFile, refFile);
  }

  return 0;
}
