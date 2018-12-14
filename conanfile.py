from conans import ConanFile, CMake, tools, AutoToolsBuildEnvironment, MSBuild
from conans.util import files
import os
import shutil

class LibOpenniConan(ConanFile):
    name = "openni"
    version = "2.2.0-rev-958951f"
    generators = "cmake"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = "shared=True"
    exports = [
        "patches/FindOpenNI2.cmake",
        "patches/msvc2017.patch"
    ]
    url = "https://git.ircad.fr/conan/conan-openni"
    license="Apache License 2.0"
    description = "Open Natural Interaction."
    source_subfolder = "source_subfolder"
    build_subfolder = "build_subfolder"
    short_paths = False

    def configure(self):
        del self.settings.compiler.libcxx
        if 'CI' not in os.environ:
            os.environ["CONAN_SYSREQUIRES_MODE"] = "verify"

    def build_requirements(self):
        if tools.os_info.linux_distro == "linuxmint":
            pack_names = [
                "libusb-1.0-0-dev",
                "libudev-dev"
            ]
            installer = tools.SystemPackageTool()
            for p in pack_names:
                installer.install(p)

    def system_requirements(self):
        if tools.os_info.linux_distro == "linuxmint":
            pack_names = [
                "libusb-1.0-0",
                "libudev1"
            ]
            installer = tools.SystemPackageTool()
            for p in pack_names:
                installer.install(p)

    def source(self):
        rev = "958951f7a6c03c36915e9caf5084b15ecb301d2e"
        tools.get("https://github.com/fw4spl-org/OpenNI2/archive/{0}.tar.gz".format(rev))
        os.rename("OpenNI2-" + rev, self.source_subfolder)

    def build(self):
        openni_source_dir = os.path.join(self.source_folder, self.source_subfolder)
        if self.settings.compiler == "Visual Studio":
            cversion = self.settings.compiler.version
            if cversion == "15":
                tools.patch(openni_source_dir, "patches/msvc2017.patch")

        if tools.os_info.is_windows:
            msbuild = MSBuild(self)
            openni_sln = os.path.join(openni_source_dir, "OpenNI.sln")
            msbuild.build(
                project_file=openni_sln,
                targets=["OpenNI", r"Devices\PS1080", r"Devices\ORBBEC"],
                build_type=self.settings.build_type,
                upgrade_project=False
            )
        else:
            env_build = AutoToolsBuildEnvironment(self)
            with tools.environment_append(env_build.vars):
                build_cmd = " CFG={0} ALLOW_WARNINGS=1 GLUT_SUPPORTED=0 -f Makefile main".format(self.settings.build_type)
                self.run("make" + build_cmd, cwd=openni_source_dir)

    def package(self):
        self.copy("FindOpenNI2.cmake", src="patches", dst=".", keep_path=False)
        self.copy(pattern="*",
                    dst="include/openni2",
                    src="{0}/Include".format(self.source_subfolder),
                    keep_path=True)
        if tools.os_info.is_windows:
            self.copy(pattern="*.dll",
                      dst="bin/openni2/OpenNI2/Drivers/",
                      src="{0}/Bin/x64-{1}/OpenNI2/Drivers/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.dll",
                      dst="bin/openni2",
                      src="{0}/Bin/x64-{1}/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.lib",
                      dst="lib/openni2",
                      src="{0}/Bin/x64-{1}/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.lib",
                      dst="lib/openni2/OpenNI2/Drivers/",
                      src="{0}/Bin/x64-{1}/OpenNI2/Drivers/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*",
                      dst="bin/openni2",
                      src="{0}/Config".format(self.source_subfolder),
                      keep_path=True)
        else:
            self.copy(pattern="*.dylib",
                      dst="lib/openni2/OpenNI2/Drivers/",
                      src="{0}/Bin/x64-{1}/OpenNI2/Drivers/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.dylib",
                      dst="lib/openni2",
                      src="{0}/Bin/x64-{1}/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.so",
                      dst="lib/openni2/OpenNI2/Drivers/",
                      src="{0}/Bin/x64-{1}/OpenNI2/Drivers/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.so",
                      dst="lib/openni2",
                      src="{0}/Bin/x64-{1}/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*",
                      dst="lib/openni2",
                      src="{0}/Config".format(self.source_subfolder),
                      keep_path=True)

        if tools.os_info.is_linux:
            # LINUX WARNING
            # primesense-usb.rules should be copied to '/etc/udev/rules.d/557-primesense-usb.rules' with admin rights (sudo)
            # orbbec-usb.rules should be copied to '/etc/udev/rules.d/558-orbbec-usb.rules' with admin rights (sudo)
            self.copy(pattern="primesense-usb.rules",
                      dst="rules",
                      src="{0}/Packaging/Linux/".format(self.source_subfolder),
                      keep_path=False)
            self.copy(pattern="orbbec-usb.rules",
                      dst="rules",
                      src="{0}/Packaging/Linux/".format(self.source_subfolder),
                      keep_path=False)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
