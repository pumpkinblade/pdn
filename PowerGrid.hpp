#pragma once

#include <limits>
#include <vector>

struct LoadCurrentDesc {
  int x, y;
  double current;

  LoadCurrentDesc() : x(0), y(0), current(0) {}
  LoadCurrentDesc(int x, int y, double current)
      : x(x), y(y), current(current) {}
};

struct PowerPadDesc {
  int x, y;
  double resistance;
  PowerPadDesc()
      : x(0), y(0), resistance(std::numeric_limits<double>::infinity()) {}
  PowerPadDesc(int x, int y, double resistance)
      : x(x), y(y), resistance(resistance) {}
};

struct WireDesc {
  int x1, y1;
  int x2, y2;
  double resistance;
  WireDesc()
      : x1(0), y1(0), x2(0), y2(0),
        resistance(std::numeric_limits<double>::infinity()) {}
  WireDesc(int x1, int y1, int x2, int y2, double resistance)
      : x1(x1), y1(y1), x2(x2), y2(y2), resistance(resistance) {}
};

struct GridDesc {
  int start_x, start_y;
  int end_x, end_y;
  int step_x, step_y;
  GridDesc()
      : start_x(0), start_y(0), end_x(0), end_y(0), step_x(1), step_y(1) {}
  GridDesc(int start_x, int start_y, int end_x, int end_y, int step_x,
           int step_y)
      : start_x(start_x), start_y(start_y), end_x(end_x), end_y(end_y),
        step_x(step_x), step_y(step_y) {}
};

struct PowerGridDesc {
  GridDesc grid;
  std::vector<LoadCurrentDesc> loads;
  std::vector<PowerPadDesc> pads;
  std::vector<WireDesc> wires;
};

class PowerGrid {
public:
  PowerGrid(const PowerGridDesc &desc);

  void makePad(int x, int y, double resistance);
  void makeLoad(int x, int y, double current);
  void makeConductance(const std::vector<std::tuple<int, int, double>> &wires,
                       const std::vector<int> &points,
                       std::vector<double> &conds);

  void report() const;

private:
  void makeResistorX(int x1, int x2, int j, double conductance);
  void makeResistorY(int y1, int y2, int i, double conductance);

private:
  std::vector<int> m_points_x;
  std::vector<int> m_points_y;

  // conductance between N[i,j] and N[i+1,j]
  std::vector<std::vector<double>> m_cond_x;
  // conductance between N[i,j] and N[i,j+1]
  std::vector<std::vector<double>> m_cond_y;
  // conductance between N[i,j] and vdd source
  std::vector<std::vector<double>> m_cond_z;
  // load current at N[i,j]
  std::vector<std::vector<double>> m_load;
};
