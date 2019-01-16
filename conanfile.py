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
        "patches/CMakeProjectWrapper.txt",
        "patches/FindOpenNI2.cmake",
        "patches/msvc2017.patch"
    ]
    url = "https://git.ircad.fr/conan/conan-openni"
    license="Apache License 2.0"
    description = "Open Natural Interaction."
    source_subfolder = "source_subfolder"
    build_subfolder = "build_subfolder"
    short_paths = False
    freenect_source = "freenect_src"
    freenect_build = "freenect_build"
    freenect_version = "0.5.7"

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

    def requirements(self):
        if tools.os_info.is_macos:
            self.requires("libusb/1.0.22@sight/stable")

    def source(self):
        rev = "958951f7a6c03c36915e9caf5084b15ecb301d2e"
        tools.get("https://github.com/fw4spl-org/OpenNI2/archive/{0}.tar.gz".format(rev))
        os.rename("OpenNI2-" + rev, self.source_subfolder)

        if tools.os_info.is_linux or tools.os_info.is_macos:
            tools.get("https://github.com/OpenKinect/libfreenect/archive/v{0}.tar.gz".format(self.freenect_version))
            os.rename("libfreenect-" + self.freenect_version, self.freenect_source)

    def build(self):
        openni_source_dir = os.path.join(self.source_folder, self.source_subfolder)
        
        if tools.os_info.is_windows:
            if self.settings.compiler == "Visual Studio":
                cversion = self.settings.compiler.version
                if cversion == "15":
                    tools.patch(openni_source_dir, "patches/msvc2017.patch")

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
                if tools.os_info.is_macos:
                    # Hack to give the correct path for libusb
                    platform_path = os.path.join(openni_source_dir, "ThirdParty", "PSCommon", "BuildSystem", "Platform.x86")
                    
                    with open(platform_path, 'a') as platform_file:
                        platform_file.write("\nCFLAGS+=-I{0}".format(
                            self.deps_cpp_info["libusb"].include_paths[0]
                        ))

                        platform_file.write("\nLDFLAGS+=-l{0} -L{1}".format(
                            self.deps_cpp_info["libusb"].libs[0],
                            self.deps_cpp_info["libusb"].lib_paths[0]
                        ))
                    
                build_cmd = " CFG={0} ALLOW_WARNINGS=1 GLUT_SUPPORTED=0 -f Makefile main".format(self.settings.build_type)
                self.run("make" + build_cmd, cwd=openni_source_dir)

        # Build freenect driver on unix system
        if tools.os_info.is_linux or tools.os_info.is_macos:
            shutil.move("patches/CMakeProjectWrapper.txt", "CMakeLists.txt")
            
            cmake = CMake(self)
            cmake.definitions["BUILD_EXAMPLES"] = "OFF"
            cmake.definitions["BUILD_OPENNI2_DRIVER"] = "ON"

            cmake.configure(build_folder=self.freenect_build)
            cmake.build()
            cmake.install()


    def package(self):
        self.copy("FindOpenNI2.cmake", src="patches", dst=".", keep_path=False)
        self.copy(pattern="*",
                    dst="include/openni2",
                    src="{0}/Include".format(self.source_subfolder),
                    keep_path=True)
        if tools.os_info.is_windows:
            self.copy(pattern="*.dll",
                      dst="bin/OpenNI2/Drivers",
                      src="{0}/Bin/x64-{1}/OpenNI2/Drivers/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.dll",
                      dst="bin",
                      src="{0}/Bin/x64-{1}/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.lib",
                      dst="lib",
                      src="{0}/Bin/x64-{1}/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.lib",
                      dst="lib/OpenNI2/Drivers",
                      src="{0}/Bin/x64-{1}/OpenNI2/Drivers/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*",
                      dst="bin",
                      src="{0}/Config".format(self.source_subfolder),
                      keep_path=True)
        else:
            self.copy(pattern="*.dylib",
                      dst="lib/OpenNI2/Drivers",
                      src="{0}/Bin/x64-{1}/OpenNI2/Drivers/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.dylib",
                      dst="lib",
                      src="{0}/Bin/x64-{1}/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.so",
                      dst="lib/OpenNI2/Drivers",
                      src="{0}/Bin/x64-{1}/OpenNI2/Drivers/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*.so",
                      dst="lib",
                      src="{0}/Bin/x64-{1}/".format(self.source_subfolder, self.settings.build_type),
                      keep_path=False)
            self.copy(pattern="*",
                      dst="lib",
                      src="{0}/Config".format(self.source_subfolder),
                      keep_path=True)

            # Also copy freenect driver into OpenNI2/Drivers

            self.copy(pattern="*",
                      dst="lib/OpenNI2/Drivers",
                      src="{0}/lib/OpenNI2-FreenectDriver/".format(self.freenect_build),
                      keep_path=True)

        if tools.os_info.is_linux:
            # LINUX WARNING
            # primesense-usb.rules should be copied to '/etc/udev/rules.d/557-primesense-usb.rules' with admin rights (sudo)
            # orbbec-usb.rules should be copied to '/etc/udev/rules.d/558-orbbec-usb.rules' with admin rights (sudo)
            # 51-kinect.rules should be copied to '/etc/udev/rules.d/51-kinect.rules' with admin rights (sudo)
            self.copy(pattern="primesense-usb.rules",
                      dst="rules",
                      src="{0}/Packaging/Linux/".format(self.source_subfolder),
                      keep_path=False)
            self.copy(pattern="orbbec-usb.rules",
                      dst="rules",
                      src="{0}/Packaging/Linux/".format(self.source_subfolder),
                      keep_path=False)
            self.copy(pattern="51-kinect.rules",
                      dst="rules",
                      src="{0}/platform/linux/udev/".format(self.freenect_source),
                      keep_path=False)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
