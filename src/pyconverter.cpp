// This file is part of slideio project.
// It is subject to the license terms in the LICENSE file found in the top-level directory
// of this distribution and at http://slideio.com/license.html.
#include "pyscene.hpp"
#include "pyconverter.hpp"
#include "pyerror.hpp"
#include "slideio/converter/converter.hpp"
#include "slideio/converter/converterparameters.hpp"
#include <exception>
#include <functional>

namespace py = pybind11;

using namespace slideio;
using namespace slideio::converter;

ConverterParameters* pyCreateConverterParameters(ImageFormat format, Compression encoding)
{
    ConverterParameters* params(nullptr);
    if (format == ImageFormat::SVS) {
        if (encoding == Compression::Jpeg) {
            params = new SVSJpegConverterParameters;
        }
        else if (encoding == Compression::Jpeg2000) {
            params = new SVSJp2KConverterParameters;
        }
        else {
            RAISE_PYERROR << "Unknown encoding for SVS m_format: " << (int)encoding;
        }
    }
    else {
        RAISE_PYERROR << "Unknown m_format: " << (int)format;
    }
    return params;
}

void pyConvertFile(std::shared_ptr<PyScene>& pyScene, ConverterParameters* parameters, const std::string& filePath)
{
    std::shared_ptr<slideio::Scene> scene = extractScene(pyScene);
    slideio::converter::convertScene(scene, *parameters, filePath, parameters->getTileBatchSize());
}

void pyConvertFileEx(std::shared_ptr<PyScene>& pyScene, ConverterParameters* parameters, const std::string& filePath, py::function callback)
{
    std::shared_ptr<slideio::Scene> scene = extractScene(pyScene);

    // Holds a Python error raised inside the user callback so it can be
    // re-raised cleanly after convertScene returns. Letting it propagate as a
    // C++ exception through the (C) conversion pipeline crashes the process.
    std::exception_ptr callbackError;

    std::function<void(int)> cb = [&callback, &callbackError](int progress) {
        // convertScene may invoke this from a worker thread, so acquire the
        // GIL before touching the Python callable. Holding the GIL here also
        // serializes access to callbackError across concurrent invocations.
        py::gil_scoped_acquire gil;
        if (callbackError) {
            // A prior invocation already failed; stop calling into Python.
            return;
        }
        try {
            callback(progress);
        }
        catch (...) {
            callbackError = std::current_exception();
        }
    };

    {
        // Release the GIL around the conversion so callbacks fired from worker
        // threads can acquire it (otherwise gil_scoped_acquire would deadlock).
        py::gil_scoped_release release;
        slideio::converter::convertScene(scene, *parameters, filePath, parameters->getTileBatchSize(), cb);
    }

    if (callbackError) {
        std::rethrow_exception(callbackError);
    }
}
