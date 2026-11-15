cmake_minimum_required(VERSION 3.25)

# CMP0091 selects the CRT through a target property, rather than editing flags.
project(SSOVisibilityProxy VERSION 1.1.0 DESCRIPTION "Star Stable OpenGL visibility proxy" LANGUAGES C)

if(NOT WIN32 OR NOT MSVC OR NOT CMAKE_C_COMPILER_ID STREQUAL "MSVC")
    message(FATAL_ERROR "Use Windows with the Microsoft C compiler and x64 MASM (Visual Studio Desktop development with C++).")
endif()
if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8 OR NOT CMAKE_C_COMPILER_ARCHITECTURE_ID STREQUAL "x64")
    message(FATAL_ERROR "This proxy supports Windows x64 only. Select -A x64 or an x64 Developer Command Prompt.")
endif()
enable_language(ASM_MASM)

if(NOT CMAKE_CONFIGURATION_TYPES AND NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build configuration" FORCE)
endif()
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/$<CONFIG>")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib/$<CONFIG>")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib/$<CONFIG>")
set(CMAKE_PDB_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/symbols/$<CONFIG>")
set(CMAKE_COMPILE_PDB_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/symbols/$<CONFIG>")
set_property(GLOBAL PROPERTY USE_FOLDERS ON)

include(cmake/CompilerOptions.cmake)
find_program(SSO_POWERSHELL NAMES powershell.exe REQUIRED)

add_library(sso_opengl_proxy SHARED
    src/proxy_main.c
    src/visibility/visibility_runtime.c
    src/visibility/classifier.inc
    src/asm/visibility_hooks.asm
    generated/gl_forwarders.asm
    generated/opengl32.def
    generated/gl_exports.inc
    generated/hook_specs.inc
    include/sso_proxy/proxy_internal.h
)
sso_configure_target(sso_opengl_proxy)
set_target_properties(sso_opengl_proxy PROPERTIES OUTPUT_NAME opengl32 PREFIX "" FOLDER "Proxy")
target_include_directories(sso_opengl_proxy PRIVATE include generated src/visibility)
target_link_libraries(sso_opengl_proxy PRIVATE kernel32 user32)
target_link_options(sso_opengl_proxy PRIVATE
    "/DEF:${CMAKE_CURRENT_SOURCE_DIR}/generated/opengl32.def"
    "/MAP:$<TARGET_FILE_DIR:sso_opengl_proxy>/opengl32.map"
)
set_property(TARGET sso_opengl_proxy APPEND PROPERTY LINK_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/write_metadata.ps1"
    "${CMAKE_CURRENT_SOURCE_DIR}/data/visibility-sites.json"
)
add_custom_command(TARGET sso_opengl_proxy POST_BUILD
    COMMAND "${SSO_POWERSHELL}" -NoLogo -NoProfile -ExecutionPolicy Bypass
        -File "${CMAKE_CURRENT_SOURCE_DIR}/tools/write_metadata.ps1"
        -DllPath "$<TARGET_FILE:sso_opengl_proxy>"
        -MapPath "$<TARGET_FILE_DIR:sso_opengl_proxy>/opengl32.map"
        -SitesPath "${CMAKE_CURRENT_SOURCE_DIR}/data/visibility-sites.json"
        -OutputPath "$<TARGET_FILE_DIR:sso_opengl_proxy>/validation/proxy-symbols.json"
    COMMENT "Writing DLL-specific diagnostic metadata"
    VERBATIM
)
source_group(TREE "${CMAKE_CURRENT_SOURCE_DIR}" FILES
    src/proxy_main.c src/visibility/visibility_runtime.c src/visibility/classifier.inc
    src/asm/visibility_hooks.asm generated/gl_forwarders.asm generated/opengl32.def
    generated/gl_exports.inc generated/hook_specs.inc include/sso_proxy/proxy_internal.h)

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

install(TARGETS sso_opengl_proxy RUNTIME DESTINATION . COMPONENT Runtime)
install(FILES docs/USER_GUIDE.md DESTINATION . RENAME README.md COMPONENT Runtime)
install(FILES tools/read-proxy-state.ps1 DESTINATION . COMPONENT Runtime)
install(FILES "$<TARGET_FILE_DIR:sso_opengl_proxy>/validation/proxy-symbols.json"
    DESTINATION validation COMPONENT Runtime)
install(FILES "$<TARGET_FILE_DIR:sso_opengl_proxy>/opengl32.map"
    DESTINATION symbols COMPONENT Symbols)
install(FILES "$<TARGET_PDB_FILE:sso_opengl_proxy>"
    DESTINATION symbols COMPONENT Symbols OPTIONAL)

set(CPACK_PACKAGE_NAME "SSO-Visibility-Proxy")
set(CPACK_PACKAGE_VENDOR "SSO visibility proxy project")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Windows x64 OpenGL forwarding and local visibility controls")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_FILE_NAME "${CPACK_PACKAGE_NAME}-${PROJECT_VERSION}-win64")
set(CPACK_GENERATOR ZIP)
set(CPACK_PACKAGE_DIRECTORY "${CMAKE_BINARY_DIR}/packages")
set(CPACK_SOURCE_GENERATOR ZIP)
set(CPACK_SOURCE_PACKAGE_FILE_NAME "${CPACK_PACKAGE_NAME}-${PROJECT_VERSION}-source")
set(CPACK_SOURCE_IGNORE_FILES "/out/;/\\.git/;/\\.vs/;/__pycache__/;\\.pyc$;CMakeUserPresets\\.json$;\\.log$")
include(CPack)

message(STATUS "Proxy: ${PROJECT_VERSION}, x64 MSVC + MASM, static CRT; game layout 645.348067")
message(STATUS "Native tests: ${BUILD_TESTING}; optional Python tests: ${Python3_Interpreter_FOUND}")
