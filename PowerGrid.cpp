#include "PowerGrid.hpp"
#include <algorithm>
#include <fmt/core.h>

PowerGrid::PowerGrid(const PowerGridDesc &desc) {
  // init grid
  for (int x = desc.grid.start_x; x < desc.grid.end_x + desc.grid.step_x;
       x += desc.grid.step_x) {
    m_points_x.push_back(std::min(x, desc.grid.end_x));
  }
  for (int y = desc.grid.start_y; y < desc.grid.end_y + desc.grid.step_y;
       y += desc.grid.step_y) {
    m_points_y.push_back(std::min(y, desc.grid.end_y));
  }
  m_cond_x.resize(m_points_x.size(),
                  std::vector<double>(m_points_y.size(), 0.));
  m_cond_y.resize(m_points_x.size(),
                  std::vector<double>(m_points_y.size(), 0.));
  m_cond_z.resize(m_points_x.size(),
                  std::vector<double>(m_points_y.size(), 0.));
  m_load.resize(m_points_x.size(), std::vector<double>(m_points_y.size(), 0.));

  // make load
  for (const auto [x, y, current] : desc.loads) {
    makeLoad(x, y, current);
  }

  // make pad
  for (const auto [x, y, resistance] : desc.pads) {
    makePad(x, y, resistance);
  }

  // partition x wires and y wires
  std::vector<WireDesc> wires(desc.wires);
  auto x_wire_begin = wires.begin();
  auto x_wire_end =
      std::partition(wires.begin(), wires.end(),
                     [](const WireDesc &w) { return w.x1 != w.x2; });
  auto y_wire_begin = x_wire_end;
  auto y_wire_end = wires.end();

  // handle x wires
  std::vector<std::tuple<int, int, double>> x_wires;
  std::vector<double> x_conds;
  for (int j = 0; j < m_points_y.size() - 1; j++) {
    x_wires.clear();
    int ly = m_points_y[j];
    int hy = m_points_y[j + 1];
    for (auto it = x_wire_begin; it != x_wire_end; it++) {
      if (ly <= it->y1 && it->y1 < hy) {
        double conductance = 1. / it->resistance / (hy - ly) * (hy - it->y1);
        x_wires.emplace_back(it->x1, it->x2, conductance);
      }
    }
    makeConductance(x_wires, m_points_x, x_conds);
    for (int i = 0; i < m_points_x.size() - 1; i++) {
      m_cond_x[i][j] = x_conds[i];
    }
  }
  x_wires.clear();
  for (auto it = x_wire_begin; it != x_wire_end; it++) {
    if (it->y1 == m_points_y.back()) {
      double conductance = 1. / it->resistance;
      x_wires.emplace_back(it->x1, it->x2, conductance);
    }
  }
  makeConductance(x_wires, m_points_x, x_conds);
  for (int i = 0; i < m_points_x.size() - 1; i++) {
    m_cond_x[i][m_points_y.size() - 1] = x_conds[i];
  }

  // handle y wires
  std::vector<std::tuple<int, int, double>> y_wires;
  std::vector<double> y_conds;
  for (int i = 0; i < m_points_x.size() - 1; i++) {
    y_wires.clear();
    int lx = m_points_x[i];
    int hx = m_points_x[i + 1];
    for (auto it = y_wire_begin; it != y_wire_end; it++) {
      if (lx <= it->x1 && it->x1 < hx) {
        double conductance = 1. / it->resistance / (hx - lx) * (hx - it->x1);
        y_wires.emplace_back(it->y1, it->y2, conductance);
      }
    }
    makeConductance(y_wires, m_points_y, y_conds);
    for (int j = 0; j < m_points_y.size() - 1; j++) {
      m_cond_y[i][j] = y_conds[j];
    }
  }
  y_wires.clear();
  for (auto it = y_wire_begin; it != y_wire_end; it++) {
    if (it->x1 == m_points_x.back()) {
      double conductance = 1. / it->resistance;
      y_wires.emplace_back(it->y1, it->y2, conductance);
    }
  }
  makeConductance(y_wires, m_points_y, y_conds);
  for (int j = 0; j < m_points_y.size() - 1; j++) {
    m_cond_y[m_points_x.size() - 1][j] = y_conds[j];
  }
}

