cmake_minimum_required(VERSION 3.25)

# CMP0091 selects the CRT through a target property, rather than editing flags.
project(SSOVisibility VERSION 1.2.1 DESCRIPTION "Native Star Stable visibility controller" LANGUAGES C)

if(NOT WIN32 OR NOT MSVC OR NOT CMAKE_C_COMPILER_ID STREQUAL "MSVC")
    message(FATAL_ERROR "Use Windows with the Microsoft C compiler and x64 MASM (Visual Studio Desktop development with C++).")
endif()
if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8 OR NOT CMAKE_C_COMPILER_ARCHITECTURE_ID STREQUAL "x64")
    message(FATAL_ERROR "This proxy supports Windows x64 only. Select -A x64 or an x64 Developer Command Prompt.")
endif()
enable_language(ASM_MASM RC)

if(NOT CMAKE_CONFIGURATION_TYPES AND NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build configuration" FORCE)
endif()
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/$<CONFIG>")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib/$<CONFIG>")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib/$<CONFIG>")
set(CMAKE_PDB_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/symbols/$<CONFIG>")
set(CMAKE_COMPILE_PDB_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/symbols/$<CONFIG>")
set_property(GLOBAL PROPERTY USE_FOLDERS ON)

include(cmake/VersionResources.cmake)
include(cmake/CompilerOptions.cmake)
find_program(SSO_POWERSHELL NAMES powershell.exe REQUIRED)

set(SSO_HOST "PROXY" CACHE STRING "Loader adapter: PROXY, RESHADE, ASI, or PLUGIN")
set_property(CACHE SSO_HOST PROPERTY STRINGS PROXY RESHADE ASI PLUGIN)
string(TOUPPER "${SSO_HOST}" SSO_HOST)
if(NOT SSO_HOST MATCHES "^(PROXY|RESHADE|ASI|PLUGIN)$")
    message(FATAL_ERROR "SSO_HOST must be PROXY, RESHADE, ASI or PLUGIN")
endif()
set(sso_sources src/host.c src/presets.c src/visibility/visibility_runtime.c
    src/visibility/classifier.inc src/asm/visibility_hooks.asm generated/hook_specs.inc
    generated/particle_policy.inc include/sso_proxy/proxy_internal.h include/sso_proxy/host.h
    include/sso_proxy/presets.h)
if(SSO_HOST STREQUAL "PROXY")
    list(APPEND sso_sources src/proxy_main.c generated/gl_forwarders.asm generated/opengl32.def generated/gl_exports.inc)
else()
    enable_language(CXX)
    list(APPEND sso_sources src/hosts/plugin_host.cpp)
endif()
add_library(sso_visibility SHARED ${sso_sources})
sso_configure_target(sso_visibility)
set_target_properties(sso_visibility PROPERTIES PREFIX "" FOLDER "Visibility")
if(SSO_HOST STREQUAL "PROXY")
    set_target_properties(sso_visibility PROPERTIES OUTPUT_NAME opengl32)
    target_link_options(sso_visibility PRIVATE "/DEF:${CMAKE_CURRENT_SOURCE_DIR}/generated/opengl32.def")
else()
    set_target_properties(sso_visibility PROPERTIES OUTPUT_NAME SSOVisibility)
    if(SSO_HOST STREQUAL "RESHADE")
        set_target_properties(sso_visibility PROPERTIES SUFFIX ".addon64")
    elseif(SSO_HOST STREQUAL "ASI")
        set_target_properties(sso_visibility PROPERTIES SUFFIX ".asi")
    endif()
endif()
target_include_directories(sso_visibility PRIVATE include generated src/visibility)
target_compile_definitions(sso_visibility PRIVATE SSO_VERSION_STRING="${PROJECT_VERSION}")
target_link_libraries(sso_visibility PRIVATE kernel32 user32)
target_link_options(sso_visibility PRIVATE "/MAP:$<TARGET_FILE_DIR:sso_visibility>/$<TARGET_FILE_BASE_NAME:sso_visibility>.map")
set_property(TARGET sso_visibility APPEND PROPERTY LINK_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/write_metadata.ps1"
    "${CMAKE_CURRENT_SOURCE_DIR}/data/visibility-sites.json"
    "${CMAKE_CURRENT_SOURCE_DIR}/data/runtime-layout.json")
add_custom_command(TARGET sso_visibility POST_BUILD
    COMMAND "${SSO_POWERSHELL}" -NoLogo -NoProfile -ExecutionPolicy Bypass
        -File "${CMAKE_CURRENT_SOURCE_DIR}/tools/write_metadata.ps1"
        -DllPath "$<TARGET_FILE:sso_visibility>"
        -MapPath "$<TARGET_FILE_DIR:sso_visibility>/$<TARGET_FILE_BASE_NAME:sso_visibility>.map"
        -SitesPath "${CMAKE_CURRENT_SOURCE_DIR}/data/visibility-sites.json"
        -LayoutPath "${CMAKE_CURRENT_SOURCE_DIR}/data/runtime-layout.json"
        -OutputPath "$<TARGET_FILE_DIR:sso_visibility>/validation/proxy-symbols.json"
    COMMAND "${CMAKE_COMMAND}" "-DSSO_DEFAULT_INI=${CMAKE_CURRENT_SOURCE_DIR}/config/SSOVisibility.ini"
        "-DSSO_OUTPUT_INI=$<TARGET_FILE_DIR:sso_visibility>/SSOVisibility.ini"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/CopyDefaultConfig.cmake"
    COMMENT "Writing matching metadata and installing the initial default INI"
    VERBATIM)
source_group(TREE "${CMAKE_CURRENT_SOURCE_DIR}" FILES ${sso_sources})

include(CTest)
option(SSO_PROXY_ENABLE_ASM_TESTS "Run linked MASM tests (requires Python and Unicorn)" OFF)
find_package(Python3 3.10 QUIET COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
    add_custom_target(regenerate_assets
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_assets.py"
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" VERBATIM)
    set_target_properties(regenerate_assets PROPERTIES FOLDER "Maintenance")
endif()
if(BUILD_TESTING)
    add_subdirectory(tests)
endif()

install(TARGETS sso_visibility RUNTIME DESTINATION . COMPONENT Runtime)
install(FILES config/SSOVisibility.ini DESTINATION . COMPONENT Runtime)
install(FILES docs/USER_GUIDE.md DESTINATION . RENAME README.md COMPONENT Runtime)
install(FILES docs/LOADER_ADAPTERS.md DESTINATION . COMPONENT Runtime)
install(FILES docs/IMPLEMENTATION_STATUS.md DESTINATION . COMPONENT Runtime)
install(FILES tools/read-proxy-state.ps1 DESTINATION . COMPONENT Runtime)
install(FILES "$<TARGET_FILE_DIR:sso_visibility>/validation/proxy-symbols.json"
    DESTINATION validation COMPONENT Runtime)
install(FILES "$<TARGET_FILE_DIR:sso_visibility>/$<TARGET_FILE_BASE_NAME:sso_visibility>.map"
    DESTINATION symbols COMPONENT Symbols)
install(FILES "$<TARGET_PDB_FILE:sso_visibility>"
    DESTINATION symbols COMPONENT Symbols OPTIONAL)

set(CPACK_PACKAGE_NAME "SSO-Visibility-Proxy")
set(CPACK_PACKAGE_VENDOR "SSO visibility proxy project")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Windows x64 visibility presets with OpenGL, ReShade and plugin adapters")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_FILE_NAME "${CPACK_PACKAGE_NAME}-${PROJECT_VERSION}-${SSO_HOST}-win64")
set(CPACK_GENERATOR ZIP)
set(CPACK_PACKAGE_DIRECTORY "${CMAKE_BINARY_DIR}/packages")
set(CPACK_SOURCE_GENERATOR ZIP)
set(CPACK_SOURCE_PACKAGE_FILE_NAME "${CPACK_PACKAGE_NAME}-${PROJECT_VERSION}-source")
set(CPACK_SOURCE_IGNORE_FILES "/out/;/\\.git/;/\\.vs/;/__pycache__/;\\.pyc$;CMakeUserPresets\\.json$;\\.log$")
include(CPack)

message(STATUS "Host ${SSO_HOST}: ${PROJECT_VERSION}, x64 MSVC + MASM, static CRT; game layout 645.348067")
message(STATUS "Native tests: ${BUILD_TESTING}; optional Python tests: ${Python3_Interpreter_FOUND}")
