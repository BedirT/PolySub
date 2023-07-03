import os
import tkinter
import tkinter.filedialog
import customtkinter
import threading
from subsai import SubsAI, Tools


class SubtitleApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # Set appearance mode to dark
        customtkinter.set_appearance_mode("Dark")

        # Configure window
        self.title("Subtitle Generator and Translator")
        self.geometry("1000x1200")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)

        # Select video file button
        self.select_video_button = customtkinter.CTkButton(self, text="Select Video Files", command=self.select_video_files)
        self.select_video_button.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # Input language label and dropdown
        self.input_language_label = customtkinter.CTkLabel(self, text="Input Language:")
        self.input_language_label.grid(row=1, column=0, padx=20, pady=(20, 0), sticky="nsew")
        self.input_language_var = tkinter.StringVar()
        self.input_language_dropdown = customtkinter.CTkOptionMenu(self, variable=self.input_language_var)
        self.input_language_dropdown.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.input_language_var.set("English")  # Set default input language

        # Output language label and dropdown
        self.output_language_label = customtkinter.CTkLabel(self, text="Output Language:")
        self.output_language_label.grid(row=3, column=0, padx=20, pady=(20, 0), sticky="nsew")
        self.output_language_var = tkinter.StringVar()
        self.output_language_dropdown = customtkinter.CTkOptionMenu(self, variable=self.output_language_var)
        self.output_language_dropdown.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.output_language_var.set("Turkish")  # Set default output language

        # Select output file location button
        self.select_output_button = customtkinter.CTkButton(self, text="Select Output File Location (Optional)", command=self.select_output_folder)
        self.select_output_button.grid(row=5, column=0, padx=20, pady=20, sticky="nsew")

        # Log text box
        self.log_textbox = customtkinter.CTkTextbox(self, state="disabled", width=250)
        self.log_textbox.grid(row=6, column=0, padx=20, pady=20, sticky="nsew")

        # Progress bar
        self.progress_bar = customtkinter.CTkProgressBar(self)
        self.progress_bar.grid(row=7, column=0, padx=20, pady=20, sticky="nsew")
        self.progress_bar.set(0)  # Set initial value of progress bar to 0
        self.progress_bar.grid_remove()  # Hide progress bar initially

        # Status label
        self.status_label = customtkinter.CTkLabel(self, text="Status: Ready")
        self.status_label.grid(row=8, column=0, padx=20, pady=20, sticky="nsew")

        # Start process button
        self.start_process_button = customtkinter.CTkButton(self, text="Start Process", command=self.start_process)
        self.start_process_button.grid(row=9, column=0, padx=20, pady=20, sticky="nsew")

        # Initialize variables
        self.video_files = []
        self.output_folder = None

        # Load languages in a separate thread to improve startup time
        threading.Thread(target=self.load_languages, daemon=True).start()

    def load_languages(self):
        languages = self.get_languages()
        self.input_language_dropdown.configure(values=languages)
        self.output_language_dropdown.configure(values=languages)

    def select_video_files(self):
        self.video_files = tkinter.filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov *.flv *.wmv")])
        self.log(f"Selected video files: {self.video_files}")

    def select_output_folder(self):
        self.output_folder = tkinter.filedialog.askdirectory()
        self.log(f"Selected output folder: {self.output_folder}")

    def get_languages(self):
        translation_model = 'facebook/mbart-large-50-many-to-many-mmt'
        return Tools.available_translation_languages(translation_model)

    def start_process(self):
        if not self.video_files:
            tkinter.messagebox.showerror("Error", "Please select video files.")
            return

        if not self.input_language_var.get():
            tkinter.messagebox.showerror("Error", "Please select an input language.")
            return

        if not self.output_language_var.get():
            tkinter.messagebox.showerror("Error", "Please select an output language.")
            return

        self.progress_bar.grid()  # Show progress bar when process starts
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)  # Reset progress bar value
        self.status_label.configure(text="Status: In progress")
        threading.Thread(target=self.process_videos, daemon=True).start()

    def process_videos(self):
        # Disable start process button
        self.start_process_button.configure(state="disabled")

        for index, video_file in enumerate(self.video_files):
            try:
                # Generate subtitles
                self.log(f"Generating subtitles for {video_file}")
                subs_ai = SubsAI()
                model = subs_ai.create_model('openai/whisper', {'model_type': 'base'})
                subs = subs_ai.transcribe(video_file, model)

                # Translate subtitles
                self.log(f"Translating subtitles for {video_file}")
                translation_model = 'facebook/mbart-large-50-many-to-many-mmt'
                translated_subs = Tools.translate(subs, source_language=self.input_language_var.get(), target_language=self.output_language_var.get(), model=translation_model)

                # Save translated subtitles
                output_file = self.get_output_file(video_file)
                translated_subs.save(output_file)
                self.log(f"Translated file saved to {output_file}")

                # Update progress bar and status label
                self.progress_bar.set((index + 1)/len(self.video_files))
                self.status_label.configure(text=f"Status: Processed {index + 1}/{len(self.video_files)}")
            except Exception as e:
                self.log(f"Error processing {video_file}: {e}")
                self.status_label.configure(text=f"Status: Error processing {video_file}")

        # Reset progress bar value and enable start process button
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()  # Hide progress bar when process is done
        self.status_label.configure(text="Status: Finished")
        self.start_process_button.configure(state="normal")

    def get_output_file(self, video_file):
        if self.output_folder:
            output_file = os.path.join(self.output_folder, os.path.splitext(os.path.basename(video_file))[0] + ".srt")
        else:
            output_file = os.path.splitext(video_file)[0] + ".srt"
        return output_file

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert(tkinter.END, message + "\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.yview(tkinter.END)

if __name__ == "__main__":
    app = SubtitleApp()
    app.mainloop()