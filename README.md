# HoloLens2ResearchModeTools

This repo includes the development tools for HoloLens2.

## HL2ResearchModeUnityPlugin
The Unity Plugin built upon the [HoloLens2ForCV](https://github.com/microsoft/HoloLens2ForCV) and [HoloLens2-Unity-ResearchModeStreamer](https://github.com/cgsaxner/HoloLens2-Unity-ResearchModeStreamer) repos.

It serves as a streamer server publishing Depth AHaT and PV camera streamings via predefined ports. Details are listed as below:

- AHaT Depth Frame
  - Frame header
  - Depth data (512x512@45FPS)
  - `Rig2World` transforms

- PV Frame
  - Frame header
  - RGB Data (640x360@30FPS)
  - Intrinsic info (fx, fy, cx, cy)
  - `PV2World` transforms

## [UnityHL2Streamer](UnityProjects\UnityHL2Streamer)
The Unity Project demo to publish AHaT and PV streamings.
A compiled app file is provided [here](UnityProjects\UnityHL2Streamer\App\UnityHL2Streamer_1.0.0.0_arm64.msixbundle), we could install it in Hololens Windows Device Portal.
- `Views > Apps > Deploy apps > Local Storage > Choose File > Install`

![app_install_1](docs/resources/unity_project/app_install_1.png)
![app_install_2](docs/resources/unity_project/app_install_2.png)

## PythonScripts
- [HL2StreamingCient.py](PythonScripts\HL2StreamingCient.py)
  A demo script for subscribe streamings from HoloLens 2 streamer.
![client_demo](docs/resources/python_client_demo.png)

- [HoloLens2_ROS_Publisher.py](PythonScripts\HoloLens2_ROS_Publisher.py)
  A demo Publisher script used in ROS to register streamings from HoloLens2 and publish as topics.
  ```shell
  # Publish color streaming
  python3 HoloLens2_ROS_Publisher.py --host <HoloLens_IP_Addr> --sensor_type color
  # Publish depth streaming
  python3 HoloLens2_ROS_Publisher.py --host <HoloLens_IP_Addr> --sensor_type depth
  ```
  By detecting color sensor's position using AprilTag, people could visualize hololens's pose in real time with RVIZ tool.
  ![ros_publisher_demo](docs/resources/hololens2_ROS_publisher_demo.gif)

## Setup the Developer Environment

- A PC with Windows 10/11
  - Enable developer mode at `Settings > Update & Security > For developers`
  ![enable_developer_mode](docs/resources/windows_developer_mode.png)

- HoloLens 2
  - Enable Research Mode on HoloLens 2
  Research mode allows us to access data of more sensors other than PV. Follow steps in this [article](https://docs.microsoft.com/en-us/windows/mixed-reality/develop/advanced-concepts/research-mode#enabling-research-mode-hololens-first-gen-and-hololens-2) to enable Research Mode.

  - Windows Device Portal
  The Windows Device Portal for HoloLens lets us configure and manage your device remotely over Wi-Fi or USB, it's really useful for developing (we could use [REST API](https://docs.microsoft.com/en-us/windows/mixed-reality/develop/advanced-concepts/device-portal-api-reference) to control the device programmatically). Follow steps in this [article](https://docs.microsoft.com/en-us/windows/mixed-reality/develop/advanced-concepts/using-the-windows-device-portal) to enable Windows Device Portal.

- Unity 2021.3.9f1 LTS
  - The Visual Studio 2019 will be installed by default
  - Check the module `Universal Windows Platform Build Support`
  ![unity_installation](docs/resources/unity_installation.png)

- Installing Visual Studio 2019
  Be sure following workloads are installed
  - .NET desktop development
  - Desktop development with C++
  - Universal Windows Platform (UWP) development
    - Windows 10 SDK version 10.0.18362.0
    - USB Device Connectivity
    - C++ (v142) Universal Windows Platform tools
  ![visual_studio_2019_install](docs/resources/visual_studio_2019_config.png)

## Using the Plugin
- Build the Unity Plugin with Visual Studio
  1. Open the plugin solution in Visual Studio.
  2. Build the solution for `Release, ARM64`.
  3. You could find the `HL2ResearchModeUnityPlugin.dll` under `HL2ResearchModeUnityPlugin > ARM64 > Release > HL2RmStreamUnityPlugin`.
- In the Unity Project
  1. Download the Mixed Reality Feature Tool ([.NET 5.0 runtime](https://dotnet.microsoft.com/download/dotnet/5.0) required)
        -
  2. Create a folder `Assets/Plugins/WSA/ARM64`.
  3. Copy the `HL2ResearchModeUnityPlugin.dll` to the folder created in last step. And modify the import settings for the `.dll` file
   ![dll_import_setting](docs/resources/dll_plugin_import_setting.png)
  4. Config the `Build Settings` with `File > Build Settings` as below:
   ![unity_build_settings](docs/resources/unity_build_settings.png)
  5. Make sure following Capabilities are enabled in `Build Settings > Player Settings`:
     - InternetClient
     - InternetClientServer
     - PrivateNetworkClientServer
     - WebCam
     - SpatialPerception
   ![player_setting](docs/resources/unity_player_setting.png)
  6. Build the Unity Project and open the solution in Visual Studio.
  7. Open the `Package.appxmanifest` in the solution in a text editor to add the restricted capability to the manifest file for research mode:
       - add rescap package to `<Package>`
       `xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"`
       - add rescap to the Ignorable Namespaces under `<Package>`
       `IgnorableNamespaces="... rescap"`
       - add rescap capability to `<Capabilities>`
       `<rescap:Capability Name="perceptionSensorsExperimental" />`
       - an example is listed below (`<DeviceCapability Name="backgroundSpatialPerception"/>` is only necessary if you use IMU sensor)
           ```xml
           <Package
               xmlns:mp="http://schemas.microsoft.com/appx/2014/phone/manifest"
               xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
               xmlns:uap2="http://schemas.microsoft.com/appx/manifest/uap/windows10/2"
               xmlns:uap3="http://schemas.microsoft.com/appx/manifest/uap/windows10/3"
               xmlns:uap4="http://schemas.microsoft.com/appx/manifest/uap/windows10/4"
               xmlns:iot="http://schemas.microsoft.com/appx/manifest/iot/windows10"
               xmlns:mobile="http://schemas.microsoft.com/appx/manifest/mobile/windows10"
               xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
               IgnorableNamespaces="uap uap2 uap3 uap4 mp mobile iot rescap"
               xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10">

           <Capabilities>
               <rescap:Capability Name="perceptionSensorsExperimental" />
               <Capability Name="internetClient" />
               <Capability Name="internetClientServer" />
               <Capability Name="privateNetworkClientServer" />
               <uap2:Capability Name="spatialPerception" />
               <DeviceCapability Name="webcam" />
           </Capabilities>
           ```
       - build solution for `Release, ARM64`
       - deploy to HoloLens 2. For details of deploying, please refer to this [article](https://docs.microsoft.com/en-us/windows/mixed-reality/develop/advanced-concepts/using-visual-studio?tabs=hl2#deploying-a-hololens-app-over-wi-fi-or-usb).
