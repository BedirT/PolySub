# PolySub

<div align="center">
  <img src="images/logo@8x.png" alt="Logo" width="200">
</div>

PolySub is a simple yet powerful GUI-based application that allows you to generate and translate subtitles for any video content. The application leverages the power of the state-of-the-art `SubsAI` module, using machine learning to perform transcription and translation.

## Features

- Transcribes and generates subtitles from video files in various formats (e.g., `.mp4`, `.mkv`, `.avi`, `.mov`, `.flv`, `.wmv`)
- Translates generated subtitles from one language to another
- Option to save translated subtitles in a custom output directory

## Prerequisites

- Python 3.6 or later
- Python packages: `os`, `tkinter`, `threading`, `customtkinter`, `subsai`



## Installation

### Requirements

This project has a number of Python package requirements which are listed in the `requirements.txt` file.

To install these requirements, use pip in the following way:

```bash
pip install -r requirements.txt
```

It's recommended to use a virtual environment to avoid any package conflicts.

Here is an example of how you can set up a virtual environment for this project:

```bash
python -m venv env
source env/bin/activate  # On Windows use `env\Scripts\activate`
pip install -r requirements.txt
```

When you're done working on the project, you can deactivate the virtual environment:

```bash
deactivate
```

If you're using a different shell or operating system, the commands for activating and deactivating the virtual environment might be different. You can find more information in the Python [documentation](https://docs.python.org/3/library/venv.html).

To install this application, you can clone the repository and run the script:

```bash
git clone https://github.com/BedirT/PolySub
cd yourrepo
python SubtitleApp.py
```

## Usage

After starting the application:

1. Click on "Select Video Files" to choose one or multiple video files you want to process.
2. Choose the input language (the language the video content is in).
3. Choose the output language (the language you want the subtitles translated to).
4. (Optional) Click on "Select Output File Location" to choose a custom directory to save the translated subtitle files. If you skip this step, the subtitle files will be saved in the same directory as the video files.
5. Click on "Start Process" to start the transcription and translation process.

The progress of the process will be displayed on the progress bar and in the status label, and detailed logs will be shown in the log text box.

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for more information.

## License

This project is licensed under the terms of the MIT license. See the [LICENSE](LICENSE.md) file.

---

## Support

For any questions or issues, please refer to our [Issue Tracker](https://github.com/BedirT/PolySub/issues) or contact us directly.

---

Feel free to use this README.md as a template for your project and replace "yourname", "yourrepo", and "yourproject" with the appropriate values.