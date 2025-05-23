﻿// This file is part of slideio project.
// It is subject to the license terms in the LICENSE file found in the top-level directory
// of this distribution and at http://slideio.com/license.html.
#pragma once
#include <utility>


#include "pyscene.hpp"
#include "slideio/slideio/slide.hpp"

class PySlide
{
public:
    PySlide(std::shared_ptr<slideio::Slide> slide) : m_slide(slide)
    {
    }
    ~PySlide()
    {
    }
    int getNumScenes() const;
    std::string getFilePath() const;
    std::shared_ptr<PyScene> getScene(int index);
    std::shared_ptr<PyScene> getSceneByName(const std::string& sceneName);
    const std::string& getRawMetadata() const;
    slideio::MetadataFormat getMetadataFormat() const;
    std::list<std::string> getAuxImageNames() const;
    int getNumAuxImages() const;
    std::shared_ptr<PyScene> getAuxImage(const std::string& imageName);
    std::string toString() const;
private:
    std::shared_ptr<slideio::Slide> m_slide;
};
