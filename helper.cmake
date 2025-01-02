MACRO(FIX_MACOS_RPATH target)
    IF (APPLE)
        FOREACH(entry ${NAME_TOOL_LIB_LIST})
            string(REPLACE "@rpath/" "" new_val ${entry})
            message("Fixing rpath for ${target}: ${entry} -> ${new_val}")
            add_custom_command(TARGET ${target}
                POST_BUILD COMMAND
                ${CMAKE_INSTALL_NAME_TOOL} -change ${entry} @loader_path/${new_val}
                $<TARGET_FILE:${target}>)
        ENDFOREACH()
    ENDIF()
ENDMACRO(FIX_MACOS_RPATH)
