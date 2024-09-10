# User guide

**QGIS Conefor** is a plugin for the Open Source GIS software [QGIS](http://qgis.org) that allows to interact with 
the [Conefor](http://conefor.org) application.

This plugin includes an interface which can be used for preparing inputs to use by Conefor as a separate
application.

??? example "Running Conefor algorithms from inside QGIS"

    This plugin also aims to provide a bridge between QGIS and Conefor, allowing you to run Conefor's landscape 
    connectivity analysis algorithms from inside QGIS, through the QGIS Processing framework/toolbox. 

    **This feature is still work-in-progress** and is therefore not available yet. When ready, it will present a 
    convenient environment for landscape and habitat analysis, enabling Conefor algorithms to be directly integrated 
    in more complex workflows through models and scripts and use all other GIS algorithms included in the QGIS 
    processing framework/toolbox.

    Stay tuned for future updates on the landing of this feature.


Once installed, the plugin tools can be reached in different places:

- From the main menu: _vector > Conefor inputs_
- The _Vector_ toolbar also shows a button to launch the plugin dialog
- _Processing_ toolbox (see below, "Using Conefor inside QGIS" paragraph)


??? note

    In QGIS the toolbars can be activated/deactivated by using the following menu:

		_View > toolbars_

	The content of a toolbar may vary depending on what tools/plugins are installed/active in a specific QGIS installation


## Usage

This plugin has two main intended usage workflows:

1. As a means for generating the Conefor input files (nodes and connections) from geospatial layers and then running 
   the standalone Conefor application with the tese input files. For this you can either:

   - Use the plugin's main dialog
   - Use the Processing algorithms present in _Processing toolbox > Conefor > Prepare input files_

2. As way to run the Conefor application from inside QGIS. In this workflow you can both prepare the Conefor input files
   and run the Conefor analysis by combining the Processing algorithms present in _Processing toolbox > Conefor_


## Preparing the inputs for post-processing with Conefor

The icon/shortcut available in the _Vector > conefor inputs_ menu or in the _Vector_ toolbar provides access to an 
interface that allows you to create the input files to be then processed with the Conefor application. For information
on how to use the Conefor application, see the 
[Conefor user manual](http://www.conefor.org/files/usuarios/Manual_Conefor_26.pdf). 

The tool allows to compute distance analysis and node (feature) queries:

- Distance from edges (for polygon layers)
- Distance from centroids (for polygon layers)
- Compute area of polygons (for polygon layers)
- Extract one attribute

The results are placed into (separate) text files (with the .txt file extension) inside an output folder.

For distance queries is available the option to compute also a vector layer that represents 
the segments with the minimum distance between the input features.

Upon opening the tool, it will load all currently selected vector layers. Additional layers can also be selected by
adding rows to the tool's main table.

{Insert image of the dialog}

The options are described here below:

-   **Layer**: the list of loaded layers to be analyzed/queried. If the user mistakenly loads a layer that is not to be 
    used, then it can double click on its name and a dropdown will show, allowing to choose any other proper layer 
    loaded in the QGIS project.

-   **NODE ID**: this option allows to choose what is the attribute to be used as unique ID. The plugin is also 
    able to autogenerate an ID

-   **Node Attribute**: this option allows the user to query (extract) one attribute from the table of attributes of the 
    input layer. Results will be placed in a text file beside the "NODE ID" values. 

    If you select the _<GENERATE_FROM_AREA>_ value, the plugin will the area of each feature as the node attribute. 
    Areas are computed using the ellipsoid and units defined in the QGIS Project. You can manage them by going to the
    QGIS main menu _Project > Properties... > General > Measurements_

-   **Remove layer/Add layer** buttons: These buttons allow you to remove/add layers to be processed

-   **Calculate node connections as**:

    -   **Edge distances** - When this option is active an output text file will be created and it will contain the 
        minimum distance between the edges (boundaries) of each feature.
    
    -   **Centroid distances** - When this option is active an output text file will be created and it will contain the 
        minimum distance between the centroids of features.


-   **Only use selected features**: If a selection is made in the QGIS canvas (in one or more input layers) and this 
    option is checked, then the analysis/queries will be run only using the selected features.

-   **Lock field names to first layer**: before running any analysis/query, for each layer it is mandatory to select
    a few options (a unique ID among the others, see below for details). If the number of layers to be analyzed/queried
    is high then this can become a tedious operation. By checking this option the user can force the tool to assume
    that the same analysis/queries have to be run for all the layers. The tool will also assume that all the layers
    have a unique ID with the same name.

- **Output directory**: the folder where output Conefor nodes and connections files will be placed. The output file 
  names contain the type of query and the layer name. For example, if the input file name is "espacios_natura2000" 
  then all the possible outputs will be:

    - distances_centroids_espacios_natura2000.txt
    - distances_edges_espacios_natura2000.txt
    - nodes_calculated_area_espacios_natura2000.txt
    - nodes_NODE_ATTRIBUTE_espacios_natura2000.txt
  
    !!! note
    
        When running multiple times the same analysis/query then the output files will not be overwritten, instead an 
        underscore and a progressive number is added at the end of the output file name, for example:
        
        - distances_centroids_espacios_natura2000_2.txt
        - distances_centroids_espacios_natura2000_2.txt
        - distances_centroids_espacios_natura2000_3.txt
        - ...

- **Run** button: to run the analysis/queries. 

  When running, the plugin dialog will close itself and the processing will be taking place as a background task. 
  The progress is displayed in QGIS status bar. You can also cancel the execution by clicking on the progress 
  indicator and then clicking the cancel button.

  When finished, the plugin displays a notification to let you know its work is done.


[//]: # (## Using Conefor inside QGIS)

[//]: # ()
[//]: # (The files created with the tool described in the previous section are meant to eventually be processed using the Conefor )

[//]: # (application, with either its graphical user interface or using the command line version.)

[//]: # ()
[//]: # (However, the qgisconefor plugin also provdes a set of QGIS Processing algorithms to perform the Conefor analysis )

[//]: # (directly inside the QGIS environment. This feature uses under the hood the command line version of Conefor, thus )

[//]: # (requiring that you have it installed on your system.)

[//]: # ()
[//]: # (This approach has the advantage of providing integration between QGIS' multiple geoprocessing/analysis/statistics tools)

[//]: # (and Conefor. It becomes possible to use Conefor analysis either:)

[//]: # ()
[//]: # (- As a standalone tool inside QGIS)

[//]: # (- For batch processing of multiple files)

[//]: # (- Chaining together multiple QGIS Processing tools by means of building a workflow with the Processing model builder)

[//]: # (- Storing complex workflows that use Conefor for reuse and sharing)

[//]: # ()
[//]: # ()
[//]: # (### Configure the Conefor Processing provider)

[//]: # ()
[//]: # (As mentioned above, in order to use Conefor inside QGIS you must have its command-line version already installed on )

[//]: # (your system. Follow the [Conefor download instructions]&#40;http://conefor.org/coneforsensinode.html&#41; for more information)

[//]: # (on how to install the Conefor command line version.)

[//]: # ()
[//]: # (In QGIS, you need to specify the path to the Conefor application by going to:)

[//]: # ()
[//]: # (_Settings > Options... > Processing > Providers > Conefor > Conefor executable path_)

[//]: # ()
[//]: # (and then providing the path on your system where Conefor is installed.)

[//]: # ()
[//]: # ()
[//]: # (### Using the Conefor Processing algorithms)

[//]: # ()
[//]: # (In the QGIS Processing toolbox, look for the **Conefor** section. )

[//]: # ()
[//]: # (??? Info - Enabling the QGIS Processing toolbox)

[//]: # ()
[//]: # (    If not already visible, you can enable it by going QGIS main menu _Processing > Toolbox_ )

[//]: # ()
[//]: # ()
[//]: # (The QGIS/Processing Conefor section is organized in groups, each one containing one or more tools:)

[//]: # ()
[//]: # (- _Binary indices_ - Contains algorithms for using Conefor's binary indices: BC, BCIIC, CCP, etc.)

[//]: # ()
[//]: # (- _Prepare input files_ - Contains algorithms for preparing the Conefor nodes and connection input files. These perform)

[//]: # (  the same task as the plugin's main dialog, which was described above)

[//]: # ()
[//]: # (- _Probability indices &#40;distance based&#41;_ - Contains algorithms for using Conefor's probability indices)

[//]: # (- _Probability indices &#40;probability based&#41;_ - Contains algorithms for using Conefor's probability indices)

[//]: # ()
[//]: # (- _Utilities_)

[//]: # ()
[//]: # (Technically the tools in the _Prepare input files_ and _Utilities_ sections do not require the Conefor command line )

[//]: # (tool to be installed, as they are meant to create the input files to be processed with the Conefor program )

[//]: # (&#40;as discussed above. The advantages of having these tools inside the QGIS Processing toolbox are the ones already )

[//]: # (cited, especially the possibility to run them in batch mode or as part of a larger workflow.)

[//]: # ()
[//]: # (When double clicking one of the tools a dialog is presented to the user, this allows to choose the inputs and )

[//]: # (parameters for that particular tasks. Please read the Conefor user manual for information related to the various Conefor)

[//]: # (indices and parameters.)

[//]: # ()
[//]: # ()
[//]: # (#### Running an algorithm in batch mode)

[//]: # ()
[//]: # (Since the Conefor algorithms are exposed inside the QGIS Processing toolbox, they can be ran in batch mode, just like)

[//]: # (all other toolbox tools. The official QGIS documentation has a section on how to use the batch mode:)

[//]: # ()
[//]: # (https://docs.qgis.org/3.34/en/docs/user_manual/processing/batch.html)

[//]: # ()
[//]: # ()
[//]: # (#### Creating Processing workflows with the model builder)

[//]: # ()
[//]: # (Since the Conefor algorithms are exposed inside the QGIS Processing toolbox, they can be integrated into larger )

[//]: # (workflows. The official QGIS documentation has a section on how to use the processing Model designer:)

[//]: # ()
[//]: # (https://docs.qgis.org/3.34/en/docs/user_manual/processing/modeler.html)
