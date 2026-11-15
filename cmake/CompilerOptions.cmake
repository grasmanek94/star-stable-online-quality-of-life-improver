include_guard(GLOBAL)

function(sso_configure_target target)
    set_target_properties(${target} PROPERTIES
        C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO
        CXX_STANDARD 17 CXX_STANDARD_REQUIRED YES CXX_EXTENSIONS NO
        MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>"
        MSVC_DEBUG_INFORMATION_FORMAT "$<$<CONFIG:Debug,RelWithDebInfo>:ProgramDatabase>"
        VS_GLOBAL_VcpkgEnabled false
    )
    target_compile_definitions(${target} PRIVATE _WIN32_WINNT=0x0602)
    target_compile_options(${target} PRIVATE "$<$<COMPILE_LANGUAGE:C,CXX>:/W4;/utf-8>")
    # Stable direct symbols are needed by the link-map diagnostic and ASM tests.
    target_link_options(${target} PRIVATE /DYNAMICBASE /NXCOMPAT /INCREMENTAL:NO
        "$<$<CONFIG:Release,RelWithDebInfo>:/OPT:REF;/OPT:ICF>")
    sso_add_version_resource(${target})
endfunction()

function(sso_configure_test target)
    sso_configure_target(${target})
    # Each native test source enables its assertions before including assert.h.
    set_target_properties(${target} PROPERTIES FOLDER "Tests")
endfunction()