void PowerGrid::makeConductance(
    const std::vector<std::tuple<int, int, double>> &wires,
    const std::vector<int> &points, std::vector<double> &conds) {
  std::vector<int> ps(points);
  for (const auto &[x1, x2, conductance] : wires) {
    ps.push_back(x1);
    ps.push_back(x2);
  }
  std::sort(ps.begin(), ps.end());
  ps.erase(std::unique(ps.begin(), ps.end()), ps.end());

  std::vector<double> cs(ps.size() - 1);
  for (int i = 0; i < ps.size() - 1; i++) {
    int p1 = ps[i];
    int p2 = ps[i + 1];
    for (const auto &[x1, x2, cond] : wires) {
      if (std::max(x1, p1) < std::min(x2, p2)) {
        cs[i] += cond / (std::min(x2, p2) - std::max(x1, p1)) * (x2 - x1);
      }
    }
  }

  conds.resize(points.size() - 1, 0.);
  for (int j = 0; j < points.size() - 1; j++) {
    int i1 = std::distance(ps.begin(),
                           std::lower_bound(ps.begin(), ps.end(), points[j]));
    int i2 = std::distance(
        ps.begin(), std::lower_bound(ps.begin(), ps.end(), points[j + 1]));
    conds[j] = cs[i1];
    for (int i = i1 + 1; i < i2; i++) {
      conds[j] = conds[j] * cs[i] / (conds[j] + cs[i]);
    }
  }
}

void PowerGrid::makePad(int x, int y, double resistance) {
  double conductance = 1. / resistance;
  int i =
      std::distance(m_points_x.begin(),
                    std::lower_bound(m_points_x.begin(), m_points_x.end(), x));
  int j =
      std::distance(m_points_y.begin(),
                    std::lower_bound(m_points_y.begin(), m_points_y.end(), y));
  if (m_points_x[i] == x && m_points_y[j] == y) {
    m_cond_z[i][j] += conductance;
  } else if (m_points_x[i] == x) {
    double t = (y - m_points_y[j]) /
               static_cast<double>(m_points_y[j + 1] - m_points_y[j]);
    m_cond_z[i][j] += (1 - t) * conductance;
    m_cond_z[i][j + 1] += t * conductance;
  } else if (m_points_y[j] == y) {
    double s = (x - m_points_x[i]) /
               static_cast<double>(m_points_x[i + 1] - m_points_x[i]);
    m_cond_z[i][j] += (1 - s) * conductance;
    m_cond_z[i + 1][j] += s * conductance;
  } else {
    double s = (x - m_points_x[i]) /
               static_cast<double>(m_points_x[i + 1] - m_points_x[i]);
    double t = (y - m_points_y[j]) /
               static_cast<double>(m_points_y[j + 1] - m_points_y[j]);
    m_cond_z[i][j] += (1 - s) * (1 - t) * conductance;
    m_cond_z[i][j + 1] += (1 - s) * t * conductance;
    m_cond_z[i + 1][j] += s * (1 - t) * conductance;
    m_cond_z[i + 1][j + 1] += s * t * conductance;
  }
}

void PowerGrid::makeLoad(int x, int y, double current) {
  int i =
      std::distance(m_points_x.begin(),
                    std::lower_bound(m_points_x.begin(), m_points_x.end(), x));
  int j =
      std::distance(m_points_y.begin(),
                    std::lower_bound(m_points_y.begin(), m_points_y.end(), y));
  if (m_points_x[i] == x && m_points_y[j] == y) {
    m_load[i][j] += current;
  } else if (m_points_x[i] == x) {
    double t = (y - m_points_y[j]) /
               static_cast<double>(m_points_y[j + 1] - m_points_y[j]);
    m_load[i][j] += (1 - t) * current;
    m_load[i][j + 1] += t * current;
  } else if (m_points_y[j] == y) {
    double s = (x - m_points_x[i]) /
               static_cast<double>(m_points_x[i + 1] - m_points_x[i]);
    m_load[i][j] += (1 - s) * current;
    m_load[i + 1][j] += s * current;
  } else {
    double s = (x - m_points_x[i]) /
               static_cast<double>(m_points_x[i + 1] - m_points_x[i]);
    double t = (y - m_points_y[j]) /
               static_cast<double>(m_points_y[j + 1] - m_points_y[j]);
    m_load[i][j] += (1 - s) * (1 - t) * current;
    m_load[i][j + 1] += (1 - s) * t * current;
    m_load[i + 1][j] += s * (1 - t) * current;
    m_load[i + 1][j + 1] += s * t * current;
  }
}

void PowerGrid::report() const {
  fmt::println("load: ");
  for (int j = 0; j < m_points_y.size(); j++) {
    for (int i = 0; i < m_points_x.size(); i++) {
      fmt::print("{:.2f} ", m_load[i][j]);
    }
    fmt::println("");
  }
  fmt::println("cond_z: ");
  for (int j = 0; j < m_points_y.size(); j++) {
    for (int i = 0; i < m_points_x.size(); i++) {
      fmt::print("{:.2f} ", m_cond_z[i][j]);
    }
    fmt::println("");
  }
  fmt::println("cond_x: ");
  for (int j = 0; j < m_points_y.size(); j++) {
    for (int i = 0; i < m_points_x.size(); i++) {
      fmt::print("{:.2f} ", m_cond_x[i][j]);
    }
    fmt::println("");
  }
  fmt::println("cond_y: ");
  for (int j = 0; j < m_points_y.size(); j++) {
    for (int i = 0; i < m_points_x.size(); i++) {
      fmt::print("{:.2f} ", m_cond_y[i][j]);
    }
    fmt::println("");
  }
}
