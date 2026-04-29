# MALDI Mass Spec Analyzer



This tool is designed for the rapid identification of polymer repeat units and end-groups in MALDI-TOF mass spectra.

It automates the calculation of mass differences  between detected peaks and compares them against a customizable reference database.



\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

### 1\. Key Features



•	Interactive Spectrum View

Load .dat or .txt files and zoom into specific regions of interest.



•	Live Smoothing

Real-time noise reduction using a Savitzky-Golay filter with an adjustable window size.



•	Automated Peak Detection

Variable intensity thresholding to identify relevant signals even in noisy data.



•	Monomer Identification

Combinatorial delta-mass matching against an Excel database with adjustable tolerance.



•	End-Group Analysis

Automatic calculation of residual masses with support for common adducts,



•	Multi Series Annotation

Automatic calculation of residual masses with support for common adducts,



•	Series Export

Single or multiple series will be exported to Excel for further handling

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_





















### 2\. User Workflow



###### **Load Spectrum**

Import your raw data file (two-column ASCII format: m/z and intensity).



Fig.1



###### **Select m/z Region**

Use the **magnifying glass** in the left bottom toolbar to select a specific peak area.

If necessary, use the **Smooth slider (%)** to reduce baseline noise.



Fig.2



###### **Peak Detection Threshold**



Adjust the **Peak Detection Threshold slider (%)** to ensure that only significant peaks are marked with red crosses.

Avoid picking the ‘wrong’ isotope peaks in a high-resolution spectrum. Always adjust the threshold to select only the most abundant isotope.



Fig. 3



###### **Adduct Ion**



Select the adduct-ion from the dropdown list.

Then, carefully adjust the **Match tolerance (Da)** based on the quality of your instrument's calibration or to differentiate between polymer structures with nearly identical repeat unit masses. A value of 0.5 Da is sufficient for most monomer units. Increase slightly when your expected monomer mass does not appear in the table after the next step.



Fig. 4



###### **Analyze Zoom**



Click **Analyze Zoom** to populate the results table.

In this example, two monomer units are proposed. This (mostly) happens when peaks from two different series (i.e. two different end groups) are selected.

Here, it is clearly a PEG. However, it might be more difficult to determine in other cases. This can easily be checked using the right-hand window, as shown in the next step.



Fig. 5



###### **Select Monomer from Table**



Click on a row in the table to view a detailed zoom-in of the right window, which includes the calculated residual (end-group) mass. The peak assignment in this window enables the unambiguous identification of the correct polymer structure, as shown in the following two examples.

The selected monomer structure is highlighted by colored circles in the main spectrum.

&#x20;

For better visibility, the width of the window can be adjusted by sliding the divider, at the expense of the other window.



Check whether the red triangles indicate the correct isotopes (at higher resolution) or the same peak positions (at lower resolution). If not, then the wrong monomer structure was selected. In this case, the number of peaks marked in the main spectrum should ideally be reduced to two. This can be achieved in two ways:



1\. Select a narrower **zoom** region that ideally contains only two peaks of the series.

2\) Increasing the **peak threshold** so that only two peaks remain marked with red crosses.



###### Case #1 – correct structure



Fig. 6



###### Case #2 – wrong structure



Fig. 7



Use the **Home** button in the left bottom toolbar to display the whole m/z range and to check whether the correct structure has been selected.



The program cannot distinguish isobaric masses, such as acrylic acid and lactic acid, which both have a sum formula of (C3H4O2)n = 72.06 Da, or methyl methacrylate and valerolactone, which both have a sum formula of (C5H8O2)n = 100.05 Da.

Identifying them requires prior knowledge.

The selected monomer structure is highlighted by colored circles in the main spectrum. Use the **Home** button in the bottom left toolbar to display the entire m/z range, which allows you to verify that the correct structure has been selected.



Fig. 8



If too many (or too few) peaks have been selected, especially on the less intense sides of the peak distribution, increase the **Series Sensitivity** slightly and click **Analyze Zoom** again. Before selecting the monomer from the table again, press \[DEL] on your keyboard to delete the previously selected series.



Fig.9



If the mass spectrum shows multiple peak series with different end groups or monomer structures, use the **Home** button in the main spectrum and repeat all steps for each series.

Each series is indicated by a differently colored circle and can be exported separately or together with other series using the **Export Series** button.



Fig. 10



Minor series should be selected by carefully zooming in on just two peaks of the series. The right hand spectrum confirms a correct selection.



Fig. 11



###### **References**

###### &#x09;

Double-click the **References** in the selected row. These references are just examples, mostly of the first publications to refer to these polymers. Many more references are available, especially for the most common polymers.





###### **Reset**



Deletes all operations and clears all windows.

The **status** of each operation is displayed at the top right of the main window.







### Reference Database (structures.xlsx)



The program requires the Excel file named structures.xlsx which will be delivered with the program.

This file contains most common polymer structures along with specific polymer structures that were published in literature (by 2026) and can be customized by every user by adding new entries.

