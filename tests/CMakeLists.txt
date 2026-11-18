add_executable(sso_runtime_tests
    runtime_tests.c client_audit.c ../src/visibility/visibility_runtime.c ../src/asm/visibility_hooks.asm)
sso_configure_test(sso_runtime_tests)
target_compile_definitions(sso_runtime_tests PRIVATE SSO_PROXY_TESTING)
target_include_directories(sso_runtime_tests PRIVATE ../include ../generated ../src/visibility)
target_link_libraries(sso_runtime_tests PRIVATE kernel32 user32)
add_test(NAME runtime COMMAND sso_runtime_tests)
set_tests_properties(runtime PROPERTIES TIMEOUT 60 PASS_REGULAR_EXPRESSION "NATIVE_PROXY_TESTS_PASS")

if(SSO_HOST STREQUAL "PROXY")
add_executable(sso_forwarding_tests forwarding_tests.c)
sso_configure_test(sso_forwarding_tests)
target_link_libraries(sso_forwarding_tests PRIVATE kernel32)
add_dependencies(sso_forwarding_tests sso_visibility)
add_test(NAME forwarding COMMAND sso_forwarding_tests "$<TARGET_FILE:sso_visibility>")
set_tests_properties(forwarding PROPERTIES TIMEOUT 30 PASS_REGULAR_EXPRESSION "FORWARDING_TESTS_PASS 368")

else()
    add_executable(sso_plugin_tests plugin_tests.cpp)
    sso_configure_test(sso_plugin_tests)
    target_link_libraries(sso_plugin_tests PRIVATE kernel32)
    add_dependencies(sso_plugin_tests sso_visibility)
    add_test(NAME plugin_loader COMMAND sso_plugin_tests "$<TARGET_FILE:sso_visibility>")
    set_tests_properties(plugin_loader PROPERTIES TIMEOUT 30)
endif()

add_executable(sso_preset_tests preset_tests.c ../src/presets.c)
sso_configure_test(sso_preset_tests)
target_include_directories(sso_preset_tests PRIVATE ../include)
add_test(NAME presets COMMAND sso_preset_tests "${PROJECT_SOURCE_DIR}/config/SSOVisibility.ini")
set_tests_properties(presets PROPERTIES TIMEOUT 30)

if(Python3_Interpreter_FOUND)
    add_library(sso_classifier_test SHARED classifier_bridge.c classifier_bridge.def)
    sso_configure_test(sso_classifier_test)
    target_include_directories(sso_classifier_test PRIVATE ../src/visibility ../generated)
    target_link_options(sso_classifier_test PRIVATE "/DEF:${CMAKE_CURRENT_SOURCE_DIR}/classifier_bridge.def")
    add_test(NAME classifier COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test_classifier.py"
        --dll "$<TARGET_FILE:sso_classifier_test>"
        --report "$<TARGET_FILE_DIR:sso_classifier_test>/validation/classifier.json")
    add_test(NAME generated_assets COMMAND "${Python3_EXECUTABLE}"
        "${PROJECT_SOURCE_DIR}/tools/generate_assets.py" --check)
    set_tests_properties(classifier generated_assets PROPERTIES TIMEOUT 30)
endif()

if(SSO_PROXY_ENABLE_ASM_TESTS)
    if(NOT Python3_Interpreter_FOUND)
        message(FATAL_ERROR "ASM tests require 64-bit Python 3.10+ and tests/requirements.txt.")
    endif()
    execute_process(COMMAND "${Python3_EXECUTABLE}" -c "import unicorn"
        RESULT_VARIABLE unicorn_status OUTPUT_QUIET ERROR_QUIET)
    if(NOT unicorn_status EQUAL 0)
        message(FATAL_ERROR "ASM tests require Unicorn: python -m pip install -r tests/requirements.txt")
    endif()
    add_test(NAME compiled_assembly COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/test_compiled_asm.py"
        --dll "$<TARGET_FILE:sso_visibility>"
        --map "$<TARGET_FILE_DIR:sso_visibility>/$<TARGET_FILE_BASE_NAME:sso_visibility>.map"
        --report "$<TARGET_FILE_DIR:sso_visibility>/validation/compiled-assembly.json")
    set_tests_properties(compiled_assembly PROPERTIES TIMEOUT 60)
endif()
