#include "IbmpgCircuit.hpp"
#include <CLI/CLI.hpp>

int main(int argc, char *argv[]) {
  CLI::App app;
  std::string netlist_file;
  app.add_option("-i,--input", netlist_file, "ibmpg spice netlist")->required();
  CLI11_PARSE(app, argc, argv);

  IbmpgCircuit ckt;
  ckt.readNetlist(netlist_file);
  ckt.report();
  return 0;
}
