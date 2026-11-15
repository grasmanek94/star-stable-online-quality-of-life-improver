if(NOT EXISTS "${SSO_OUTPUT_INI}")
    configure_file("${SSO_DEFAULT_INI}" "${SSO_OUTPUT_INI}" COPYONLY)
endif()
