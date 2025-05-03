#include "pyslide.hpp"
#include "pyscene.hpp"

int PySlide::getNumScenes() const
{
    return m_slide->getNumScenes();
}

std::string PySlide::getFilePath() const
{
    return m_slide->getFilePath();
}

std::shared_ptr<PyScene> PySlide::getScene(int index)
{
    std::shared_ptr<slideio::Scene> scene = m_slide->getScene(index);
    std::shared_ptr<PyScene> wrapper(new PyScene(scene, m_slide));
    return wrapper;
}

std::shared_ptr<PyScene> PySlide::getSceneByName(const std::string& sceneName)
{
    std::shared_ptr<slideio::Scene> scene = m_slide->getSceneByName(sceneName);
    std::shared_ptr<PyScene> wrapper(new PyScene(scene, m_slide));
    return wrapper;
}

const std::string& PySlide::getRawMetadata() const
{
    return m_slide->getRawMetadata();
}

slideio::MetadataFormat PySlide::getMetadataFormat() const
{
    return m_slide->getMetadataFormat();
}

std::list<std::string> PySlide::getAuxImageNames() const
{
    return m_slide->getAuxImageNames();
}

int PySlide::getNumAuxImages() const
{
    return m_slide->getNumAuxImages();
}

std::shared_ptr<PyScene> PySlide::getAuxImage(const std::string& imageName)
{
    std::shared_ptr<slideio::Scene> scene = m_slide->getAuxImage(imageName);
    std::shared_ptr<PyScene> wrapper(new PyScene(scene, nullptr));
    return wrapper;
}

std::string PySlide::toString() const {
    return m_slide->toString();
}

