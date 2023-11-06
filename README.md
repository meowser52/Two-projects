"learn to write" plain text editor and keyboard trainer
=================
First project in **Python practice** cource.

**Table of Contents**

- [Features](#features)
- [Installing](#installing)
- [Customization](#customization)

# Features
* Basic text editing: select, cut, copy, paste
* Open files, save files, print files
* Standard keyboard shortcuts support
* Keyboard Training with Statistics on matplotlib
  - upload any files to test your writing skills
  - task yourself with wikipedia keyboard training
  - see your results: words count; timer; erros made 
  - save/clear data from JSON

# Installing
Clone this repository and install requirements (pyQt5, wikipedia, matplotlib, pyqtdarktheme required)
```
pip install -r requirements.txt
```

Run "learn to write"
`python3 main.py`

# Customization
It's easy to design your own themes using `settings.json`.
* Change `default_font` field to set another font
* Change `theme` to dark to use default dark theme or
* set `use_default_theme` to __true__ and provide path to your stylesheet in `stylesheet`

