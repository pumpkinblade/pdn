#include "IbmpgParser.hpp"
#include "PowerGrid.hpp"
#include <CLI/CLI.hpp>

int main(int argc, char *argv[]) {
  CLI::App app;
  std::string netlist_file;
  app.add_option("-i,--input", netlist_file, "ibmpg spice netlist")->required();
  CLI11_PARSE(app, argc, argv);

  IbmpgParser parser(netlist_file);
  PowerGridDesc desc;
  parser.extractPowerGrid(desc);
  PowerGrid grid(desc);
  grid.report();
  return 0;
}
