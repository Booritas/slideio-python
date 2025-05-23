// This file is part of slideio project.
// It is subject to the license terms in the LICENSE file found in the top-level directory
// of this distribution and at http://slideio.com/license.html.
#pragma once
#include "pyslide.hpp"

std::shared_ptr<PySlide> pyOpenSlide(const std::string& path, const std::string& driver);
std::vector<std::string> pyGetDriverIDs();
void pySetLogLevel(const std::string& level);
std::string pyGetVersion();
