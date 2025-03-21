// This file is part of slideio project.
// It is subject to the license terms in the LICENSE file found in the top-level directory
// of this distribution and at http://slideio.com/license.html.
#include "pyglobals.hpp"
#include <slideio/slideio/slideio.hpp>
#include "pyerror.hpp"

namespace py = pybind11;

std::shared_ptr<PySlide> pyOpenSlide(const std::string& path, const std::string& driver)
{
    std::shared_ptr<slideio::Slide> slide = slideio::openSlide(path, driver);
    if(!slide)
    {
        RAISE_PYERROR << "Cannot open file \"" << path << "\" with driver \"" << driver << "\"";
    }
    PySlide* pySlide = new PySlide(slide);
    std::shared_ptr<PySlide> wrapper(pySlide);
    return wrapper;
}


std::vector<std::string> pyGetDriverIDs()
{
    return slideio::getDriverIDs();
}

std::string pyGetVersion()
{
    return slideio::getVersion();
}

static slideio::DataType typeFromNumpyType(const pybind11::dtype& type)
{
    if (type.is(py::detail::npy_format_descriptor<uint8_t>::dtype()))
    {
    return slideio::DataType::DT_Byte;
    }
    else if(type.is(py::detail::npy_format_descriptor<int8_t>::dtype()))
    {
        return slideio::DataType::DT_Int8;
    }
    else if(type.is(py::detail::npy_format_descriptor<int16_t>::dtype()))
    {
        return slideio::DataType::DT_Int16;
    }
    else if (type.is(py::detail::npy_format_descriptor<uint16_t>::dtype()))
    {
        return slideio::DataType::DT_UInt16;
    }
    else if (type.is(py::detail::npy_format_descriptor<int32_t>::dtype()))
    {
        return slideio::DataType::DT_Int32;
    }
    else if (type.is(py::detail::npy_format_descriptor<float>::dtype()))
    {
        return slideio::DataType::DT_Float32;
    }
    else if (type.is(py::detail::npy_format_descriptor<double>::dtype()))
    {
        return slideio::DataType::DT_Float64;
    }
    RAISE_PYERROR << "Cannot convert numpy data type to internal type";
}

void pySetLogLevel(const std::string& level)
{
    slideio::setLogLevel(level);
}