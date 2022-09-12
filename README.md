# HoloLens2ResearchModeTools

This repo includes the development tools for HoloLens2.

## Contents

### [HL2ResearchModeUnityPlugin](HL2ResearchModeUnityPlugin)
The Unity Plugin built upon the [HoloLens2ForCV](https://github.com/microsoft/HoloLens2ForCV) and [HoloLens2-Unity-ResearchModeStreamer](https://github.com/cgsaxner/HoloLens2-Unity-ResearchModeStreamer) repos.

It serves as a streamer server publishing AHaT and PV frame streamings via predefined ports. Details are listed as below:

- AHaT Depth Frame (Port 10091)
  - Frame header
  - Depth data (512x512@45FPS)
  - `Rig2World` transform

- PV Frame (Port 10090)
  - Frame header
  - RGB Data (640x360@30FPS)
  - Intrinsic info (fx, fy, cx, cy)
  - `Pv2World` transform

### [UnityHL2Streamer](UnityProjects\UnityHL2Streamer)
The Unity Project demo to publish AHaT and PV streamings.
A **pre-built app is provided [here](UnityProjects\UnityHL2Streamer\App\UnityHL2Streamer_1.0.0.0_arm64.msixbundle)**, you could install it in Hololens Windows Device Portal.
- `Views > Apps > Deploy apps > Local Storage > Choose File > Install`

![app_install_1](docs/resources/unity_project/app_install_1.png)
![app_install_2](docs/resources/unity_project/app_install_2.png)

### PythonScripts
- [HL2StreamingCient.py](PythonScripts\HL2StreamingCient.py)
  A demo script for subscribing streamings from HoloLens 2.
  ```shell
  python3 HL2StreamingCient.py
  ```
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

## How to use
### Method One
Download the **[pre-built app](UnityProjects\UnityHL2Streamer\App\UnityHL2Streamer_1.0.0.0_arm64.msixbundle)** and install it on HoloLens 2 in Windows Device Portal.

### Method Two
Modify the codes of **HL2ResearchModeUnityPlugin** and compile step by step.
#### Step 1: Setup the Developer Environment

- A Desktop with Windows 10/11
  - Enable **developer mode** at `Settings > Update & Security > For developers`
  ![enable_developer_mode](docs/resources/windows_developer_mode.png)

- HoloLens 2
  - Enable Research Mode on HoloLens 2
  Research mode allows us to access data of more sensors other than PV. Follow steps in this [article](https://docs.microsoft.com/en-us/windows/mixed-reality/develop/advanced-concepts/research-mode#enabling-research-mode-hololens-first-gen-and-hololens-2) to enable Research Mode.

  - Windows Device Portal
  The Windows Device Portal for HoloLens lets us configure and manage your device remotely over Wi-Fi or USB, it's really useful for developing (we could use [REST API](https://docs.microsoft.com/en-us/windows/mixed-reality/develop/advanced-concepts/device-portal-api-reference) to control the device programmatically). Follow steps in this [article](https://docs.microsoft.com/en-us/windows/mixed-reality/develop/advanced-concepts/using-the-windows-device-portal) to enable Windows Device Portal.

- Unity3D
  - Download `UnityHub` and install `Unity 2021.3.9f1 LTS`
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

#### Step 2: Add MRTK features to Unity Project
- Download the [Mixed Reality Feature Tool](https://docs.microsoft.com/en-us/windows/mixed-reality/develop/unity/welcome-to-mr-feature-tool)
- Install [.NET 5.0 runtime](https://dotnet.microsoft.com/download/dotnet/5.0)
- Unzip & launch the Mixed Reality Feature Tool
  ![mrtk_1](docs/resources/unity_project/mrtk_setup_1.png)
- Select path to your Unity Project
  ![mrtk_2](docs/resources/unity_project/mrtk_setup_2.png)
- Select & import feature packages
  - `Mixed Reality Toolkit > Mixed Reality Toolkit Foundation`
  - `Mixed Reality Toolkit > Mixed Reality Toolkit Standard Assets`
  - `Platform Support > Mixed Reality OpenXR Plugin`
  ![mrtk_2](docs/resources/unity_project/mrtk_setup_3.png)
  ![mrtk_3](docs/resources/unity_project/mrtk_setup_4.png)
  ![mrtk_4](docs/resources/unity_project/mrtk_setup_5.png)
  ![mrtk_5](docs/resources/unity_project/mrtk_setup_6.png)

#### Step 3: Configure MRTK in Unity Project
- Go to your Unity project editor, you should be asked to restart editor to enable the backends
  ![](docs/resources/unity_project/mrtk_setup_7.png)
- Configure MRTK features
  - Click `Unity OpenXR plugin (recommended)`
  ![](docs/resources/unity_project/mrtk_setup_8.png)
  - Set `XR Plug-in Management Settings`
  ![](docs/resources/unity_project/mrtk_setup_9.png)
  - Click the yellow warning icon to fix all issues
  ![](docs/resources/unity_project/mrtk_setup_10.png)
  - Add `Microsoft Hand Interaction Profile` and set `Depth Submission Mode` to **`16 bit`**
  ![](docs/resources/unity_project/mrtk_setup_11.png)
  - Apply Settings for first time setup
  ![](docs/resources/unity_project/mrtk_setup_12.png)
  - Select all `Project Settings` and `UWP Capabilities`, then click `Apply`
  ![](docs/resources/unity_project/mrtk_setup_13.png)
  - Import the `TextMeshPro`
  ![](docs/resources/unity_project/mrtk_setup_14.png)
  - Finish the MRTK setup
  ![](docs/resources/unity_project/mrtk_setup_15.png)

#### Step 4: Build the `HL2ResearchModeUnityPlugin` with Visual Studio
- Open the plugin solution in Visual Studio.
- Build the solution for `Release, ARM64`.
You could find the `HL2ResearchModeUnityPlugin.dll` under `HL2ResearchModeUnityPlugin > ARM64 > Release > HL2RmStreamUnityPlugin`.

#### Build the Unity Project
- Create the folder `Assets/Plugins/WSA/ARM64`.
- Copy the `HL2ResearchModeUnityPlugin.dll` to the folder created in last step.
- Then modify the import settings for the `.dll` file
  - `SDK > UWP`
  - `CPU > ARM64`
   ![dll_import_setting](docs/resources/dll_plugin_import_setting.png)
- Config the `Build Settings` with `File > Build Settings` as below:
  - `Architecture > ARM 64-bit`
  - `Target SDK Version > 10.0.20348.0`
  - `Minimum Platform Version > 10.0.18362.0`
  - `Build Configuration > Release`
   ![unity_build_settings](docs/resources/unity_build_settings.png)
- Make sure following Capabilities are enabled in `Build Settings > Player Settings`:
  - InternetClient
  - InternetClientServer
  - PrivateNetworkClientServer
  - WebCam
  - SpatialPerception
  ![player_setting](docs/resources/unity_player_setting.png)
- Build the Unity Project and
- Open the solution in Visual Studio.
  - Open the `Package.appxmanifest` in the solution in a text editor to add the restricted capability to the manifest file for research mode:
  - Add rescap package to `<Package>`
  `xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"`
  - Add rescap to the Ignorable Namespaces under `<Package>`
  `IgnorableNamespaces="... rescap"`
  - Add rescap capability to `<Capabilities>`
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
       - Build solution for `Release, ARM64`
       - Deploy to HoloLens 2.
      For details of deploying, please refer to this [article](https://docs.microsoft.com/en-us/windows/mixed-reality/develop/advanced-concepts/using-visual-studio?tabs=hl2#deploying-a-hololens-app-over-wi-fi-or-usb).
## Notes
- How to get rig2depth transform matrix?
  Build and run the [StreamRecorder](https://github.com/microsoft/HoloLens2ForCV/tree/main/Samples/StreamRecorder) sample on HoloLens 2, you could find the `Depth Long Throw_extrinsics.txt` file under `System->FileExplorer->LocalAppData->StreamRecorder->LocalState` via Device Portal.
- How to extract point cloud from depth image?
  HoloLens does not provide intrinsic of Depth camera, they provide a look-up-table `.bin` file to reconstruct point cloud.
  - For long throw depth, build and run the [StreamRecorder](https://github.com/microsoft/HoloLens2ForCV/tree/main/Samples/StreamRecorder) sample on HoloLens 2, you could find the `Depth Long Throw_lut.bin` file under `System->FileExplorer->LocalAppData->StreamRecorder->LocalState` via Device Portal.
  - For AHaT depth, modify code for AHaT depth, then build and run the [StreamRecorder](https://github.com/microsoft/HoloLens2ForCV/tree/main/Samples/StreamRecorder) sample on HoloLens 2, you could find the `Depth AHaT_lut.bin` file under `System->FileExplorer->LocalAppData->StreamRecorder->LocalState` via Device Portal.
