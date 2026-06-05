// This file is part of slideio project.
// It is subject to the license terms in the LICENSE file found in the top-level directory
// of this distribution and at http://slideio.com/license.html.
#include "pymetadata.hpp"

namespace py = pybind11;

py::object metadataToPyObject(const slideio::Metadata& metadata)
{
    switch (metadata.type()) {
    case slideio::Metadata::Type::Bool:
        return py::bool_(metadata.asBool());
    case slideio::Metadata::Type::Int:
        return py::int_(metadata.asInt());
    case slideio::Metadata::Type::Double:
        return py::float_(metadata.asDouble());
    case slideio::Metadata::Type::String:
        return py::str(metadata.asString());
    case slideio::Metadata::Type::Array: {
        py::list list;
        for (size_t index = 0; index < metadata.size(); ++index) {
            list.append(metadataToPyObject(metadata[index]));
        }
        return list;
    }
    case slideio::Metadata::Type::Object: {
        py::dict dict;
        for (const std::string& key : metadata.keys()) {
            dict[py::str(key)] = metadataToPyObject(metadata[key]);
        }
        return dict;
    }
    case slideio::Metadata::Type::Null:
    default:
        return py::none();
    }
}
