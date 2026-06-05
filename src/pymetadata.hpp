// This file is part of slideio project.
// It is subject to the license terms in the LICENSE file found in the top-level directory
// of this distribution and at http://slideio.com/license.html.
#pragma once
#include <pybind11/pybind11.h>
#include "slideio/core/metadata.hpp"

pybind11::object metadataToPyObject(const slideio::Metadata& metadata);
