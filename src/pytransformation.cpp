// This file is part of slideio project.
// It is subject to the license terms in the LICENSE file found in the top-level directory
// of this distribution and at http://slideio.com/license.html.
#include "pyscene.hpp"
#include "pytransformation.hpp"
#include "pyerror.hpp"
#include "slideio/transformer/transformer.hpp"
#include "slideio/transformer/transformations.hpp"
#include "slideio/transformer/transformationwrapper.hpp"


namespace py = pybind11;

using namespace slideio;

std::shared_ptr<PyScene> pyTransformScene(std::shared_ptr<PyScene>& pyScene, const pybind11::list& source)
{
    std::list<std::shared_ptr<TransformationWrapper>> transformations;
    for (const auto& obj : source) {
        if (!py::isinstance<TransformationWrapper>(obj)) {
            RAISE_PYERROR << "Invalid transformation object received in the transformation list";
        }
        const TransformationWrapper& transformation = py::cast<TransformationWrapper&>(obj);
        auto ptr = makeTransformationCopy(transformation);
        transformations.push_back(ptr);
    }
    if (transformations.empty()) {
        RAISE_PYERROR << "Empty transformation list received.";
    }
    std::shared_ptr<slideio::Scene> scene = extractScene(pyScene);
    std::shared_ptr<Scene> transformScene = slideio::transformSceneEx(scene, transformations);
    std::shared_ptr<PyScene> wrapper(new PyScene(transformScene, nullptr));
    return wrapper;
}
