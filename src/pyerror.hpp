// This file is part of slideio project.
// It is subject to the license terms in the LICENSE file found in the top-level directory
// of this distribution and at http://slideio.com/license.html.
#pragma once
#include <string>
#include <sstream>

struct PyError : public std::exception {
    template <typename T>
    PyError& operator << (T rhs) {
        m_innerStream << rhs;
        return *this;
    }
    PyError() = default;
    PyError(PyError& rhs) {
        std::string message = rhs.m_innerStream.str();
        m_innerStream << message;
    }
    virtual const char* what() const noexcept {
        m_message = m_innerStream.str();
        return m_message.c_str();
    }
private:
    std::stringstream m_innerStream;
    mutable std::string m_message;
};

#define RAISE_PYERROR throw PyError() << __FILE__ << ":" << __LINE__ << ":"
