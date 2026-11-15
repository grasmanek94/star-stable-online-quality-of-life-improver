include_guard(GLOBAL)

# All executable/shared/module targets configured by this project get the same
# product identity. Target filename expressions resolve after OUTPUT_NAME/SUFFIX.
function(sso_add_version_resource target)
    get_target_property(target_type ${target} TYPE)
    if(target_type STREQUAL "EXECUTABLE")
        set(resource_type VFT_APP)
    elseif(target_type MATCHES "^(SHARED_LIBRARY|MODULE_LIBRARY)$")
        set(resource_type VFT_DLL)
    else()
        return()
    endif()

    set(resource_path "${CMAKE_CURRENT_BINARY_DIR}/version/$<CONFIG>/${target}.rc")
    set(resource_target "${target}_version_resource")
    set(version_tweak "${PROJECT_VERSION_TWEAK}")
    if(version_tweak STREQUAL "")
        set(version_tweak 0)
    endif()
    add_custom_target(${resource_target}
        COMMAND "${CMAKE_COMMAND}"
            "-DSSO_RESOURCE_OUTPUT=${resource_path}"
            "-DSSO_RESOURCE_TEMPLATE=${CMAKE_CURRENT_FUNCTION_LIST_DIR}/version.rc.in"
            "-DSSO_RESOURCE_FILENAME=$<TARGET_FILE_NAME:${target}>"
            "-DSSO_RESOURCE_INTERNAL_NAME=$<TARGET_FILE_BASE_NAME:${target}>"
            "-DSSO_RESOURCE_FILETYPE=${resource_type}"
            "-DSSO_RESOURCE_DEBUG=$<IF:$<CONFIG:Debug>,1,0>"
            "-DSSO_RESOURCE_VERSION=${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}.${PROJECT_VERSION_PATCH}.${version_tweak}"
            "-DSSO_RESOURCE_VERSION_TUPLE=${PROJECT_VERSION_MAJOR},${PROJECT_VERSION_MINOR},${PROJECT_VERSION_PATCH},${version_tweak}"
            -P "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/GenerateVersionResource.cmake"
        BYPRODUCTS "${resource_path}"
        COMMENT "Checking PE version resource for ${target}"
        VERBATIM)
    set_target_properties(${resource_target} PROPERTIES FOLDER "Build support")
    add_dependencies(${target} ${resource_target})
    target_sources(${target} PRIVATE "${resource_path}")
    source_group("Resources" FILES "${resource_path}")
endfunction()
