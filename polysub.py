""" Transcribe & Translate - PolySub App Layout using Flet """

import flet as ft
from flet import (
    UserControl,
    Page,
    Column,
    Row,
    Container,
    Text,
    padding,
    alignment,
    IconButton,
    Image,
    FilledTonalButton,
    Dropdown,
    ProgressBar,
    FilledButton,
    FilePicker,
)
from subsai import SubsAI, Tools
import os


# Main Class
class PolySub(UserControl):

    def __init__(self, page: Page):
        super().__init__(page)
        self.page = page
        self.file_picker = ft.FilePicker(on_result=self.on_dialog_result)
        page.overlay.append(self.file_picker)
        self.video_files = []
        self.output_folder = None
        
        self.languages = self.get_languages()

        self.input_lang = 'English'
        self.output_lang = 'Turkish'

        self.font_family = 'RobotoSlab'

        self.build()

    def get_languages(self):
        """ Get available languages for translation """
        translation_model = 'facebook/mbart-large-50-many-to-many-mmt'
        return Tools.available_translation_languages(translation_model)

    def set_input_lang(self, e):
        """ Set input language """
        self.input_lang = self.input_dropdown.value

    def set_output_lang(self, e):
        """ Set output language """
        self.output_lang = self.output_dropdown.value

    def add_log(self, text):
        """ Add text to log """
        self.log_view.controls.append(Text(
            text,
            size=17,
            color=ft.colors.WHITE,
            weight=ft.FontWeight.W_100,
            text_align=ft.TextAlign.LEFT,
            font_family=self.font_family,
        ))
        self.page.update()

    def on_dialog_result(self, e: ft.FilePickerResultEvent):
        self.video_files = []
        for f in e.files:
            print(f.path)
            self.video_files.append(f.path)

    def process_selected_videos(self, e):
        # Disable start process button
        self.button_submit.text = "Processing..."
        self.button_submit.style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            bgcolor=ft.colors.GREY_400,
        )
        self.button_submit.disabled = True
        self.page.update()

        for index, video_file in enumerate(self.video_files):
            try:
                # Generate subtitles
                print(f"Generating subtitles for {video_file}")
                subs_ai = SubsAI()
                model = subs_ai.create_model('openai/whisper', {'model_type': 'base'})
                subs = subs_ai.transcribe(video_file, model)

                # Translate subtitles
                print(f"Translating subtitles for {video_file}")
                translation_model = 'facebook/mbart-large-50-many-to-many-mmt'
                translated_subs = Tools.translate(subs, source_language=self.input_lang, target_language=self.output_lang, model=translation_model)

                # Save translated subtitles
                output_file = self.get_output_file(video_file)
                translated_subs.save(output_file)
                print(f"Translated file saved to {output_file}")

                # Update progress bar and status label
                self.progress_bar.value = (index + 1)/len(self.video_files)
                # self.status_label.configure(text=f"Status: Processed {index + 1}/{len(self.video_files)}")
            except Exception as e:
                print(f"Error processing {video_file}: {e}")
                # self.status_label.configure(text=f"Status: Error processing {video_file}")

    def get_output_file(self, video_file):
        if self.output_folder:
            output_file = os.path.join(self.output_folder, os.path.splitext(os.path.basename(video_file))[0] + ".srt")
        else:
            output_file = os.path.splitext(video_file)[0] + ".srt"
        return output_file

    # Navigation Container
    def NavContainer(self):
        self.nav = Container(
            Row(
                controls=[
                    Container(
                        Image(src='images/logo@8x.png', width=300),
                        padding=padding.all(0),
                        expand=1,
                    ),
                    Container(
                        padding=padding.all(0),
                        expand=2,
                    ),
                    Container(
                        Row(
                            controls=[
                                Container(
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    IconButton(icon='question_mark_rounded', aspect_ratio=1, scale=1),
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    IconButton(icon='settings', aspect_ratio=1, scale=1),
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                            ],
                        ),
                        padding=padding.all(0),
                        expand=1,
                    ),
                ],
            ),
            padding=0,
            expand=1,
        )

        return self.nav

    # Main Container
    def MainContainer(self):
        self.input_dropdown = Dropdown(
            options=[
                ft.dropdown.Option(lang) for lang in self.languages
            ],
            hint_text="Select Input Language",
            on_change=self.set_input_lang,
            value=self.input_lang,
        )

        self.output_dropdown = Dropdown(
            options=[
                ft.dropdown.Option(lang) for lang in self.languages
            ],
            hint_text="Select Output Language",
            on_change=self.set_output_lang,
            value=self.output_lang,
        )
        self.main = Container(
            Row(
                controls=[
                    Container(
                        padding=padding.all(0),
                        expand=1,
                    ),
                    Container(
                        Column(
                            controls=[
                                Container(
                                    FilledTonalButton(
                                        "Select Videos", 
                                        icon="file_upload_outlined",
                                        on_click=lambda _: self.file_picker.pick_files(
                                            allow_multiple=True,
                                            file_type=ft.FilePickerFileType.VIDEO,
                                        ),
                                        expand=1,
                                        width=450, # ! Temp solution
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                        ),
                                    ),
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                                Container(
                                    Text(
                                        'You can drag & drop your videos!',
                                        size=17,
                                        color=ft.colors.GREY_400,
                                        weight=ft.FontWeight.W_500,
                                        text_align=ft.TextAlign.CENTER,
                                        width=450, # ! Temp solution
                                        font_family=self.font_family,
                                    ),
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    self.input_dropdown,
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                                Container(
                                    self.output_dropdown,
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                                Container(
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    Text(
                                        'This Step is optional',
                                        size=17,
                                        color=ft.colors.GREY_400,
                                        weight=ft.FontWeight.W_500,
                                        text_align=ft.TextAlign.CENTER,
                                        width=450, # ! Temp solution
                                        font_family=self.font_family,
                                    ),
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    FilledTonalButton(
                                        "Select Save Path", 
                                        icon="folder_open",
                                        on_click=lambda x: print("Hello World"),
                                        expand=1,
                                        width=450, # ! Temp solution
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                            bgcolor=ft.colors.GREY_400,
                                        ),
                                        disabled=True,
                                    ),
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                            ],
                        ),
                        padding=padding.all(0),
                        expand=3,
                    ),
                    Container(
                        self.LogContainer(),
                        padding=padding.all(0),
                        expand=3,
                    ),
                    Container(
                        padding=padding.all(0),
                        expand=1,
                    ),
                ],
            ),
            padding=0,
            expand=3,
        )

        return self.main

    # Function Container
    def SubmitContainer(self):
        self.progress_bar = ProgressBar(
            width=900, # ! Temp solution
            bar_height=4,
            value=0,
            color="amber", 
            bgcolor="#eeeeee",
        )
        self.button_submit = FilledButton(
            "Start Transcribing",
            on_click=self.process_selected_videos,
            expand=1,
            width=900, # ! Temp solution
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                bgcolor=ft.colors.INDIGO,
            ),
        )
        self.submit = Container(
            Row(
                controls=[
                    Container(
                        padding=padding.all(0),
                        expand=1,
                    ),
                    Container(
                        Column(
                            controls=[
                                Container(
                                    self.progress_bar, 
                                    expand=1,
                                    padding=padding.all(20),
                                ),
                                Container(
                                    self.button_submit,
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                            ],
                        ),
                        padding=padding.all(0),
                        expand=6,
                    ),
                    Container(
                        padding=padding.all(0),
                        expand=1,
                    ),
                ],
            ),
            padding=0,
            expand=1,
        )

        return self.submit

    # Footer Container
    def FooterContainer(self):
        self.footer = Container(
            Column(
                controls=[
                    Container(
                        padding=padding.all(0),
                        expand=2,
                    ),
                    Container(
                        Text(
                            'All Rights Reserved © 2023',
                            size=17,
                            color=ft.colors.GREY_400,
                            weight=ft.FontWeight.W_500,
                            text_align=ft.TextAlign.CENTER,
                            width=1200, # ! Temp solution  
                            font_family=self.font_family,
                        ),
                        padding=padding.all(0),
                        expand=1,
                    )
                ],
            ),
            padding=0,
            expand=1,
        )

        return self.footer

    # Log Container
    def LogContainer(self):
        self.log_view = ft.ListView(
                expand=1,
                spacing=10,
                padding=padding.all(20),
                auto_scroll=True,
            )
        self.log_containter = Container(
            self.log_view,
            width=450, # ! Temp solution
            height=500, # ! Temp solution
            bgcolor='#333536',
        )
        return self.log_containter

    def build(self):
        return Column(
            controls=[
                self.NavContainer(),
                self.MainContainer(),
                self.SubmitContainer(),
                self.FooterContainer(),
            ],
            width=1200,
            height=1050,
        )

def start(page: Page):
    page.title = "PolySub - Transcribe & Translate"

    page.fonts = {
        "RobotoSlab": "https://github.com/google/fonts/raw/main/apache/robotoslab/RobotoSlab%5Bwght%5D.ttf"
    }

    page.horizontal_alignment = 'center'
    page.vertical_alignment = 'center'

    page.theme = ft.Theme(color_scheme_seed=ft.colors.INDIGO)

    # page.window_min_height = 600
    # page.window_min_width = 900

    # page.window_max_height = 800
    # page.window_max_width = 1200

    app = PolySub(page)
    page.add(app)

    page.window_height = 1100
    page.window_width = 1300
    page.window_resizable = False
    page.padding = padding.all(0)
    
    page.update()

if __name__ == '__main__':
    ft.app(target=start)
